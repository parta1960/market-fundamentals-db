# Schema (v0.1)

All tables are Parquet files under `data/parquet/`, queryable with DuckDB/pandas.
String dates are ISO `YYYY-MM-DD`.

## companies.parquet

| column | type | notes |
|---|---|---|
| ticker | string | primary key |
| cik | string | 10-digit zero-padded SEC CIK |
| name | string | |
| exchange | string | |
| sector | string | from Alpha Vantage OVERVIEW |
| industry | string | |
| fiscal_year_end | string | month name, e.g. "July" (Cisco) |

## index_membership.parquet

Dated from day one so point-in-time membership (v2.0) is a data addition, not a redesign.

| column | type | notes |
|---|---|---|
| ticker | string | |
| index_name | string | `SP500` or `NDX100` |
| as_of | date | snapshot date this membership was observed |

## fundamentals.parquet (long format — one row per line item)

| column | type | notes |
|---|---|---|
| ticker | string | |
| fiscal_date_ending | date | company fiscal quarter end (NOT calendar quarter) |
| statement | string | `income` / `balance` / `cashflow` |
| item | string | line-item name (Alpha Vantage naming, e.g. `totalRevenue`) |
| value | double | USD unless `currency` says otherwise |
| currency | string | |
| source | string | `alphavantage` / `edgar` |
| filed_date | date | when the number became public (prevents look-ahead bias); null until v0.2 for AV rows |

Long format is deliberate: ~100 items × sources merge cleanly, and screens pivot only
the items they need.

## shares_outstanding.parquet

| column | type | notes |
|---|---|---|
| ticker | string | |
| as_of | date | XBRL `end` date (EDGAR) or fiscal quarter end (AV) |
| shares | double | |
| source | string | `edgar:dei` (cover-page count) / `edgar:us-gaap` / `alphavantage` |
| filed_date | date | |

## prices_daily.parquet

| column | type |
|---|---|
| ticker | string |
| date | date |
| open / high / low / close | double |
| adjusted_close | double |
| volume | int64 |
| dividend_amount | double |
| split_coefficient | double |

## Derived (arrives v0.4)

`derived_metrics.parquet` — per-share values (EPS, revenue/share, FCF/share, book/share),
TTM aggregates, margins, growth rates, and quarterly valuation-ratio snapshots
(P/E, P/S, EV/EBITDA); computed daily going forward from v0.4.
