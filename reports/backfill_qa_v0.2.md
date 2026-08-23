# Full backfill QA report (v0.2) — 2026-08-23 15:14 UTC

- Universe size: **2992**
- Completed tickers: **2988**
- Failed tickers: **4**
- Run incomplete (budget hit): **False**

## EDGAR shares coverage

- Tickers with 0 EDGAR share points: 29 ['DGICA', 'ELE', 'FRBA', 'GEF', 'GEF-B', 'GFL', 'GRDN', 'GTXI', 'HIFS', 'HOLX', 'IMKTA', 'JBS', 'MC', 'NBN', 'NU', 'ODD', 'OZK', 'PAX', 'PDLI', 'PFBC']
- META: **124** share points (v0.1 was META=0, XOM=7)
- XOM: **15** share points (v0.1 was META=0, XOM=7)

## Failures

- ADRO: `AVError: TIME_SERIES_DAILY_ADJUSTED/ADRO: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED.`
- AKE: `AVError: TIME_SERIES_DAILY_ADJUSTED/AKE: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED.`
- INH: `AVError: TIME_SERIES_DAILY_ADJUSTED/INH: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED.`
- P5N994: `AVError: TIME_SERIES_DAILY_ADJUSTED/P5N994: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED.`

Full per-ticker census: `reports/coverage_census_v0.2.csv`

## Aggregate coverage

- Median AV quarters: 81
- Tickers with >=40 quarters (10y): 2226/2988
- Median price days: 4637
- Median EDGAR share points: 231

## CSCO validation vs Yahoo reference

| item | expected | got | diff | pass |
|---|---|---|---|---|
| totalRevenue | 1.584e+10 | 1.584e+10 | 0.01% | PASS |
| grossProfit | 1.008e+10 | 1.008e+10 | 0.00% | PASS |
| operatingIncome | 3.96e+09 | 3.96e+09 | 0.00% | PASS |
| netIncome | 3.37e+09 | 3.373e+09 | 0.09% | PASS |
| ebitda | 5.05e+09 | 5.044e+09 | 0.12% | PASS |

**Validation failures: 0**