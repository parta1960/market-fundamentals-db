# Full backfill QA report (v0.2) — 2026-08-21 15:17 UTC

- Universe size: **2992**
- Completed tickers: **2975**
- Failed tickers: **19**
- Run incomplete (budget hit): **False**

## EDGAR shares coverage

- Tickers with 0 EDGAR share points: 30 ['DGICA', 'ELE', 'FRBA', 'GEF', 'GEF-B', 'GFL', 'GRDN', 'GTXI', 'HIFS', 'HOLX', 'IA', 'IMKTA', 'JBS', 'MC', 'NBN', 'NU', 'ODD', 'OZK', 'PAX', 'PDLI']
- META: **124** share points (v0.1 was META=0, XOM=7)
- XOM: **15** share points (v0.1 was META=0, XOM=7)

## Failures

- ADRO: `AVError: TIME_SERIES_DAILY_ADJUSTED/ADRO: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED.`
- AKE: `AVError: TIME_SERIES_DAILY_ADJUSTED/AKE: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED.`
- BNL: `AVError: INCOME_STATEMENT/BNL: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for INCOME_STATEMENT.`
- CACC: `AVError: BALANCE_SHEET/CACC: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`
- CAR: `AVError: BALANCE_SHEET/CAR: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`
- ECVT: `AVError: BALANCE_SHEET/ECVT: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`
- FWONA: `AVError: INCOME_STATEMENT/FWONA: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for INCOME_STATEMENT.`
- INH: `AVError: TIME_SERIES_DAILY_ADJUSTED/INH: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED.`
- MGRC: `AVError: BALANCE_SHEET/MGRC: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`
- OPFI: `AVError: BALANCE_SHEET/OPFI: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`
- P5N994: `AVError: TIME_SERIES_DAILY_ADJUSTED/P5N994: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED.`
- PPLI: `AVError: INCOME_STATEMENT/PPLI: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for INCOME_STATEMENT.`
- PSFE: `AVError: BALANCE_SHEET/PSFE: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`
- PUMP: `AVError: INCOME_STATEMENT/PUMP: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for INCOME_STATEMENT.`
- RRBI: `AVError: INCOME_STATEMENT/RRBI: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for INCOME_STATEMENT.`
- RYZ: `AVError: INCOME_STATEMENT/RYZ: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for INCOME_STATEMENT.`
- STLN: `AVError: BALANCE_SHEET/STLN: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`
- UFCS: `AVError: BALANCE_SHEET/UFCS: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`
- UVSP: `AVError: BALANCE_SHEET/UVSP: Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for BALANCE_SHEET.`

Full per-ticker census: `reports/coverage_census_v0.2.csv`

## Aggregate coverage

- Median AV quarters: 81
- Tickers with >=40 quarters (10y): 2219/2975
- Median price days: 4685
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