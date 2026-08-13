"""Derived metrics (v0.4) — per-share values, TTM aggregates, margins, ratios.

Reads the parquet part directories, writes data/parquet/derived_metrics/
  per_quarter.parquet — one row per (ticker, fiscal_date_ending):
      revenue, gross_profit, operating_income, net_income, ocf, capex, fcf,
      shares (best point-in-time count), eps_q, revenue_ps, fcf_ps, book_ps,
      gross_margin, op_margin, net_margin, revenue_ttm, net_income_ttm,
      fcf_ttm, eps_ttm, rev_yoy, ni_yoy
  latest_ratios.parquet — one row per ticker with last close and
      pe_ttm, ps_ttm, pfcf_ttm, pb (computed at build time; daily going
      forward since this runs in the daily job).

Shares selection: prefer edgar:dei, then edgar:us-gaap, then alphavantage,
then weighted-average tags; as-of join (latest count on/before quarter end).
"""

import glob
import os

import pandas as pd

PARQUET = "data/parquet"
OUT = f"{PARQUET}/derived_metrics"

ITEMS = {
    "totalRevenue": "revenue",
    "grossProfit": "gross_profit",
    "operatingIncome": "operating_income",
    "netIncome": "net_income",
    "operatingCashflow": "ocf",
    "capitalExpenditures": "capex",
    "totalShareholderEquity": "equity",
}
SHARE_PREF = {"edgar:dei": 0, "edgar:us-gaap": 1, "alphavantage": 2,
              "edgar:us-gaap-issued": 3, "edgar:wavg-basic": 4,
              "edgar:wavg-diluted": 5}


def _read(table):
    files = glob.glob(f"{PARQUET}/{table}/part_*.parquet")
    if not files:
        single = f"{PARQUET}/{table}.parquet"
        files = [single] if os.path.exists(single) else []
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)


def best_shares(shares: pd.DataFrame) -> pd.DataFrame:
    s = shares.dropna(subset=["shares", "as_of"]).copy()
    s = s[s.shares > 0]
    s["pref"] = s.source.map(SHARE_PREF).fillna(9)
    s = (s.sort_values(["ticker", "as_of", "pref"])
           .drop_duplicates(["ticker", "as_of"], keep="first"))
    return s[["ticker", "as_of", "shares"]].sort_values(["ticker", "as_of"])


def build():
    fund = _read("fundamentals")
    shares = _read("shares_outstanding")
    prices = _read("prices_daily")
    if fund.empty:
        print("derived: no fundamentals yet, skipping")
        return

    f = fund[fund.item.isin(ITEMS)].copy()
    f["metric"] = f["item"].map(ITEMS)
    # a metric can appear on 2 statements (e.g. netIncome) — keep first
    wide = (f.sort_values("statement")
              .drop_duplicates(["ticker", "fiscal_date_ending", "metric"])
              .pivot(index=["ticker", "fiscal_date_ending"],
                     columns="metric", values="value")
              .reset_index())
    wide = wide.sort_values(["ticker", "fiscal_date_ending"])
    wide["fcf"] = wide.get("ocf", pd.NA) - wide.get("capex", pd.NA).fillna(0)

    sh = best_shares(shares)
    wide = pd.merge_asof(
        wide.sort_values("fiscal_date_ending"),
        sh.rename(columns={"as_of": "fiscal_date_ending"})
          .sort_values("fiscal_date_ending"),
        on="fiscal_date_ending", by="ticker", direction="backward")
    wide = wide.sort_values(["ticker", "fiscal_date_ending"])

    g = wide.groupby("ticker", group_keys=False)
    for col, out in (("revenue", "revenue_ttm"), ("net_income", "net_income_ttm"),
                     ("fcf", "fcf_ttm")):
        if col in wide.columns:
            wide[out] = g[col].transform(lambda s: s.rolling(4, min_periods=4).sum())
    for num, den, out in (("gross_profit", "revenue", "gross_margin"),
                          ("operating_income", "revenue", "op_margin"),
                          ("net_income", "revenue", "net_margin")):
        if num in wide.columns:
            wide[out] = wide[num] / wide[den]
    if "revenue" in wide.columns:
        wide["rev_yoy"] = g["revenue"].transform(lambda s: s / s.shift(4) - 1)
    if "net_income" in wide.columns:
        wide["ni_yoy"] = g["net_income"].transform(lambda s: s / s.shift(4) - 1)
    wide["eps_q"] = wide.get("net_income", pd.NA) / wide["shares"]
    wide["eps_ttm"] = wide.get("net_income_ttm", pd.NA) / wide["shares"]
    wide["revenue_ps"] = wide.get("revenue", pd.NA) / wide["shares"]
    wide["fcf_ps"] = wide.get("fcf", pd.NA) / wide["shares"]
    wide["book_ps"] = wide.get("equity", pd.NA) / wide["shares"]

    os.makedirs(OUT, exist_ok=True)
    wide.to_parquet(f"{OUT}/per_quarter.parquet", compression="zstd", index=False)

    if not prices.empty:
        last_px = (prices.sort_values("date").groupby("ticker").tail(1)
                   [["ticker", "date", "adjusted_close", "close"]])
        latest_q = wide.groupby("ticker").tail(1)
        r = last_px.merge(latest_q, on="ticker", how="inner")
        r["pe_ttm"] = r.close / r.eps_ttm
        r["ps_ttm"] = r.close / (r.revenue_ttm / r.shares)
        r["pfcf_ttm"] = r.close / (r.fcf_ttm / r.shares)
        r["pb"] = r.close / r.book_ps
        keep = ["ticker", "date", "close", "adjusted_close", "shares",
                "eps_ttm", "revenue_ttm", "fcf_ttm", "pe_ttm", "ps_ttm",
                "pfcf_ttm", "pb", "gross_margin", "op_margin", "net_margin",
                "rev_yoy", "ni_yoy"]
        comp = _read("companies")
        if not comp.empty:
            r = r.merge(comp[["ticker", "name", "sector"]].drop_duplicates("ticker"),
                        on="ticker", how="left")
            keep = ["name", "sector"] + keep
        out_cols = [c for c in keep if c in r.columns]
        r[out_cols].to_parquet(
            f"{OUT}/latest_ratios.parquet", compression="zstd", index=False)
        # JSON snapshot for the GitHub Pages screener (same-origin, no CORS)
        os.makedirs("docs/data", exist_ok=True)
        shares_yoy = (wide.sort_values(["ticker", "fiscal_date_ending"])
                          .groupby("ticker")
                          .apply(lambda g: g.shares.iloc[-1] / g.shares.iloc[-5] - 1
                                 if len(g) >= 5 and g.shares.iloc[-5] else None,
                                 include_groups=False)
                          .rename("shares_yoy").reset_index())
        rj = r[out_cols].merge(shares_yoy, on="ticker", how="left")
        rj["date"] = rj["date"].astype(str)
        rj.round(4).to_json("docs/data/latest_ratios.json", orient="records")
    print(f"derived: {len(wide):,} quarter rows")


if __name__ == "__main__":
    build()
