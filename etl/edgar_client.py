"""SEC EDGAR client — ticker->CIK map, companyfacts, shares extraction (v0.2).

v0.2 changes vs v0.1:
  * Shares-outstanding extraction broadened to 5 tag/namespace variants
    (v0.1 got 0 points for META and 7 for XOM with only 2 tags).
  * filed-date index: maps fiscal period end -> earliest filing date using the
    us-gaap Assets series (present in every 10-Q/10-K balance sheet), used to
    enrich Alpha Vantage fundamentals rows with filed_date.
  * save_raw_filtered: stores only the extracted series, not the full
    companyfacts blob (full blobs for 520 tickers would be ~0.5 GB of git).
"""

import gzip
import json
import os
import time

import requests

from config import EDGAR_FACTS_URL, EDGAR_TICKERS_URL, EDGAR_USER_AGENT, SHARES_TAG_SOURCES

HEADERS = {"User-Agent": EDGAR_USER_AGENT, "Accept-Encoding": "gzip"}
_MIN_INTERVAL = 0.15  # stay well under SEC's 10 req/s guidance


def _get(url: str) -> requests.Response:
    last = getattr(_get, "_last", 0.0)
    wait = _MIN_INTERVAL - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    r = requests.get(url, headers=HEADERS, timeout=90)
    _get._last = time.time()
    r.raise_for_status()
    return r


def ticker_to_cik_map() -> dict[str, str]:
    data = _get(EDGAR_TICKERS_URL).json()
    return {row["ticker"].upper(): f"{row['cik_str']:010d}" for row in data.values()}


def fetch_companyfacts(cik: str) -> dict:
    return _get(EDGAR_FACTS_URL.format(cik=cik)).json()


def save_raw(payload: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt") as f:
        json.dump(payload, f)


def extract_shares_outstanding(facts: dict, ticker: str) -> list[dict]:
    """Pull shares series from all configured tag variants, deduplicated.

    Dedup key is (as_of, source): different filings restate the same period end;
    we keep the first-seen value per tag source. Preferred sources come first in
    SHARES_TAG_SOURCES, and downstream consumers should prefer edgar:dei, then
    edgar:us-gaap, falling back to weighted-average tags only when point-in-time
    counts are absent.
    """
    rows, seen = [], set()
    for ns, tag, label in SHARES_TAG_SOURCES:
        node = facts.get("facts", {}).get(ns, {}).get(tag, {})
        for unit_rows in node.get("units", {}).values():
            for it in unit_rows:
                val, end = it.get("val"), it.get("end")
                if val is None or not end:
                    continue
                key = (end, label)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "ticker": ticker,
                    "as_of": end,
                    "shares": float(val),
                    "source": label,
                    "filed_date": it.get("filed"),
                })
    return rows


def extract_filed_date_index(facts: dict) -> dict[str, str]:
    """Map fiscal period end date -> earliest filed date, from us-gaap Assets."""
    out: dict[str, str] = {}
    node = facts.get("facts", {}).get("us-gaap", {}).get("Assets", {})
    for unit_rows in node.get("units", {}).values():
        for it in unit_rows:
            end, filed = it.get("end"), it.get("filed")
            if not end or not filed:
                continue
            if end not in out or filed < out[end]:
                out[end] = filed
    return out


def save_raw_filtered(shares_rows: list[dict], filed_index: dict, path: str) -> None:
    save_raw({"shares": shares_rows, "filed_index": filed_index}, path)
