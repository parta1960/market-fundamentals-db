"""Configuration — v0.2 (full-universe backfill)."""

# ---------------------------------------------------------------- pilot (v0.1)
# 10 pilot tickers: mix of sectors, fiscal calendars (CSCO = July FYE), both indices.
PILOT_TICKERS = ["CSCO", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "JPM", "XOM"]

AV_BASE = "https://www.alphavantage.co/query"
EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# SEC requires a descriptive User-Agent with contact info.
EDGAR_USER_AGENT = "market-fundamentals-db (ptayebati@gmail.com)"

# Reference values for validation, read off the user's Yahoo Finance CSCO screenshot
# (quarterly income statement, fiscal quarter ending 2026-04-30). Tolerance is loose
# (2%) because Yahoo rounds to 3 significant figures.
CSCO_REFERENCE = {
    "fiscal_date_ending": "2026-04-30",
    "totalRevenue": 15.84e9,
    "grossProfit": 10.08e9,
    "operatingIncome": 3.96e9,
    "netIncome": 3.37e9,
    "ebitda": 5.05e9,
}
CSCO_REFERENCE_TOLERANCE = 0.02

RATE_TEST_MAX_CALLS = 80
RATE_TEST_WINDOW_SECONDS = 65

# ---------------------------------------------------------------- universe (v0.2)
SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NDX_URL = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"
WIKI_USER_AGENT = "market-fundamentals-db universe builder (ptayebati@gmail.com)"

# Sanity bounds — fail loudly if a scrape looks wrong rather than committing garbage.
SP500_EXPECTED_RANGE = (495, 512)
NDX_EXPECTED_RANGE = (95, 112)

# ---------------------------------------------------------------- backfill (v0.2)
# v0.1 measured >=150 calls/min on this key (80 calls in 34s, zero throttling).
# 0.45s spacing ~= 133/min leaves headroom; the client still backs off on any
# throttle message it sees.
AV_MIN_INTERVAL_SECONDS = 0.45

# Tickers per chunk. After each chunk the runner flushes Parquet parts and
# (in CI) commits, so a killed run resumes at the next chunk.
CHUNK_SIZE = 40

# Broadened EDGAR shares-outstanding extraction (v0.1 gap: META=0 pts, XOM=7 pts).
# Order matters: preferred sources first; dedup keeps the first occurrence.
SHARES_TAG_SOURCES = [
    ("dei", "EntityCommonStockSharesOutstanding", "edgar:dei"),
    ("us-gaap", "CommonStockSharesOutstanding", "edgar:us-gaap"),
    ("us-gaap", "CommonStockSharesIssued", "edgar:us-gaap-issued"),
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic", "edgar:wavg-basic"),
    ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding", "edgar:wavg-diluted"),
]

# CIKs missing from SEC's company_tickers.json (verified against EDGAR companyfacts).
CIK_OVERRIDES = {
    "AEP": "0000004904",  # American Electric Power — absent from ticker file 2026-08-13
}
