# Changelog

Versioning convention: `vMAJOR.MINOR.PATCH`. Minor versions add capability per the
scoping document; v1.0.0 is the first production (daily-updating, full-universe) release.

## Roadmap

- **v0.1.0** — Repo scaffold, schema, 10-ticker pilot pipeline (Alpha Vantage +
  SEC EDGAR), Alpha Vantage rate-limit measurement, QA report validated against Yahoo
  Finance reference values for CSCO.
- **v0.2.0** (current) — Universe builder (S&P 500 + Nasdaq-100 + CIK map), broadened
  EDGAR shares-outstanding extraction (fixes META/XOM gap), filed-date enrichment,
  chunked + resumable full-universe backfill engine, API-based uploader (`tools/`).
- **v0.3.0** — Tag applied when the full ~520-ticker backfill completes and passes QA
  (coverage census, source cross-checks).
- **v0.4.0** — Daily GitHub Actions automation (post-close weekdays), quarterly
  valuation-ratio snapshots backfilled, daily ratios computed going forward;
  Google Drive backup task.
- **v1.0.0** — Stable production database; documented query patterns.
- **v1.1.0** — Netlify screener dashboard (DuckDB-WASM over the Parquet files).
- **v2.0.0** — Point-in-time index membership incl. removed/delisted companies
  (removes survivorship bias).

## v0.2.0 — 2026-08-13

- `etl/universe.py`: scrapes S&P 500 + Nasdaq-100 constituents (Wikipedia), normalizes
  tickers (dots -> dashes), joins SEC CIKs, writes dated `index_membership` snapshot.
- `etl/edgar_client.py`: shares-outstanding extraction broadened to 5 tag variants
  (dei + us-gaap point-in-time, issued, weighted-average basic/diluted); filed-date
  index from us-gaap Assets; filtered raw saves (full companyfacts no longer stored).
- `etl/full_backfill.py`: chunked (40/chunk), resumable (per-ticker done markers),
  time-budgeted full-universe backfill; per-chunk Parquet parts under
  `data/parquet/<table>/part_*.parquet` (v0.1 single files removed); per-chunk commits
  in CI; QA report + per-ticker coverage census.
- `etl/pilot_backfill.py` is now a shim delegating to `full_backfill.py` (keeps the
  Bootstrap workflow entrypoint stable).
- `tools/gh_push.py`: stdlib-only GitHub Data-API uploader (push/dispatch/runs/watch) —
  used to ship code from the maintainer's machine without git.
- `.github/workflows/backfill.yml`: dispatchable full backfill (350-min timeout,
  budget + max_tickers inputs).

## v0.1.0 — 2026-08-13

Initial scaffold and pilot pipeline. Pilot PASSED: 10/10 tickers, 43,363 fundamental
rows, 60,533 price rows (back to 1999), 1,298 share-count points; CSCO validation
5/5 items within 0.12% of Yahoo reference; rate limit measured >=150/min.
