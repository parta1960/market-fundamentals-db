"""Universe builder — S&P 500 + Nasdaq-100 constituents with CIK mapping (v0.2).

Scrapes the two Wikipedia constituent lists, normalizes tickers, joins SEC CIKs,
and writes:
  data/parquet/index_membership.parquet  (dated snapshot rows, appended)
  data/universe/universe_<date>.csv      (human-readable snapshot)

Ticker normalization: Wikipedia uses dots for share classes (BRK.B); both
Alpha Vantage and SEC's ticker file use dashes (BRK-B). We store the dashed
form as the canonical ticker.
"""

import datetime as dt
import io
import os
import re

import pandas as pd
import requests

import edgar_client
from config import (CIK_OVERRIDES, NDX_EXPECTED_RANGE, NDX_URL, SP500_EXPECTED_RANGE,
                    SP500_URL, WIKI_USER_AGENT)

PARQUET = "data/parquet"
UNIVERSE_DIR = "data/universe"
# Committed Russell 1000 (IWB) + 2000 (IWM) membership snapshot with
# SEC-canonical tickers + CIKs. Built from the iShares holdings CSVs via a
# browser (iShares blocks CI/urllib), so the pipeline reads a static file
# rather than fetching iShares from GitHub Actions. Refresh at reconstitution.
RUSSELL_FILE = f"{UNIVERSE_DIR}/russell_membership.csv"


def _load_russell() -> pd.DataFrame:
    if not os.path.exists(RUSSELL_FILE):
        return pd.DataFrame(columns=["ticker", "name", "index", "cik"])
    df = pd.read_csv(RUSSELL_FILE, dtype=str).fillna("")
    df["ticker"] = df["ticker"].map(_norm)
    return df


def _tables(url: str) -> list[pd.DataFrame]:
    r = requests.get(url, headers={"User-Agent": WIKI_USER_AGENT}, timeout=60)
    r.raise_for_status()
    return pd.read_html(io.StringIO(r.text))


def _norm(ticker: str) -> str:
    return re.sub(r"\.", "-", str(ticker).strip().upper())


def fetch_sp500() -> pd.DataFrame:
    for tbl in _tables(SP500_URL):
        cols = {str(c).lower() for c in tbl.columns}
        if "symbol" in cols and ("security" in cols or "company" in cols):
            tbl.columns = [str(c).lower() for c in tbl.columns]
            name_col = "security" if "security" in tbl.columns else "company"
            out = pd.DataFrame({
                "ticker": tbl["symbol"].map(_norm),
                "name": tbl[name_col],
                "sector_wiki": tbl.get("gics sector"),
            })
            return out.dropna(subset=["ticker"]).drop_duplicates("ticker")
    raise RuntimeError("S&P 500 constituents table not found on Wikipedia page")


def fetch_ndx() -> pd.DataFrame:
    for tbl in _tables(NDX_URL):
        cols = [str(c).lower() for c in tbl.columns]
        if ("ticker" in cols or "symbol" in cols) and len(tbl) > 50:
            tbl.columns = cols
            tick_col = "ticker" if "ticker" in cols else "symbol"
            name_col = next((c for c in ("company", "security") if c in cols), None)
            out = pd.DataFrame({
                "ticker": tbl[tick_col].map(_norm),
                "name": tbl[name_col] if name_col else None,
            })
            return out.dropna(subset=["ticker"]).drop_duplicates("ticker")
    raise RuntimeError("Nasdaq-100 constituents table not found on Wikipedia page")


def build(as_of: str | None = None) -> pd.DataFrame:
    as_of = as_of or dt.date.today().isoformat()
    sp = fetch_sp500()
    ndx = fetch_ndx()

    n_sp, n_ndx = len(sp), len(ndx)
    if not (SP500_EXPECTED_RANGE[0] <= n_sp <= SP500_EXPECTED_RANGE[1]):
        raise RuntimeError(f"S&P 500 scrape suspicious: {n_sp} tickers")
    if not (NDX_EXPECTED_RANGE[0] <= n_ndx <= NDX_EXPECTED_RANGE[1]):
        raise RuntimeError(f"Nasdaq-100 scrape suspicious: {n_ndx} tickers")

    russ = _load_russell()

    memb = [
        pd.DataFrame({"ticker": sp.ticker, "index_name": "SP500", "as_of": as_of}),
        pd.DataFrame({"ticker": ndx.ticker, "index_name": "NDX100", "as_of": as_of}),
    ]
    for idx_tag, name in (("IWB", "RUSSELL1000"), ("IWM", "RUSSELL2000")):
        sub = russ[russ["index"] == idx_tag]
        if not sub.empty:
            memb.append(pd.DataFrame({"ticker": sub.ticker, "index_name": name,
                                      "as_of": as_of}))
    membership = pd.concat(memb, ignore_index=True)

    # unique universe with names + CIKs (S&P 500 + Nasdaq-100 + Russell 1000/2000)
    frames = [sp[["ticker", "name"]], ndx[["ticker", "name"]]]
    if not russ.empty:
        frames.append(russ[["ticker", "name"]])
    uni = pd.concat(frames, ignore_index=True).drop_duplicates("ticker").reset_index(drop=True)
    cik = edgar_client.ticker_to_cik_map()
    uni["cik"] = uni.ticker.map(cik)
    missing = uni.cik.isna()
    uni.loc[missing, "cik"] = uni.loc[missing, "ticker"].map(CIK_OVERRIDES)
    # backfill any still-missing CIKs from the Russell file's own CIK column
    if not russ.empty:
        rcik = {t: c for t, c in zip(russ.ticker, russ.cik) if c}
        still = uni.cik.isna()
        uni.loc[still, "cik"] = uni.loc[still, "ticker"].map(rcik)

    os.makedirs(PARQUET, exist_ok=True)
    os.makedirs(UNIVERSE_DIR, exist_ok=True)

    membership["as_of"] = pd.to_datetime(membership["as_of"])
    path = f"{PARQUET}/index_membership.parquet"
    if os.path.exists(path):
        prev = pd.read_parquet(path)
        membership = pd.concat([prev, membership], ignore_index=True).drop_duplicates()
    membership.to_parquet(path, compression="zstd", index=False)

    uni.to_csv(f"{UNIVERSE_DIR}/universe_{as_of}.csv", index=False)
    uni.to_csv(f"{UNIVERSE_DIR}/universe_latest.csv", index=False)
    n_russ = len(russ)
    print(f"Universe: {len(uni)} unique tickers ({n_sp} SP500, {n_ndx} NDX100, "
          f"{n_russ} Russell rows), {uni.cik.notna().sum()} with CIK")
    return uni


if __name__ == "__main__":
    build()
