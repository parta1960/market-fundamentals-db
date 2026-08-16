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
    ("close", "Price (quarter-end close, unadjusted)", "ps", "Valuation"),
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
        wide["shares"] = wide["adj"] / pd.Series(
            [fmap[i] for i in wide.index], index=wide.index)
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

    names = {}
    if not comp.empty:
        c = comp.drop_duplicates("ticker")
        names = {r.ticker: (r.name if isinstance(r.name, str) else getattr(r, "name", ""),
                            getattr(r, "sector", ""))
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
        # drop metrics that are entirely null for this ticker (smaller files)
        doc["series"] = {k: v for k, v in doc["series"].items()
                        if any(x is not None for x in v)}
        blob = json.dumps(doc, separators=(",", ":")).encode()
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
        json.dump(manifest, f, separators=(",", ":"))
    print(f"history_export: {written} written, {unchanged} unchanged, "
          f"{len(tickers_out)} tickers")


if __name__ == "__main__":
    build()
