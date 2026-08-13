# Changelog

Versioning convention: `vMAJOR.MINOR.PATCH`. Minor versions add capability per the
scoping document; v1.0.0 is the first production (daily-updating, full-universe) release.

## Roadmap

- **v0.1.0** (current) — Repo scaffold, schema, 10-ticker pilot pipeline (Alpha Vantage +
  SEC EDGAR), Alpha Vantage rate-limit measurement, QA report validated against Yahoo
  Finance reference values for CSCO.
- **v0.2.0** — EDGAR backfill engine: XBRL tag normalization, Q4 derivation (FY − Q1−Q2−Q3)
  for flow statements, fiscal-calendar handling.
- **v0.3.0** — Full ~520-ticker backfill + data-quality report (source cross-checks, gap census).
- **v0.4.0** — Daily GitHub Actions automation (post-close weekdays), quarterly valuation-ratio
  snapshots backfilled, daily ratios computed going forward; Google Drive backup task.
- **v1.0.0** — Stable production database; documented query patterns.
- **v1.1.0** — Netlify screener dashboard (DuckDB-WASM over the Parquet files).
- **v2.0.0** — Point-in-time index membership incl. removed/delisted companies
  (removes survivorship bias).

## v0.1.0 — 2026-08-13

Initial scaffold and pilot pipeline.
