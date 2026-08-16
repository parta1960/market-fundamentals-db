# Full backfill QA report (v0.2) — 2026-08-16 12:48 UTC

- Universe size: **518**
- Completed tickers: **514**
- Failed tickers: **4**
- Run incomplete (budget hit): **False**

## EDGAR shares coverage

- Tickers with 0 EDGAR share points: 1 ['STZ']
- META: **124** share points (v0.1 was META=0, XOM=7)
- XOM: **15** share points (v0.1 was META=0, XOM=7)

## Failures

- LMT: `AVError: INCOME_STATEMENT/LMT: Burst pattern detected. Please consider spreading out your API requests more evenly across a 1-minute window and query no more than 10 requests per second. Please contac`
- LYV: `AVError: BALANCE_SHEET/LYV: Burst pattern detected. Please consider spreading out your API requests more evenly across a 1-minute window and query no more than 10 requests per second. Please contact s`
- VLTO: `AVError: INCOME_STATEMENT/VLTO: Burst pattern detected. Please consider spreading out your API requests more evenly across a 1-minute window and query no more than 10 requests per second. Please conta`
- VRSN: `AVError: INCOME_STATEMENT/VRSN: Burst pattern detected. Please consider spreading out your API requests more evenly across a 1-minute window and query no more than 10 requests per second. Please conta`

Full per-ticker census: `reports/coverage_census_v0.2.csv`

## Aggregate coverage

- Median AV quarters: 81
- Tickers with >=40 quarters (10y): 484/514
- Median price days: 6737
- Median EDGAR share points: 282

## CSCO validation vs Yahoo reference

| item | expected | got | diff | pass |
|---|---|---|---|---|
| totalRevenue | 1.584e+10 | 1.584e+10 | 0.01% | PASS |
| grossProfit | 1.008e+10 | 1.008e+10 | 0.00% | PASS |
| operatingIncome | 3.96e+09 | 3.96e+09 | 0.00% | PASS |
| netIncome | 3.37e+09 | 3.373e+09 | 0.09% | PASS |
| ebitda | 5.05e+09 | 5.044e+09 | 0.12% | PASS |

**Validation failures: 0**