"""v0.2/v0.3 full-universe backfill — chunked, resumable, time-budgeted.

Reads etl/run_config.json:
  mode            "full" (S&P500+NDX100 universe) or "pilot" (10 tickers)
  chunk_size      tickers per chunk (default config.CHUNK_SIZE)
  max_tickers     optional cap, for smoke tests
  budget_seconds  soft wall-clock budget; stops cleanly after the current
                  chunk when exceeded (re-run resumes; default 3000)

Resume model: after each ticker completes, a marker JSON is written to
data/state/done/<TICKER>.json (stats + overview fields). After each chunk,
Parquet parts are flushed to data/parquet/<table>/part_<TICKER-RANGE>.parquet
and (when GIT_AUTOCOMMIT=1) committed. A re-run skips tickers with markers.

Per ticker:
  Alpha Vantage: INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW, OVERVIEW,
                 TIME_SERIES_DAILY_ADJUSTED (full)
  SEC EDGAR:     companyfacts -> shares outstanding (5 tag variants) +
                 filed-date index (us-gaap Assets) used to stamp filed_date
                 onto Alpha Vantage fundamentals rows
"""

import datetime as dt
import glob
import json
import os
import subprocess
import sys
import time

import pandas as pd

import av_client
import edgar_client
from config import (AV_MIN_INTERVAL_SECONDS, CHUNK_SIZE, CSCO_REFERENCE,
                    CSCO_REFERENCE_TOLERANCE, PILOT_TICKERS)

RAW_AV = "data/raw/av"
RAW_EDGAR = "data/raw/edgar"
PARQUET = "data/parquet"
STATE = "data/state/done"
REPORTS = "reports"

STATEMENTS = {"income": "INCOME_STATEMENT", "balance": "BALANCE_SHEET",
              "cashflow": "CASH_FLOW"}
TABLES = ("fundamentals", "prices_daily", "shares_outstanding", "companies")


# ------------------------------------------------------------------ flattening
def flatten_statement(payload, ticker, statement, filed_index):
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
                continue
            rows.append({"ticker": ticker, "fiscal_date_ending": fde,
                         "statement": statement, "item": item, "value": value,
                         "currency": cur, "source": "alphavantage",
                         "filed_date": filed_index.get(fde)})
    return rows


def flatten_prices(payload, ticker):
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


def av_fallback_shares(balance_payload, ticker):
    rows = []
    for rep in balance_payload.get("quarterlyReports", []):
        try:
            shares = float(rep.get("commonStockSharesOutstanding"))
        except (TypeError, ValueError):
            continue
        rows.append({"ticker": ticker, "as_of": rep.get("fiscalDateEnding"),
                     "shares": shares, "source": "alphavantage",
                     "filed_date": None})
    return rows


# ------------------------------------------------------------------ per ticker
def process_ticker(t, cik, buf):
    # cik may arrive as NaN (float) from a failed map lookup — only a digit
    # string is usable (v0.2.2 fix: NaN is truthy, broke AEP in v0.2.1).
    cik = cik if isinstance(cik, str) and cik.isdigit() else None
    stats = {"ticker": t, "cik": cik}
    filed_index = {}
    shares_rows = []

    if cik:
        try:
            facts = edgar_client.fetch_companyfacts(cik)
            shares_rows = edgar_client.extract_shares_outstanding(facts, t)
            filed_index = edgar_client.extract_filed_date_index(facts)
            edgar_client.save_raw_filtered(shares_rows, filed_index,
                                           f"{RAW_EDGAR}/{t}_extract.json.gz")
        except Exception as e:  # noqa: BLE001 — EDGAR failure must not kill AV pull
            stats["edgar_error"] = f"{type(e).__name__}: {e}"[:200]
    stats["edgar_share_points"] = len(shares_rows)
    stats["edgar_oldest"] = min((r["as_of"] for r in shares_rows), default=None)

    balance_payload = None
    for stmt, fn in STATEMENTS.items():
        payload = av_client.fetch(fn, t, AV_MIN_INTERVAL_SECONDS)
        av_client.save_raw(payload, f"{RAW_AV}/{t}_{stmt}.json.gz")
        if stmt == "balance":
            balance_payload = payload
        rows = flatten_statement(payload, t, stmt, filed_index)
        buf["fundamentals"] += rows
        if stmt == "income":
            q = payload.get("quarterlyReports", [])
            stats["av_quarters"] = len(q)
            stats["av_oldest"] = q[-1]["fiscalDateEnding"] if q else None

    buf["shares_outstanding"] += shares_rows
    buf["shares_outstanding"] += av_fallback_shares(balance_payload or {}, t)

    ov = av_client.fetch("OVERVIEW", t, AV_MIN_INTERVAL_SECONDS)
    av_client.save_raw(ov, f"{RAW_AV}/{t}_overview.json.gz")
    company = {"ticker": t, "cik": cik, "name": ov.get("Name"),
               "exchange": ov.get("Exchange"), "sector": ov.get("Sector"),
               "industry": ov.get("Industry"),
               "fiscal_year_end": ov.get("FiscalYearEnd")}
    buf["companies"].append(company)

    px = av_client.fetch("TIME_SERIES_DAILY_ADJUSTED", t, AV_MIN_INTERVAL_SECONDS,
                         extra={"outputsize": "full"})
    av_client.save_raw(px, f"{RAW_AV}/{t}_prices.json.gz")
    p = flatten_prices(px, t)
    buf["prices_daily"] += p
    stats["price_days"] = len(p)
    stats["price_oldest"] = min((r["date"] for r in p), default=None)
    stats["company"] = company
    return stats


# ------------------------------------------------------------------ chunk I/O
def flush_chunk(buf, label):
    for table in TABLES:
        rows = buf[table]
        if not rows:
            continue
        df = pd.DataFrame(rows)
        for col in ("fiscal_date_ending", "date", "as_of", "filed_date"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        os.makedirs(f"{PARQUET}/{table}", exist_ok=True)
        df.to_parquet(f"{PARQUET}/{table}/part_{label}.parquet",
                      compression="zstd", index=False)
        buf[table] = []


def git_autocommit(msg):
    if os.environ.get("GIT_AUTOCOMMIT") != "1":
        return
    ident = ["-c", "user.name=etl-bot", "-c", "user.email=actions@github.com"]
    for cmd in (["git", "add", "-A"],
                ["git", *ident, "commit", "-m", msg + " [skip ci]"],
                ["git", "push"]):
        p = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if p.returncode and cmd[-1] == "push":
            print(f"autocommit push failed: {p.stderr[:200]}", flush=True)


def mark_done(stats):
    os.makedirs(STATE, exist_ok=True)
    with open(f"{STATE}/{stats['ticker']}.json", "w") as f:
        json.dump(stats, f)


def load_done():
    out = {}
    for p in glob.glob(f"{STATE}/*.json"):
        with open(p) as f:
            s = json.load(f)
        out[s["ticker"]] = s
    return out


# ------------------------------------------------------------------ QA report
def write_qa(done, failed, incomplete, universe_size):
    os.makedirs(REPORTS, exist_ok=True)
    lines = [f"# Full backfill QA report (v0.2) — "
             f"{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC\n"]
    lines.append(f"- Universe size: **{universe_size}**")
    lines.append(f"- Completed tickers: **{len(done)}**")
    lines.append(f"- Failed tickers: **{len(failed)}**")
    lines.append(f"- Run incomplete (budget hit): **{incomplete}**\n")

    zero_shares = sorted(t for t, s in done.items()
                         if not s.get("edgar_share_points"))
    lines.append(f"## EDGAR shares coverage\n")
    lines.append(f"- Tickers with 0 EDGAR share points: {len(zero_shares)}"
                 f" {zero_shares[:20] if zero_shares else ''}")
    for t in ("META", "XOM"):
        s = done.get(t, {})
        lines.append(f"- {t}: **{s.get('edgar_share_points', 'not run')}** share "
                     f"points (v0.1 was META=0, XOM=7)")
    lines.append("")

    if failed:
        lines.append("## Failures\n")
        for t, err in sorted(failed.items()):
            lines.append(f"- {t}: `{err[:200]}`")
        lines.append("")

    # coverage census CSV
    census = pd.DataFrame([{k: v for k, v in s.items() if k != "company"}
                           for s in done.values()])
    census_path = f"{REPORTS}/coverage_census_v0.2.csv"
    if not census.empty:
        census.sort_values("ticker").to_csv(census_path, index=False)
        lines.append(f"Full per-ticker census: `{census_path}`\n")
        lines.append("## Aggregate coverage\n")
        lines.append(f"- Median AV quarters: {census.av_quarters.median():.0f}")
        lines.append(f"- Tickers with >=40 quarters (10y): "
                     f"{(census.av_quarters >= 40).sum()}/{len(census)}")
        lines.append(f"- Median price days: {census.price_days.median():.0f}")
        lines.append(f"- Median EDGAR share points: "
                     f"{census.edgar_share_points.median():.0f}")

    # CSCO revalidation
    failures = 0
    fund_files = glob.glob(f"{PARQUET}/fundamentals/part_*.parquet")
    if fund_files and "CSCO" in done:
        fund = pd.concat([pd.read_parquet(p) for p in fund_files])
        ref_date = pd.Timestamp(CSCO_REFERENCE["fiscal_date_ending"])
        csco = fund[(fund.ticker == "CSCO") & (fund.fiscal_date_ending == ref_date)]
        lines.append("\n## CSCO validation vs Yahoo reference\n")
        lines.append("| item | expected | got | diff | pass |")
        lines.append("|---|---|---|---|---|")
        for item, expected in CSCO_REFERENCE.items():
            if item == "fiscal_date_ending":
                continue
            got = csco[csco.item == item]["value"]
            if got.empty:
                lines.append(f"| {item} | {expected:.3g} | MISSING | — | FAIL |")
                failures += 1
                continue
            got = float(got.iloc[0])
            diff = abs(got - expected) / expected
            ok = diff <= CSCO_REFERENCE_TOLERANCE
            failures += (not ok)
            lines.append(f"| {item} | {expected:.4g} | {got:.4g} | {diff:.2%} | "
                         f"{'PASS' if ok else 'FAIL'} |")

    lines.append(f"\n**Validation failures: {failures}**")
    with open(f"{REPORTS}/backfill_qa_v0.2.md", "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return failures


# ------------------------------------------------------------------ main
def main():
    cfg = {}
    if os.path.exists("etl/run_config.json"):
        with open("etl/run_config.json") as f:
            cfg = json.load(f)
    mode = cfg.get("mode", "full")
    chunk_size = int(cfg.get("chunk_size", CHUNK_SIZE))
    budget = float(cfg.get("budget_seconds", 3000))
    start = time.time()

    if mode == "pilot":
        cik_map = edgar_client.ticker_to_cik_map()
        tickers = PILOT_TICKERS
        uni = pd.DataFrame({"ticker": tickers})
        uni["cik"] = uni.ticker.map(cik_map)
    else:
        import universe
        uni = universe.build()
    if cfg.get("max_tickers"):
        uni = uni.head(int(cfg["max_tickers"]))
    cik_of = dict(zip(uni.ticker, uni.cik))

    # v0.1 wrote single-file parquets; v0.2 canonical layout is per-table
    # directories of parts. Remove the legacy files so queries never double-count.
    for legacy in TABLES:
        p = f"{PARQUET}/{legacy}.parquet"
        if os.path.exists(p):
            os.remove(p)

    # Weekly refresh: CLEAR_STATE=1 wipes the done markers so every ticker is
    # re-pulled (catches restatements). Parquet parts are overwritten in place.
    if os.environ.get("CLEAR_STATE") == "1":
        for pth in glob.glob(f"{STATE}/*.json"):
            os.remove(pth)
        print("CLEAR_STATE=1 — full refresh of all tickers")

    done = load_done()
    todo = [t for t in uni.ticker if t not in done]
    print(f"{len(done)} already done, {len(todo)} to fetch "
          f"(chunk={chunk_size}, budget={budget:.0f}s)")

    failed, incomplete = {}, False
    for ci in range(0, len(todo), chunk_size):
        if time.time() - start > budget:
            incomplete = True
            print("Budget exceeded — stopping cleanly (re-run to resume).")
            break
        chunk = todo[ci:ci + chunk_size]
        buf = {t: [] for t in TABLES}
        for t in chunk:
            try:
                stats = process_ticker(t, cik_of.get(t), buf)
                mark_done(stats)
                done[t] = stats
                print(f"OK {t}: {stats.get('av_quarters')}q "
                      f"{stats.get('price_days')}d "
                      f"{stats.get('edgar_share_points')}sh", flush=True)
            except Exception as e:  # noqa: BLE001 — record and continue
                failed[t] = f"{type(e).__name__}: {e}"
                print(f"FAIL {t}: {failed[t]}", flush=True)
        label = f"{chunk[0]}_{chunk[-1]}".replace("-", "")
        flush_chunk(buf, label)
        git_autocommit(f"v0.2 backfill chunk {label}: "
                       f"{len(done)}/{len(uni)} tickers")

    qa_failures = write_qa(done, failed, incomplete, len(uni))
    git_autocommit(f"v0.2 backfill QA report ({len(done)}/{len(uni)} done)")

    fail_rate = len(failed) / max(len(uni), 1)
    if incomplete:
        print("PARTIAL RUN — dispatch again to resume.")
        return 0
    return 1 if (qa_failures or fail_rate > 0.05) else 0


if __name__ == "__main__":
    sys.exit(main())
