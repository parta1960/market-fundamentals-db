"""SEC EDGAR client: ticker->CIK mapping and companyfacts download."""

import gzip
import json
import os
import time

import requests

from config import EDGAR_FACTS_URL, EDGAR_TICKERS_URL, EDGAR_USER_AGENT

HEADERS = {"User-Agent": EDGAR_USER_AGENT, "Accept-Encoding": "gzip"}
_MIN_INTERVAL = 0.15  # stay well under SEC's 10 req/s guidance


def _get(url: str) -> requests.Response:
    last = getattr(_get, "_last", 0.0)
    wait = _MIN_INTERVAL - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    r = requests.get(url, headers=HEADERS, timeout=60)
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
    """Pull shares-outstanding series from both dei and us-gaap namespaces."""
    rows = []
    sources = [
        ("dei", "EntityCommonStockSharesOutstanding", "edgar:dei"),
        ("us-gaap", "CommonStockSharesOutstanding", "edgar:us-gaap"),
    ]
    for ns, tag, label in sources:
        node = facts.get("facts", {}).get(ns, {}).get(tag, {})
        for unit_rows in node.get("units", {}).values():
            for it in unit_rows:
                if it.get("val") is None:
                    continue
                rows.append({
                    "ticker": ticker,
                    "as_of": it.get("end"),
                    "shares": float(it["val"]),
                    "source": label,
                    "filed_date": it.get("filed"),
                })
    return rows
