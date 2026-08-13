"""Pilot configuration — v0.1."""

# 10 pilot tickers: mix of sectors, fiscal calendars (CSCO = July FYE), and both indices.
# CSCO is the validation ticker (reference values from Yahoo Finance, 2026-08-13).
PILOT_TICKERS = ["CSCO", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "JPM", "XOM"]

AV_BASE = "https://www.alphavantage.co/query"
EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# SEC requires a descriptive User-Agent with contact info.
EDGAR_USER_AGENT = "market-fundamentals-db pilot (ptayebati@gmail.com)"

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

# How many rapid GLOBAL_QUOTE calls to attempt when measuring the key's rate limit.
RATE_TEST_MAX_CALLS = 80
RATE_TEST_WINDOW_SECONDS = 65
