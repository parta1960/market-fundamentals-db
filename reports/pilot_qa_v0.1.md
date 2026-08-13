# Pilot backfill QA report — 2026-08-13 16:21 UTC

## Alpha Vantage rate-limit measurement

- Successful calls in 34.3s: **80**
- Inferred tier: **>=150/min premium (or higher)**

## Coverage depth per ticker

| ticker | AV quarters | AV oldest | price days | price oldest | EDGAR share pts | EDGAR oldest |
|---|---|---|---|---|---|---|
| CSCO | 81 | 2006-07-31 | 6735 | 1999-11-01 | 203 | 2009-07-25 |
| AAPL | 81 | 2006-06-30 | 6735 | 1999-11-01 | 214 | 2008-09-27 |
| MSFT | 81 | 2006-06-30 | 6735 | 1999-11-01 | 250 | 2007-06-30 |
| NVDA | 81 | 2006-04-30 | 6735 | 1999-11-01 | 102 | 2009-01-25 |
| GOOGL | 81 | 2006-06-30 | 5530 | 2004-08-19 | 88 | 2014-12-31 |
| AMZN | 81 | 2006-06-30 | 6735 | 1999-11-01 | 207 | 2008-12-31 |
| META | 66 | 2010-03-31 | 3578 | 2012-05-18 | 0 | None |
| AVGO | 78 | 2007-01-31 | 4280 | 2009-08-06 | 103 | 2016-01-31 |
| JPM | 81 | 2006-06-30 | 6735 | 1999-11-01 | 124 | 2008-12-31 |
| XOM | 81 | 2006-06-30 | 6735 | 1999-11-01 | 7 | 2024-12-31 |

## CSCO validation vs Yahoo Finance reference (quarter ending 2026-04-30)

| item | expected | got | diff | pass |
|---|---|---|---|---|
| totalRevenue | 1.584e+10 | 1.584e+10 | 0.01% | PASS |
| grossProfit | 1.008e+10 | 1.008e+10 | 0.00% | PASS |
| operatingIncome | 3.96e+09 | 3.96e+09 | 0.00% | PASS |
| netIncome | 3.37e+09 | 3.373e+09 | 0.09% | PASS |
| ebitda | 5.05e+09 | 5.044e+09 | 0.12% | PASS |

## Output sizes

- `data/raw/edgar/AAPL_companyfacts.json.gz`: 0.27 MB
- `data/raw/edgar/AMZN_companyfacts.json.gz`: 0.30 MB
- `data/raw/edgar/AVGO_companyfacts.json.gz`: 0.14 MB
- `data/raw/edgar/CSCO_companyfacts.json.gz`: 0.39 MB
- `data/raw/edgar/GOOGL_companyfacts.json.gz`: 0.19 MB
- `data/raw/edgar/JPM_companyfacts.json.gz`: 0.52 MB
- `data/raw/edgar/META_companyfacts.json.gz`: 0.18 MB
- `data/raw/edgar/MSFT_companyfacts.json.gz`: 0.33 MB
- `data/raw/edgar/NVDA_companyfacts.json.gz`: 0.28 MB
- `data/raw/edgar/XOM_companyfacts.json.gz`: 0.01 MB
- `data/raw/av/AAPL_balance.json.gz`: 0.01 MB
- `data/raw/av/AAPL_cashflow.json.gz`: 0.01 MB
- `data/raw/av/AAPL_income.json.gz`: 0.01 MB
- `data/raw/av/AAPL_overview.json.gz`: 0.00 MB
- `data/raw/av/AAPL_prices.json.gz`: 0.22 MB
- `data/raw/av/AMZN_balance.json.gz`: 0.01 MB
- `data/raw/av/AMZN_cashflow.json.gz`: 0.01 MB
- `data/raw/av/AMZN_income.json.gz`: 0.01 MB
- `data/raw/av/AMZN_overview.json.gz`: 0.00 MB
- `data/raw/av/AMZN_prices.json.gz`: 0.18 MB
- `data/raw/av/AVGO_balance.json.gz`: 0.01 MB
- `data/raw/av/AVGO_cashflow.json.gz`: 0.00 MB
- `data/raw/av/AVGO_income.json.gz`: 0.01 MB
- `data/raw/av/AVGO_overview.json.gz`: 0.00 MB
- `data/raw/av/AVGO_prices.json.gz`: 0.14 MB
- `data/raw/av/CSCO_balance.json.gz`: 0.01 MB
- `data/raw/av/CSCO_cashflow.json.gz`: 0.01 MB
- `data/raw/av/CSCO_income.json.gz`: 0.01 MB
- `data/raw/av/CSCO_overview.json.gz`: 0.00 MB
- `data/raw/av/CSCO_prices.json.gz`: 0.20 MB
- `data/raw/av/GOOGL_balance.json.gz`: 0.01 MB
- `data/raw/av/GOOGL_cashflow.json.gz`: 0.01 MB
- `data/raw/av/GOOGL_income.json.gz`: 0.01 MB
- `data/raw/av/GOOGL_overview.json.gz`: 0.00 MB
- `data/raw/av/GOOGL_prices.json.gz`: 0.19 MB
- `data/raw/av/JPM_balance.json.gz`: 0.02 MB
- `data/raw/av/JPM_cashflow.json.gz`: 0.01 MB
- `data/raw/av/JPM_income.json.gz`: 0.01 MB
- `data/raw/av/JPM_overview.json.gz`: 0.00 MB
- `data/raw/av/JPM_prices.json.gz`: 0.21 MB
- `data/raw/av/META_balance.json.gz`: 0.01 MB
- `data/raw/av/META_cashflow.json.gz`: 0.00 MB
- `data/raw/av/META_income.json.gz`: 0.01 MB
- `data/raw/av/META_overview.json.gz`: 0.00 MB
- `data/raw/av/META_prices.json.gz`: 0.12 MB
- `data/raw/av/MSFT_balance.json.gz`: 0.01 MB
- `data/raw/av/MSFT_cashflow.json.gz`: 0.01 MB
- `data/raw/av/MSFT_income.json.gz`: 0.01 MB
- `data/raw/av/MSFT_overview.json.gz`: 0.00 MB
- `data/raw/av/MSFT_prices.json.gz`: 0.21 MB
- `data/raw/av/NVDA_balance.json.gz`: 0.01 MB
- `data/raw/av/NVDA_cashflow.json.gz`: 0.01 MB
- `data/raw/av/NVDA_income.json.gz`: 0.01 MB
- `data/raw/av/NVDA_overview.json.gz`: 0.00 MB
- `data/raw/av/NVDA_prices.json.gz`: 0.21 MB
- `data/raw/av/XOM_balance.json.gz`: 0.01 MB
- `data/raw/av/XOM_cashflow.json.gz`: 0.01 MB
- `data/raw/av/XOM_income.json.gz`: 0.01 MB
- `data/raw/av/XOM_overview.json.gz`: 0.00 MB
- `data/raw/av/XOM_prices.json.gz`: 0.20 MB
- `data/parquet/companies.parquet`: 0.01 MB
- `data/parquet/fundamentals.parquet`: 0.23 MB
- `data/parquet/prices_daily.parquet`: 1.85 MB
- `data/parquet/shares_outstanding.parquet`: 0.02 MB

Row counts: fundamentals=43,363, prices=60,533, shares=1,298

**Validation failures: 0**