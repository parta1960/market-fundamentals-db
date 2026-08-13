"""Alpha Vantage client with throttling, retry, and an empirical rate-limit test."""

import gzip
import json
import os
import time

import requests

from config import AV_BASE, RATE_TEST_MAX_CALLS, RATE_TEST_WINDOW_SECONDS

API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "")  # required at call time, not import time

# Strings AV embeds in 200-OK bodies to signal throttling / entitlement problems.
LIMIT_MARKERS = ("Note", "Information", "Error Message")


class AVError(Exception):
    pass


def _is_limited(payload: dict) -> str | None:
    for k in LIMIT_MARKERS:
        if k in payload and len(payload) == 1:
            return str(payload[k])
    return None


def fetch(function: str, symbol: str, min_interval: float, extra: dict | None = None,
          max_retries: int = 4) -> dict:
    """One throttled call. min_interval seconds are enforced between calls globally."""
    params = {"function": function, "symbol": symbol, "apikey": API_KEY}
    params.update(extra or {})
    last = getattr(fetch, "_last_call", 0.0)
    wait = min_interval - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    for attempt in range(max_retries):
        r = requests.get(AV_BASE, params=params, timeout=60)
        fetch._last_call = time.time()
        r.raise_for_status()
        payload = r.json()
        msg = _is_limited(payload)
        if msg is None:
            return payload
        if "per minute" in msg or "call frequency" in msg or "higher API call volume" in msg:
            time.sleep(20 * (attempt + 1))  # throttled: back off and retry
            continue
        raise AVError(f"{function}/{symbol}: {msg}")
    raise AVError(f"{function}/{symbol}: still throttled after {max_retries} retries")


def save_raw(payload: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt") as f:
        json.dump(payload, f)


def measure_rate_limit() -> dict:
    """Fire rapid GLOBAL_QUOTE calls and count successes in the window.

    Returns dict with calls_ok, first_limit_message, inferred_tier.
    Free tier (25/day) will hit its daily cap almost immediately; premium tiers
    will sustain roughly their per-minute quota.
    """
    ok, first_msg = 0, None
    start = time.time()
    for i in range(RATE_TEST_MAX_CALLS):
        if time.time() - start > RATE_TEST_WINDOW_SECONDS:
            break
        r = requests.get(AV_BASE, params={"function": "GLOBAL_QUOTE",
                                          "symbol": "IBM", "apikey": API_KEY}, timeout=30)
        try:
            payload = r.json()
        except Exception:
            continue
        msg = _is_limited(payload)
        if msg is None and "Global Quote" in payload:
            ok += 1
        else:
            first_msg = first_msg or msg
            break
        time.sleep(0.3)
    elapsed = time.time() - start
    if first_msg and ("per day" in first_msg or "daily" in first_msg):
        tier = "FREE (25/day) — fundamentals via EDGAR, prices need alternative source"
    elif ok >= 70:
        tier = ">=150/min premium (or higher)"
    elif ok >= 40:
        tier = "~75/min premium"
    elif first_msg:
        tier = f"limited after {ok} calls — see message"
    else:
        tier = f"inconclusive ({ok} calls in {elapsed:.0f}s without hitting a limit)"
    return {"calls_ok": ok, "elapsed_seconds": round(elapsed, 1),
            "first_limit_message": first_msg, "inferred_tier": tier}
