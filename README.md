# market-fundamentals-db

Quarterly financial statements (income statement, balance sheet, cash flow), shares
outstanding, and daily adjusted prices for S&P 500 + Nasdaq-100 companies (~520 unique
tickers), covering 10 years, updated daily after US market close.

**Current version: v0.1.0** — pilot: 10 tickers, end-to-end pipeline validation.
See `CHANGELOG.md` for the version roadmap and `schema.md` for table definitions.

## Data sources

| Data | Source |
|---|---|
| Quarterly fundamentals (recent + ongoing) | Alpha Vantage `INCOME_STATEMENT` / `BALANCE_SHEET` / `CASH_FLOW` |
| Quarterly fundamentals backfill (full 10y) + shares outstanding ground truth | SEC EDGAR XBRL company facts |
| Daily adjusted prices (OHLCV, dividends, splits) | Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED` |

## Layout

```
etl/                  Python pipeline
data/raw/             Raw API responses (gzipped JSON, for audit/reprocessing)
data/parquet/         Normalized tables (the queryable database)
reports/              QA / data-quality reports from each run
.github/workflows/    pilot-backfill.yml (v0.1) — daily automation arrives in v0.4
```

## Setup (one-time)

1. Repository secret **`ALPHAVANTAGE_API_KEY`** must be set
   (Settings → Secrets and variables → Actions → New repository secret).
2. Run the pilot: Actions tab → "Pilot backfill (v0.1)" → Run workflow.
   The run measures the Alpha Vantage key's real rate limit, pulls 10 pilot tickers
   from both sources, writes Parquet, and commits a QA report to `reports/`.

## Querying

The Parquet files are directly queryable with DuckDB:

```sql
SELECT ticker, fiscal_date_ending, value
FROM 'data/parquet/fundamentals.parquet'
WHERE item = 'totalRevenue' AND ticker = 'CSCO'
ORDER BY fiscal_date_ending DESC;
```
