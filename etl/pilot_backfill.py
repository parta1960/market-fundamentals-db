"""v0.1 pilot: end-to-end pipeline for 10 tickers.

Steps:
  1. Measure the Alpha Vantage key's real rate limit (informs all later versions).
  2. Pull 3 quarterly statements + OVERVIEW + full daily adjusted prices per ticker (AV).
  3. Pull EDGAR companyfacts per ticker; extract shares outstanding.
  4. Normalize everything to Parquet.
  5. Write a QA report (depth per source, CSCO validation vs Yahoo reference, gaps).
"""

import datetime as dt
import json
import os
import sys

import pandas as pd

import av_client
import edgar_client
from config import CSCO_REFERENCE, CSCO_REFERENCE_TOLERANCE, PILOT_TICKERS

RAW_AV = "data/raw/av"
RAW_EDGAR = "data/raw/edgar"
PARQUET = "data/parquet"
REPORTS = "reports"

STATEMENTS = {
    "income": "INCOME_STATEMENT",
    "balance": "BALANCE_SHEET",
    "cashflow": "CASH_FLOW",
}


def flatten_statement(payload: dict, ticker: str, statement: str) -> list[dict]:
    rows = []
    for rep in payload.get("quarterlyReports", []):
        fde = rep.get("fiscalDateEnding")
        cur = rep.get("reportedCurrency")
        for item, raw in rep.items():
            if item in ("fiscalDateEnding", "reportedCurrency"):
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue  # "None" strings
            rows.append({"ticker": ticker, "fiscal_date_ending": fde,
                         "statement": statement, "item": item, "value": value,
                         "currency": cur, "source": "alphavantage", "filed_date": None})
    return rows


def flatten_prices(payload: dict, ticker: str) -> list[dict]:
    series = payload.get("Time Series (Daily)", {})
    rows = []
    for date, v in series.items():
        rows.append({
            "ticker": ticker, "date": date,
            "open": float(v["1. open"]), "high": float(v["2. high"]),
            "low": float(v["3. low"]), "close": float(v["4. close"]),
            "adjusted_close": float(v["5. adjusted close"]),
            "volume": int(v["6. volume"]),
            "dividend_amount": float(v["7. dividend amount"]),
            "split_coefficient": float(v["8. split coefficient"]),
        })
    return rows


def main() -> int:
    os.makedirs(PARQUET, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)
    report = [f"# Pilot backfill QA report — {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC\n"]

    # --- 1. rate-limit measurement -------------------------------------------------
    rate = av_client.measure_rate_limit()
    report.append("## Alpha Vantage rate-limit measurement\n")
    report.append(f"- Successful calls in {rate['elapsed_seconds']}s: **{rate['calls_ok']}**")
    report.append(f"- Inferred tier: **{rate['inferred_tier']}**")
    if rate["first_limit_message"]:
        report.append(f"- Limit message: `{rate['first_limit_message']}`")
    report.append("")
    # Pace subsequent calls conservatively from what we measured.
    min_interval = 1.0 if rate["calls_ok"] >= 40 else 15.0

    # --- 2 & 3. per-ticker pulls ----------------------------------------------------
    fund_rows, price_rows, share_rows, company_rows = [], [], [], []
    depth = {}
    cik_map = edgar_client.ticker_to_cik_map()

    for t in PILOT_TICKERS:
        print(f"--- {t}", flush=True)
        # Alpha Vantage
        for stmt, fn in STATEMENTS.items():
            payload = av_client.fetch(fn, t, min_interval)
            av_client.save_raw(payload, f"{RAW_AV}/{t}_{stmt}.json.gz")
            rows = flatten_statement(payload, t, stmt)
            fund_rows += rows
            if stmt == "income":
                q = payload.get("quarterlyReports", [])
                depth[t] = {"av_quarters": len(q),
                            "av_oldest": q[-1]["fiscalDateEnding"] if q else None}
        ov = av_client.fetch("OVERVIEW", t, min_interval)
        av_client.save_raw(ov, f"{RAW_AV}/{t}_overview.json.gz")
        company_rows.append({"ticker": t, "cik": cik_map.get(t),
                             "name": ov.get("Name"), "exchange": ov.get("Exchange"),
                             "sector": ov.get("Sector"), "industry": ov.get("Industry"),
                             "fiscal_year_end": ov.get("FiscalYearEnd")})
        px = av_client.fetch("TIME_SERIES_DAILY_ADJUSTED", t, min_interval,
                             extra={"outputsize": "full"})
        av_client.save_raw(px, f"{RAW_AV}/{t}_prices.json.gz")
        p = flatten_prices(px, t)
        price_rows += p
        depth[t]["price_days"] = len(p)
        depth[t]["price_oldest"] = min((r["date"] for r in p), default=None)

        # EDGAR
        cik = cik_map.get(t)
        if cik:
            facts = edgar_client.fetch_companyfacts(cik)
            edgar_client.save_raw(facts, f"{RAW_EDGAR}/{t}_companyfacts.json.gz")
            sh = edgar_client.extract_shares_outstanding(facts, t)
            share_rows += sh
            depth[t]["edgar_share_points"] = len(sh)
            depth[t]["edgar_oldest"] = min((r["as_of"] for r in sh), default=None)
            n_tags = sum(len(v) for v in facts.get("facts", {}).values())
            depth[t]["edgar_tags"] = n_tags
        else:
            depth[t]["edgar_share_points"] = 0

    # --- 4. write parquet -----------------------------------------------------------
    fund = pd.DataFrame(fund_rows)
    fund["fiscal_date_ending"] = pd.to_datetime(fund["fiscal_date_ending"])
    fund.to_parquet(f"{PARQUET}/fundamentals.parquet", compression="zstd", index=False)

    prices = pd.DataFrame(price_rows)
    prices["date"] = pd.to_datetime(prices["date"])
    prices.to_parquet(f"{PARQUET}/prices_daily.parquet", compression="zstd", index=False)

    shares = pd.DataFrame(share_rows)
    for c in ("as_of", "filed_date"):
        shares[c] = pd.to_datetime(shares[c])
    shares.to_parquet(f"{PARQUET}/shares_outstanding.parquet", compression="zstd", index=False)

    pd.DataFrame(company_rows).to_parquet(f"{PARQUET}/companies.parquet", index=False)

    # --- 5. QA report ----------------------------------------------------------------
    report.append("## Coverage depth per ticker\n")
    report.append("| ticker | AV quarters | AV oldest | price days | price oldest | EDGAR share pts | EDGAR oldest |")
    report.append("|---|---|---|---|---|---|---|")
    for t in PILOT_TICKERS:
        d = depth.get(t, {})
        report.append(f"| {t} | {d.get('av_quarters')} | {d.get('av_oldest')} | "
                      f"{d.get('price_days')} | {d.get('price_oldest')} | "
                      f"{d.get('edgar_share_points')} | {d.get('edgar_oldest')} |")
    report.append("")

    # CSCO validation against Yahoo reference values
    report.append("## CSCO validation vs Yahoo Finance reference (quarter ending "
                  f"{CSCO_REFERENCE['fiscal_date_ending']})\n")
    report.append("| item | expected | got | diff | pass |")
    report.append("|---|---|---|---|---|")
    failures = 0
    ref_date = pd.Timestamp(CSCO_REFERENCE["fiscal_date_ending"])
    csco = fund[(fund.ticker == "CSCO") & (fund.fiscal_date_ending == ref_date)]
    for item, expected in CSCO_REFERENCE.items():
        if item == "fiscal_date_ending":
            continue
        got = csco[csco.item == item]["value"]
        if got.empty:
            report.append(f"| {item} | {expected:.3g} | MISSING | — | FAIL |")
            failures += 1
            continue
        got = float(got.iloc[0])
        diff = abs(got - expected) / expected
        ok = diff <= CSCO_REFERENCE_TOLERANCE
        failures += (not ok)
        report.append(f"| {item} | {expected:.4g} | {got:.4g} | {diff:.2%} | "
                      f"{'PASS' if ok else 'FAIL'} |")
    report.append("")

    # file sizes
    report.append("## Output sizes\n")
    for root, _, files in os.walk("data"):
        for f in sorted(files):
            p = os.path.join(root, f)
            report.append(f"- `{p}`: {os.path.getsize(p)/1e6:.2f} MB")
    report.append(f"\nRow counts: fundamentals={len(fund):,}, prices={len(prices):,}, "
                  f"shares={len(shares):,}")
    report.append(f"\n**Validation failures: {failures}**")

    out = f"{REPORTS}/pilot_qa_v0.1.md"
    with open(out, "w") as f:
        f.write("\n".join(report))
    with open(f"{REPORTS}/rate_limit.json", "w") as f:
        json.dump(rate, f, indent=2)
    print("\n".join(report))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
