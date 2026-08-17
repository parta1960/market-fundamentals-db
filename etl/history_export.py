"""v1.2 history export — per-ticker quarterly time series for the charts page.

Reads data/parquet/derived_metrics/per_quarter.parquet, prices_daily and
companies; writes docs/data/history/<TICKER>.json (one compact file per ticker,
same-origin for GitHub Pages, no CORS) plus manifest.json (ticker list + metric
catalog + as-of date).

Adds price-anchored valuation history: for each fiscal quarter end we take the
last RAW close on or before that date (raw, not adjusted: the share count in
per_quarter is the count as of that quarter, so raw close x that count is the
market cap of the day — and raw closes never get retro-revised by later
dividends/splits, which keeps these files byte-stable and git-friendly) and
compute pe_ttm, ps_ttm, pfcf_ttm, pb and mktcap at that quarter end.

Ratio conventions: denominators <= 0 produce null (a negative P/E is noise).

Share-count correction (v1.2, important): the stored share observations mix two
conventions — Alpha Vantage balance-sheet counts are retroactively SPLIT-
ADJUSTED to today's basis, while EDGAR (dei / us-gaap) counts are AS-REPORTED
at the time. Pairing raw closes with today-basis counts inflates early market
caps ~28x for AAPL. Fix: using the split events recorded in prices_daily
(split_coefficient != 1), every observation is converted to a common today-
adjusted basis (AV: as-is; EDGAR: x cumulative-splits-after-observation), a
rolling-median spike guard drops corrupt points (some EDGAR weighted-average
entries are off by ~1000x — a units bug in source filings), and the count at
each fiscal quarter end is converted back to the AS-REPORTED basis of that
date. All per-share and valuation series here are recomputed from these
corrected counts; per_quarter.parquet's own eps/ps columns are NOT used
(they carry the mixed-basis flaw — fixing that upstream is a v0.6 item).
Pre-Nov-1999 splits are invisible (price history starts then), so per-share
values before ~2000 for companies that split earlier may be on the wrong
basis; those quarters have no price anyway, so valuation ratios are null.

Churn control: a ticker file is rewritten only when its content changed, so the
daily commit normally touches nothing here outside reporting season. The as-of
date lives only in manifest.json for the same reason.

File format (arrays are index-aligned; null = not available):
  {"ticker": "AAPL", "name": "...", "sector": "...",
   "quarters": ["2006-06-30", ...],
   "series": {"revenue": [...], "pe_ttm": [...], ...}}
"""

import glob
import json
import math
import os

import pandas as pd

PARQUET = "data/parquet"
OUT_DIR = "docs/data/history"

# metric key -> (label, unit, group). Unit drives axis formatting on the page:
#   usd   = dollars (auto-scaled B/M on the page)   ps = per-share dollars
#   pct   = fraction rendered as %                  x  = ratio/multiple
#   cnt   = share count (auto-scaled)
METRICS = [
    ("revenue", "Revenue (quarterly)", "usd", "Income statement"),
    ("revenue_ttm", "Revenue (TTM)", "usd", "Income statement"),
    ("gross_profit", "Gross profit", "usd", "Income statement"),
    ("operating_income", "Operating income", "usd", "Income statement"),
    ("net_income", "Net income (quarterly)", "usd", "Income statement"),
    ("net_income_ttm", "Net income (TTM)", "usd", "Income statement"),
    ("ocf", "Operating cash flow", "usd", "Cash flow"),
    ("capex", "Capital expenditures", "usd", "Cash flow"),
    ("fcf", "Free cash flow (quarterly)", "usd", "Cash flow"),
    ("fcf_ttm", "Free cash flow (TTM)", "usd", "Cash flow"),
    ("equity", "Shareholder equity (book)", "usd", "Balance sheet"),
    ("cash", "Cash & equivalents", "usd", "Balance sheet"),
    ("total_debt", "Total debt", "usd", "Balance sheet"),
    ("shares", "Shares outstanding", "cnt", "Balance sheet"),
    ("shares_diluted", "Shares (wtd-avg diluted)", "cnt", "Balance sheet"),
    ("gross_margin", "Gross margin", "pct", "Margins & growth"),
    ("op_margin", "Operating margin", "pct", "Margins & growth"),
    ("net_margin", "Net margin", "pct", "Margins & growth"),
    ("rev_yoy", "Revenue growth y/y", "pct", "Margins & growth"),
    ("ni_yoy", "Net income growth y/y", "pct", "Margins & growth"),
    ("eps_q", "EPS (quarterly)", "ps", "Per share"),
    ("eps_ttm", "EPS (TTM)", "ps", "Per share"),
    ("revenue_ps", "Revenue / share", "ps", "Per share"),
    ("fcf_ps", "FCF / share", "ps", "Per share"),
    ("book_ps", "Book value / share", "ps", "Per share"),
    ("close", "Price (quarter-end close, split-adjusted)", "ps", "Valuation"),
    ("mktcap", "Market cap", "usd", "Valuation"),
    ("pe_ttm", "P/E (TTM)", "x", "Valuation"),
    ("ps_ttm", "P/S (TTM)", "x", "Valuation"),
    ("pfcf_ttm", "P/FCF (TTM)", "x", "Valuation"),
    ("pb", "P/B", "x", "Valuation"),
]

# balance-sheet items pulled straight from the fundamentals long table
EXTRA_ITEMS = {
    "cashAndCashEquivalentsAtCarryingValue": "cash",
    "shortLongTermDebtTotal": "total_debt",
}


def _read(table):
    files = glob.glob(f"{PARQUET}/{table}/part_*.parquet")
    if not files:
        single = f"{PARQUET}/{table}.parquet"
        files = [single] if os.path.exists(single) else []
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)


def _sig(v, digits=6):
    """Round to significant digits; None for NaN/inf (JSON-safe)."""
    if v is None or isinstance(v, str):
        return v
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    if f == 0:
        return 0
    r = round(f, digits - 1 - int(math.floor(math.log10(abs(f)))))
    return int(r) if abs(r) >= 1e6 and r == int(r) else r


def _ratio(num, den):
    return num / den if den and not pd.isna(den) and den > 0 else float("nan")


SHARE_PREF = {"edgar:dei": 0, "edgar:us-gaap": 1, "alphavantage": 2,
              "edgar:us-gaap-issued": 3, "edgar:wavg-basic": 4,
              "edgar:wavg-diluted": 5}


def _factor_after(ev: pd.DataFrame, ticker: str, dates) -> "list[float]":
    """Cumulative split factor strictly AFTER each date (1.0 if none)."""
    import numpy as np
    e = ev[ev.ticker == ticker].sort_values("date")
    d = pd.to_datetime(pd.Series(list(dates)))
    if e.empty:
        return [1.0] * len(d)
    coeffs = e.split_coefficient.to_numpy()
    # suffix products: suffix[i] = product of coeffs[i:]
    suffix = np.concatenate([np.cumprod(coeffs[::-1])[::-1], [1.0]])
    idx = np.searchsorted(e.date.to_numpy(), d.to_numpy(), side="right")
    return [float(suffix[i]) for i in idx]


def corrected_shares(shares: pd.DataFrame, prices: pd.DataFrame) -> tuple:
    """Return (obs, splits): obs = per-ticker share observations on a common
    today-adjusted basis, spike-guarded; splits = split events per ticker.
    """
    ev = prices.loc[prices.split_coefficient.fillna(1) != 1,
                    ["ticker", "date", "split_coefficient"]].copy()
    ev["date"] = pd.to_datetime(ev["date"])

    s = shares.dropna(subset=["shares", "as_of"]).copy()
    s = s[s.shares > 0]
    s["as_of"] = pd.to_datetime(s["as_of"])
    s["pref"] = s.source.map(SHARE_PREF).fillna(9)
    parts = []
    for t, g in s.groupby("ticker"):
        g = g.copy()
        f = pd.Series(_factor_after(ev, t, g.as_of), index=g.index)
        # to common today-adjusted basis
        g["adj"] = g.shares.where(g.source == "alphavantage", g.shares * f)
        g = (g.sort_values(["as_of", "pref"])
               .drop_duplicates(["as_of"], keep="first"))
        # spike guard on the (smooth) adjusted series
        med = g.adj.rolling(7, center=True, min_periods=3).median()
        ok = (g.adj / med).between(0.55, 1.8) | med.isna()
        g = g[ok]
        parts.append(g[["ticker", "as_of", "adj"]])
    obs = (pd.concat(parts, ignore_index=True)
             .sort_values(["ticker", "as_of"]) if parts else pd.DataFrame())
    return obs, ev


TREND_METRICS = {"eps": "eps_ttm", "rps": "revenue_ps", "fps": "fcf_ps",
                 "rev": "revenue_ttm", "ni": "net_income_ttm", "fcf": "fcf_ttm",
                 "gm": "gross_margin", "om": "op_margin", "bps": "book_ps"}
TREND_WINDOWS = (20, 40, 0)          # 5y, 10y, all history (quarters)
# per metric: [lin %/yr, lin R², lin slope/yr, exp %/yr, exp R², exp b, n]
TREND_FIELDS = ["lg", "lr", "lm", "eg", "er", "eb", "n"]


def _lin_trend(dates, ys):
    """Least-squares line y = c + m*t (t in years) over one series.

    Returns (growth_per_year, r2, slope_per_year, n) or None when there are
    fewer than 6 usable points. growth_per_year = m / mean(y) — the slope
    expressed as a fraction of the average level, which is exactly the slope
    divided by the fitted value at the window's midpoint (an OLS line passes
    through the centroid). It is null when the average level is <= 0, where a
    percentage growth rate has no meaning (e.g. persistently negative EPS).
    """
    import numpy as np
    t, y = [], []
    for d, v in zip(dates, ys):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        t.append(pd.Timestamp(d).value / 3.15576e16)      # ns -> years
        y.append(float(v))
    if len(y) < 6:
        return None
    t = np.asarray(t); y = np.asarray(y)
    t = t - t[0]
    m, c = np.polyfit(t, y, 1)
    pred = m * t + c
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(((y - pred) ** 2).sum()) / sst if sst > 0 else 1.0
    ybar = float(y.mean())
    # A percentage rate is only meaningful when the average level is solidly
    # positive. If the series swings across zero (mean near zero relative to
    # its typical magnitude, e.g. WBD's EPS) slope/mean explodes to nonsense
    # like -2600%/yr, so report no percentage — the slope and R² still stand.
    amean = float(np.abs(y).mean())
    g = m / ybar if (ybar > 0 and amean > 0 and ybar >= 0.25 * amean) else None
    return (g, r2, float(m), len(y))


def detect_breaks(quarters, rev):
    """Sudden, SUSTAINED shifts in the revenue level (v1.12.0).

    A spin-off, divestiture, deconsolidation or transforming acquisition moves
    a company's revenue to a new plateau; fits that span such a break describe
    two different companies. Detection compares each quarter with the SAME
    quarter a year earlier (so seasonality cancels), requires the change to be
    step-like (the prior year was normal — otherwise fast organic compounding
    would be flagged) and requires the new level to hold for about a year
    (which filters out one-quarter reporting glitches and COVID-style dips
    that snap back).

    Returns [{"d": quarter, "r": level ratio after/before, "t": "s"|"x"}]
    where "x" marks changes so extreme (>5x or <0.2x) they deserve a manual
    look before being trusted.
    """
    import statistics as st
    ev, n = [], len(rev)
    for i in range(4, n):
        a, b = rev[i - 4], rev[i]
        if not a or not b or a <= 0 or b <= 0:
            continue
        yy = b / a
        pyy = None
        if i >= 5 and rev[i - 5] and rev[i - 1] and rev[i - 5] > 0 and rev[i - 1] > 0:
            pyy = rev[i - 1] / rev[i - 5]
        drop = yy <= 0.65 and (pyy is None or pyy >= 0.8)
        jump = yy >= 1.6 and (pyy is None or pyy <= 1.25)
        if not (drop or jump):
            continue
        before = [v for v in rev[max(0, i - 4):i] if v and v > 0]
        after = [v for v in rev[i:i + 4] if v and v > 0]
        if len(before) < 3 or len(after) < 3:
            continue
        mr = st.median(after) / st.median(before)
        if drop and mr > 0.75:
            continue
        if jump and mr < 1.35:
            continue
        ev.append((i, mr))
    out, last = [], -99
    for i, mr in ev:
        if i - last > 3:
            out.append({"d": quarters[i], "r": _sig(mr, 3),
                        "t": "s" if 0.2 <= mr <= 5 else "x"})
        last = i
    return out


def _exp_trend(dates, ys):
    """Least-squares y = a*e^(b*t) via ln(y) (positive values only).

    Returns (growth_per_year = e^b - 1, r2_log_space, b, n) or None.
    """
    import numpy as np
    t, y = [], []
    nn = 0
    for d, v in zip(dates, ys):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        nn += 1
        if v > 0:
            t.append(pd.Timestamp(d).value / 3.15576e16)
            y.append(math.log(float(v)))
    if len(y) < 6 or len(y) < 0.5 * nn:
        return None
    t = np.asarray(t); y = np.asarray(y)
    t = t - t[0]
    b, lna = np.polyfit(t, y, 1)
    pred = b * t + lna
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(((y - pred) ** 2).sum()) / sst if sst > 0 else 1.0
    return (math.exp(b) - 1.0, r2, float(b), len(y))


def build_trends(wide):
    """Per-ticker LINEAR and EXPONENTIAL fit parameters for the screener.

    v1.11.0: both fit families, with R², for every metric in TREND_METRICS
    and every window in TREND_WINDOWS, so any of them can be screened on.
    """
    out = {str(w): {} for w in TREND_WINDOWS}
    for t, g in wide.groupby("ticker"):
        g = g.sort_values("fiscal_date_ending")
        for w in TREND_WINDOWS:
            gw = g.tail(w) if w else g
            rec = {}
            for key, col in TREND_METRICS.items():
                if col not in gw.columns:
                    continue
                lin = _lin_trend(gw.fiscal_date_ending, gw[col])
                exp = _exp_trend(gw.fiscal_date_ending, gw[col])
                if lin is None and exp is None:
                    continue
                lg, lr, lm, n = lin if lin else (None, None, None, 0)
                eg, er, eb, en = exp if exp else (None, None, None, 0)
                rec[key] = [
                    _sig(lg, 4) if lg is not None else None,
                    _sig(lr, 3) if lr is not None else None,
                    _sig(lm, 4) if lm is not None else None,
                    _sig(eg, 4) if eg is not None else None,
                    _sig(er, 3) if er is not None else None,
                    _sig(eb, 4) if eb is not None else None,
                    max(n, en)]
            if rec:
                out[str(w)][t] = rec
    return out


def build():
    pq = f"{PARQUET}/derived_metrics/per_quarter.parquet"
    if not os.path.exists(pq):
        print("history_export: no per_quarter parquet yet, skipping")
        return
    wide = pd.read_parquet(pq)
    prices = _read("prices_daily")
    comp = _read("companies")
    fund = _read("fundamentals")

    # extra balance-sheet items -> wide columns
    if not fund.empty:
        ex = fund[fund.item.isin(EXTRA_ITEMS)].copy()
        if not ex.empty:
            ex["metric"] = ex["item"].map(EXTRA_ITEMS)
            ex = (ex.sort_values("statement")
                    .drop_duplicates(["ticker", "fiscal_date_ending", "metric"])
                    .pivot(index=["ticker", "fiscal_date_ending"],
                           columns="metric", values="value").reset_index())
            wide = wide.merge(ex, on=["ticker", "fiscal_date_ending"], how="left")

    # quarter-end raw close via as-of join (last trading day on/before quarter end)
    if not prices.empty:
        px = (prices[["ticker", "date", "close"]]
              .dropna().sort_values("date"))
        px["date"] = pd.to_datetime(px["date"])
        wide = wide.sort_values("fiscal_date_ending")
        wide = pd.merge_asof(
            wide, px.rename(columns={"date": "fiscal_date_ending"}),
            on="fiscal_date_ending", by="ticker", direction="backward",
            tolerance=pd.Timedelta(days=10))
    else:
        wide["close"] = float("nan")

    # --- corrected share counts (see module docstring) -----------------
    split_factor = None
    shares_raw = _read("shares_outstanding")
    if not shares_raw.empty and not prices.empty:
        obs, ev = corrected_shares(shares_raw, prices)
        wide = wide.sort_values("fiscal_date_ending")
        wide = pd.merge_asof(
            wide,
            obs.rename(columns={"as_of": "fiscal_date_ending"})
               .sort_values("fiscal_date_ending"),
            on="fiscal_date_ending", by="ticker", direction="backward")
        wide = wide.sort_values(["ticker", "fiscal_date_ending"])
        fq = []
        for t, g in wide.groupby("ticker", sort=True):
            fq.extend(zip(g.index, _factor_after(ev, t, g.fiscal_date_ending)))
        fmap = dict(fq)
        split_factor = pd.Series([fmap[i] for i in wide.index], index=wide.index)
        wide["shares"] = wide["adj"] / split_factor
        wide = wide.drop(columns=["adj"])
        # per-share series recomputed on the corrected, as-reported basis
        wide["eps_q"] = wide.get("net_income", pd.NA) / wide["shares"]
        wide["eps_ttm"] = wide.get("net_income_ttm", pd.NA) / wide["shares"]
        wide["revenue_ps"] = wide.get("revenue", pd.NA) / wide["shares"]
        wide["fcf_ps"] = wide.get("fcf", pd.NA) / wide["shares"]
        wide["book_ps"] = wide.get("equity", pd.NA) / wide["shares"]

    wide["mktcap"] = wide["close"] * wide["shares"]
    wide["pe_ttm"] = [_ratio(c, e) for c, e in zip(wide["close"], wide["eps_ttm"])]
    wide["ps_ttm"] = [_ratio(c, r / s) if s and not pd.isna(s) and s > 0 else float("nan")
                      for c, r, s in zip(wide["close"], wide["revenue_ttm"], wide["shares"])]
    wide["pfcf_ttm"] = [_ratio(c, f / s) if s and not pd.isna(s) and s > 0 else float("nan")
                        for c, f, s in zip(wide["close"], wide["fcf_ttm"], wide["shares"])]
    wide["pb"] = [_ratio(c, b) for c, b in zip(wide["close"], wide["book_ps"])]

    # ---- display basis: SPLIT-ADJUST price, shares and per-share series ----
    # Ratios above are computed on the internally consistent as-reported pair
    # (actual close x same-date count) and are mathematically unchanged. But
    # per-share SERIES are presented split-adjusted to today's basis so charts
    # are continuous across splits and directly comparable to Yahoo Finance /
    # Seeking Alpha (v1.4.1 fix: AAPL EPS no longer "drops" at the 2014 7:1
    # and 2020 4:1 splits).
    if split_factor is not None:
        wide["close"] = wide["close"] / split_factor
        wide["shares"] = wide["shares"] * split_factor
        for c in ("eps_q", "eps_ttm", "revenue_ps", "fcf_ps", "book_ps"):
            if c in wide.columns:
                wide[c] = wide[c] / split_factor

    # ---- diluted weighted-average share count (v1.5.0) --------------------
    # EDGAR wtd-avg DILUTED counts, converted to today-adjusted basis (same
    # split machinery), spike-guarded, joined at each fiscal quarter end.
    # Display-only series (no ratios derive from it), so no basis round-trip.
    if split_factor is not None and not shares_raw.empty:
        d = shares_raw[shares_raw.source == "edgar:wavg-diluted"].dropna(
            subset=["shares", "as_of"]).copy()
        d = d[d.shares > 0]
        d["as_of"] = pd.to_datetime(d["as_of"])
        dparts = []
        for t, g in d.groupby("ticker"):
            g = g.copy()
            f = pd.Series(_factor_after(ev, t, g.as_of), index=g.index)
            g["shares_diluted"] = g.shares * f
            g = g.sort_values("as_of").drop_duplicates(["as_of"], keep="last")
            med = g.shares_diluted.rolling(7, center=True, min_periods=3).median()
            ok = (g.shares_diluted / med).between(0.55, 1.8) | med.isna()
            dparts.append(g.loc[ok, ["ticker", "as_of", "shares_diluted"]])
        if dparts:
            dil = pd.concat(dparts, ignore_index=True).sort_values("as_of")
            wide = wide.sort_values("fiscal_date_ending")
            wide = pd.merge_asof(
                wide, dil.rename(columns={"as_of": "fiscal_date_ending"}),
                on="fiscal_date_ending", by="ticker", direction="backward",
                tolerance=pd.Timedelta(days=10))
            # absolute anchor: diluted must be within 0.5x-2x of the corrected
            # outstanding count at the same quarter (both today-adjusted here).
            # Catches BLOCKS of ~1000x units bugs that a rolling median passes
            # when consecutive filings share the bug (e.g. NVDA 2010-13).
            rr = wide["shares_diluted"] / wide["shares"]
            wide.loc[~rr.between(0.5, 2.0), "shares_diluted"] = float("nan")

    # ---- split events per ticker (v1.5.0): charts mark the first data point
    # after each split so split handling is verifiable by eye.
    splits_by = {}
    breaks_by = {}          # ticker -> structural revenue breaks (v1.12.0)
    if split_factor is not None:
        for t, g in ev.groupby("ticker"):
            splits_by[t] = [
                {"d": r.date.strftime("%Y-%m-%d"),
                 "r": _sig(r.split_coefficient, 4)}
                for r in g.sort_values("date").itertuples(index=False)]

    names = {}
    if not comp.empty:
        c = comp.drop_duplicates("ticker")
        _s = lambda v: v if isinstance(v, str) else ""   # NaN names -> "" (v1.4.2)
        names = {r.ticker: (_s(r.name), _s(r.sector))
                 for r in c[["ticker", "name", "sector"]].itertuples(index=False)}

    os.makedirs(OUT_DIR, exist_ok=True)
    written = unchanged = 0
    tickers_out = []
    keys = [k for k, *_ in METRICS]
    for t, g in wide.groupby("ticker"):
        g = g.sort_values("fiscal_date_ending")
        nm, sec = names.get(t, ("", ""))
        doc = {
            "ticker": t, "name": nm, "sector": sec,
            "quarters": [d.strftime("%Y-%m-%d") for d in g.fiscal_date_ending],
            "series": {k: [_sig(v) for v in g[k]] if k in g.columns
                       else [None] * len(g) for k in keys},
        }
        if splits_by.get(t):
            doc["splits"] = splits_by[t]
        brk = detect_breaks(doc["quarters"], doc["series"].get("revenue") or [])
        if brk:
            doc["breaks"] = brk
            breaks_by[t] = brk
        # drop metrics that are entirely null for this ticker (smaller files)
        doc["series"] = {k: v for k, v in doc["series"].items()
                        if any(x is not None for x in v)}
        blob = json.dumps(doc, separators=(",", ":"), allow_nan=False).encode()
        path = f"{OUT_DIR}/{t}.json"
        if os.path.exists(path) and open(path, "rb").read() == blob:
            unchanged += 1
        else:
            with open(path, "wb") as f:
                f.write(blob)
            written += 1
        tickers_out.append({"t": t, "n": nm, "s": sec})

    manifest = {
        "as_of": str(wide.fiscal_date_ending.max().date()),
        "count": len(tickers_out),
        "metrics": [{"k": k, "label": lab, "unit": u, "group": grp}
                    for k, lab, u, grp in METRICS],
        "tickers": sorted(tickers_out, key=lambda x: x["t"]),
    }
    with open(f"{OUT_DIR}/manifest.json", "w") as f:
        json.dump(manifest, f, separators=(",", ":"), allow_nan=False)

    # ---- fit parameters for the screener (v1.10.0, both fits v1.11.0) ---
    # One file per window so the page only downloads the window in use.
    os.makedirs("docs/data", exist_ok=True)
    allw = build_trends(wide)
    # years since the last structural break, so screens can exclude companies
    # whose fits span a spin-off / transforming acquisition (v1.12.0)
    asof = pd.Timestamp(manifest["as_of"])
    for w, data in allw.items():
        for t, rec in data.items():
            b = breaks_by.get(t)
            if b:
                yrs = (asof - pd.Timestamp(b[-1]["d"])).days / 365.25
                rec["_b"] = [_sig(yrs, 3), len(b)]
            else:
                rec["_b"] = [99, 0]
    head = {"as_of": manifest["as_of"],
            "windows": [str(w) for w in TREND_WINDOWS],
            "metrics": TREND_METRICS, "fields": TREND_FIELDS}
    with open("docs/data/trends_index.json", "w") as f:
        json.dump(head, f, separators=(",", ":"), allow_nan=False)
    total = 0
    for w, data in allw.items():
        blob = json.dumps({**head, "window": w, "t": data},
                          separators=(",", ":"), allow_nan=False).encode()
        p = f"docs/data/trends_{w}.json"
        if not (os.path.exists(p) and open(p, "rb").read() == blob):
            with open(p, "wb") as f:
                f.write(blob)
        total += len(blob)
    print(f"history_export: trend files {total/1024:.0f} KB "
          f"({len(TREND_METRICS)} metrics x {len(TREND_WINDOWS)} windows)")
    print(f"history_export: {written} written, {unchanged} unchanged, "
          f"{len(tickers_out)} tickers")


if __name__ == "__main__":
    build()
