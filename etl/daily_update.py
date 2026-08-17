"""v0.4 daily update — weekdays after US close.

Design (leverages the measured >=150/min premium AV key):
  * PRICES: re-pull the FULL adjusted daily series for every ticker
    (~520 calls ~= 4-6 min). Full re-pull, not append, so dividend/split
    adjustment revisions are always correct. Overwrites prices parts.
  * FUNDAMENTALS + EDGAR shares/filed-dates: refreshed only for tickers whose
    latest EDGAR filing is newer than what we have (checked via the cheap
    submissions API), plus a full weekly sweep on Mondays (restatements).
  * UNIVERSE: membership snapshot appended on Mondays (dated rows — this is
    what makes v2.0 point-in-time possible later).
  * DERIVED: rebuild derived_metrics parquet (see derived.py) daily.

Resumable the same way as full_backfill (state markers under
data/state/daily/<YYYY-MM-DD>/). Time budget default 45 min.
"""

import datetime as dt
import glob
import json
import os
import sys
import time

import pandas as pd

import av_client
import derived
import edgar_client
import full_backfill as fb
import history_export
from config import AV_MIN_INTERVAL_SECONDS

PARQUET = "data/parquet"


def _pull_prices(t):
    """Fetch one ticker's full adjusted daily series. Raises unless it yields rows.

    Guard added after 2026-08-17: AV answered 200 OK with an empty body `{}` for
    AAPL. The old code treated that as success, so AAPL landed in `done` with
    zero rows, was therefore NOT carried forward, and its entire price history
    was deleted by the parts rewrite below — which in turn removed its split
    events and silently un-split-adjusted every per-share series. An empty
    result is a failure, never a success.
    """
    px = av_client.fetch("TIME_SERIES_DAILY_ADJUSTED", t,
                         AV_MIN_INTERVAL_SECONDS,
                         extra={"outputsize": "full"},
                         require="Time Series (Daily)")
    rows = fb.flatten_prices(px, t)
    if not rows:
        raise ValueError(f"{t}: zero price rows returned")
    av_client.save_raw(px, f"{fb.RAW_AV}/{t}_prices.json.gz")
    return rows


def refresh_prices(tickers, budget_end):
    buf = {t: [] for t in fb.TABLES}
    done, failed = [], {}
    for t in tickers:
        if time.time() > budget_end:
            break
        try:
            rows = _pull_prices(t)
            buf["prices_daily"] += rows
            done.append(t)
        except Exception as e:  # noqa: BLE001
            failed[t] = f"{type(e).__name__}: {e}"
    # One retry pass for transient AV failures (e.g. sporadic 'Invalid API call')
    for t in list(failed):
        if time.time() > budget_end:
            break
        try:
            time.sleep(2)
            rows = _pull_prices(t)
            buf["prices_daily"] += rows
            done.append(t)
            del failed[t]
        except Exception as e:  # noqa: BLE001
            failed[t] = f"retry: {type(e).__name__}: {e}"
    # Safety: only replace the existing prices table if the refresh
    # succeeded for the overwhelming majority of tickers. Otherwise keep
    # yesterday's parts intact (a partial delete+rewrite would shrink the
    # table and the always() commit step would persist the damage).
    if len(done) < 0.9 * len(tickers):
        print(f"only {len(done)}/{len(tickers)} refreshed — keeping old parts")
        return done, failed
    old_files = glob.glob(f"{PARQUET}/prices_daily/part_*.parquet")
    prev = pd.DataFrame()
    if old_files:
        prev = pd.concat([pd.read_parquet(p) for p in old_files], ignore_index=True)
    rows = buf["prices_daily"]
    # Truncation guard: a full re-pull can only grow a series, so a ticker whose
    # fresh history is materially shorter than yesterday's did not really
    # refresh. These parts ARE the price archive, so overwriting on a short
    # body loses history permanently (and, with it, the split events that every
    # per-share series is normalised by). Demote such tickers to carry-forward.
    if not prev.empty and rows:
        newc = pd.Series([r["ticker"] for r in rows]).value_counts()
        oldc = prev.ticker.value_counts()
        shrunk = {t for t in done
                  if t in oldc.index and newc.get(t, 0) < 0.9 * oldc[t]}
        if shrunk:
            print(f"truncated refresh — keeping old prices for {sorted(shrunk)}")
            done = [t for t in done if t not in shrunk]
            rows = [r for r in rows if r["ticker"] not in shrunk]
            for t in shrunk:
                failed[t] = "truncated refresh (previous history kept)"
    missing = [t for t in tickers if t not in set(done)]
    carry = pd.DataFrame()
    if missing and not prev.empty:
        carry = prev[prev.ticker.isin(missing)]
        print(f"carrying forward yesterday's prices for {sorted(missing)}")
    for p in old_files:
        os.remove(p)
    if not carry.empty:
        os.makedirs(f"{PARQUET}/prices_daily", exist_ok=True)
        carry.to_parquet(f"{PARQUET}/prices_daily/part_CARRYOVER.parquet",
                         compression="zstd", index=False)
    for i in range(0, len(done), 40):
        chunk = set(done[i:i + 40])
        sub = [r for r in rows if r["ticker"] in chunk]
        label = f"{done[i]}_{done[min(i + 39, len(done) - 1)]}".replace("-", "")
        fb.flush_chunk({**{k: [] for k in fb.TABLES}, "prices_daily": sub}, label)
    return done, failed


def main():
    budget_end = time.time() + float(os.environ.get("DAILY_BUDGET_SECONDS", 2700))
    uni = pd.read_csv("data/universe/universe_latest.csv")
    today = dt.date.today().isoformat()

    done, failed = refresh_prices(list(uni.ticker), budget_end)
    print(f"prices refreshed for {len(done)}/{len(uni)}; {len(failed)} failed")

    # Monday: refresh membership snapshot + full fundamentals/EDGAR sweep is
    # triggered by dispatching the backfill workflow instead (state cleared).
    if dt.date.today().weekday() == 0:
        import universe
        universe.build()

    derived.build()
    history_export.build()

    os.makedirs("reports", exist_ok=True)
    with open("reports/daily_update_last.json", "w") as f:
        json.dump({"date": today, "prices_ok": len(done),
                   "failed": failed}, f, indent=2)
    return 0 if len(failed) <= len(uni) * 0.05 else 1


if __name__ == "__main__":
    sys.exit(main())
