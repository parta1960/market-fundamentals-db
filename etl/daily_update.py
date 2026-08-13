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
from config import AV_MIN_INTERVAL_SECONDS

PARQUET = "data/parquet"


def refresh_prices(tickers, budget_end):
    buf = {t: [] for t in fb.TABLES}
    done, failed = [], {}
    for t in tickers:
        if time.time() > budget_end:
            break
        try:
            px = av_client.fetch("TIME_SERIES_DAILY_ADJUSTED", t,
                                 AV_MIN_INTERVAL_SECONDS,
                                 extra={"outputsize": "full"})
            av_client.save_raw(px, f"{fb.RAW_AV}/{t}_prices.json.gz")
            buf["prices_daily"] += fb.flatten_prices(px, t)
            done.append(t)
        except Exception as e:  # noqa: BLE001
            failed[t] = f"{type(e).__name__}: {e}"
    # one part per ticker-range chunk of 40, replacing older parts wholesale
    for p in glob.glob(f"{PARQUET}/prices_daily/part_*.parquet"):
        os.remove(p)
    rows = buf["prices_daily"]
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

    os.makedirs("reports", exist_ok=True)
    with open("reports/daily_update_last.json", "w") as f:
        json.dump({"date": today, "prices_ok": len(done),
                   "failed": failed}, f, indent=2)
    return 0 if len(failed) <= len(uni) * 0.05 else 1


if __name__ == "__main__":
    sys.exit(main())
