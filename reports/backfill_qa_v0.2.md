# Full backfill QA report (v0.2) — 2026-08-13 18:30 UTC

- Universe size: **518**
- Completed tickers: **518**
- Failed tickers: **0**
- Run incomplete (budget hit): **False**

## EDGAR shares coverage

- Tickers with 0 EDGAR share points: 1 ['STZ']
- META: **124** share points (v0.1 was META=0, XOM=7)
- XOM: **15** share points (v0.1 was META=0, XOM=7)

Full per-ticker census: `reports/coverage_census_v0.2.csv`

## Aggregate coverage

- Median AV quarters: 81
- Tickers with >=40 quarters (10y): 488/518
- Median price days: 6735
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