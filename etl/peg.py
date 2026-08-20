"""PEG variants (v1.20.0) — appended to docs/data/latest_ratios.json.

Runs LAST in the daily job (after derived.build() + history_export.build()),
so every input file it reads is already fresh. Adds six fields per ticker:

  peg_yoy    P/E ÷ 1-year EPS growth   (EPS now vs 4 quarters ago)
  peg_cagr3  P/E ÷ 3-year EPS CAGR
  peg_cagr5  P/E ÷ 5-year EPS CAGR
  peg_lin    P/E ÷ %EPS(10y)           (the linear-fit unitless slope already
                                        stored in trends_40.json as eps 'pg')
  peg_fwd    Alpha Vantage OVERVIEW PEGRatio (forward/analyst-based) — premium
             key, one OVERVIEW call per ticker; carried forward on any failure
  fwd_pe     Alpha Vantage OVERVIEW ForwardPE (kept alongside for context)

All trailing PEGs are P/E ÷ (growth in %), blanked when P/E is missing/≤0 or
the growth rate is ≤0 (a PEG on non-positive growth is meaningless). These are
DATA columns only for now; the UI can expose/rank on them later.
"""
import json
import os

import av_client

LR = "docs/data/latest_ratios.json"
TR = "docs/data/trends_40.json"
HIST = "docs/data/history/{}.json"


def _cagr(e, n):
    """Compound annual EPS growth over n quarters (n/4 years), or None."""
    if len(e) > n and e[-1 - n] and e[-1] and e[-1 - n] > 0 and e[-1] > 0:
        return (e[-1] / e[-1 - n]) ** (4.0 / n) - 1
    return None


def _eps_series(t):
    p = HIST.format(t)
    if not os.path.exists(p):
        return []
    try:
        s = json.load(open(p)).get("series", {}).get("eps_ttm", [])
        return [x if isinstance(x, (int, float)) else None for x in s]
    except Exception:
        return []


def build(fetch_forward=True, min_interval=0.4):
    if not os.path.exists(LR):
        print("peg: latest_ratios.json missing — skipping")
        return
    rows = json.load(open(LR))

    # %EPS(10y) per ticker from the trend file (peg_lin numerator's growth)
    trpg = {}
    if os.path.exists(TR):
        t = json.load(open(TR))
        F = t.get("fields", [])
        i = F.index("pg") if "pg" in F else -1
        if i >= 0:
            for k, v in t.get("t", {}).items():
                ev = v.get("eps")
                trpg[k] = ev[i] if (ev and ev[i] is not None) else None

    prev_fwd = {r["ticker"]: r.get("peg_fwd") for r in rows}  # carry-forward
    prev_fpe = {r["ticker"]: r.get("fwd_pe") for r in rows}

    for r in rows:
        pe = r.get("pe_ttm")
        e = _eps_series(r["ticker"])

        def peg(g):
            return pe / (100 * g) if (pe and pe > 0 and g and g > 0) else None

        r["peg_yoy"] = peg(_cagr(e, 4))
        r["peg_cagr3"] = peg(_cagr(e, 12))
        r["peg_cagr5"] = peg(_cagr(e, 20))
        pg = trpg.get(r["ticker"])
        r["peg_lin"] = pe / (100 * pg) if (pe and pe > 0 and pg and pg > 0) else None

    n_fwd = 0
    if fetch_forward:
        for r in rows:
            t = r["ticker"]
            try:
                ov = av_client.fetch("OVERVIEW", t, min_interval, require="Symbol")

                def num(k):
                    try:
                        return float(ov.get(k))
                    except (TypeError, ValueError):
                        return None

                pf = num("PEGRatio")
                r["peg_fwd"] = pf if (pf and pf > 0) else prev_fwd.get(t)
                fpe = num("ForwardPE")
                r["fwd_pe"] = fpe if (fpe and fpe > 0) else prev_fpe.get(t)
                if pf and pf > 0:
                    n_fwd += 1
            except Exception as ex:
                r["peg_fwd"] = prev_fwd.get(t)   # keep last good value
                r["fwd_pe"] = prev_fpe.get(t)
                print(f"peg: OVERVIEW {t} failed ({ex}); carried forward")

    for r in rows:
        for k in ("peg_yoy", "peg_cagr3", "peg_cagr5", "peg_lin", "peg_fwd", "fwd_pe"):
            if isinstance(r.get(k), float):
                r[k] = round(r[k], 4)

    json.dump(rows, open(LR, "w"), separators=(",", ":"))
    print(f"peg: wrote {len(rows)} rows" +
          (f"; forward PEG for {n_fwd} from Alpha Vantage" if fetch_forward else
           " (trailing only)"))


if __name__ == "__main__":
    import sys
    build(fetch_forward="--no-forward" not in sys.argv)
