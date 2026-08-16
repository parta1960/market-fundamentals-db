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

## v1.3.0 — 2026-08-16

- `docs/chat.js` (new): built-in AI analyst. Provider menu (Claude / Gemini /
  DeepSeek / Kimi), bring-your-own-key stored ONLY in the browser's localStorage
  (never in the repo — the site is public), editable model names. The model
  receives the metric catalog + the currently charted data (main + compare
  tickers, visible range) and can DRIVE the app via a fenced `app` JSON command
  (ticker / metrics / range / compare). Graceful errors with hints (CORS-blocked
  providers, rejected keys).
- `docs/charts.html`: `window.__app` bridge for the assistant; compare mode now
  aligns companies by NEAREST quarter (±45 days) — fixes missing lines when
  fiscal calendars are offset (e.g. NVDA vs AMD).
- Ops: auto-push watcher installed on the maintainer PC (Task Scheduler, 5-min
  poll of `.mfdb\outbox` + `DEPLOY.json` flag) — staged releases deploy without
  manual commands; the GitHub token never leaves the PC.

## v1.2.1 — 2026-08-16

- `docs/charts.html`: Yahoo-style adaptive time axis — round-year labels on long
  ranges (every 1/2/5/10 years as needed), `Mon 'YY` on short ranges; gridlines
  drawn only at labeled ticks. Fixes colliding, unreadable quarter labels.
- `docs/charts.html`: metric checkboxes no longer dead-end at the 6-chart limit —
  selecting a 7th metric now replaces the oldest selection instead of silently
  rejecting the click.

## v1.2.0 — 2026-08-15

History charts: any stored metric, any ticker, any period, on the Pages site.

- `etl/history_export.py` (new): exports per-ticker quarterly history JSON to
  `docs/data/history/` (30 metrics: income/cash-flow/balance-sheet lines incl. cash &
  total debt, margins, growth, per-share, and price-anchored valuation history —
  quarter-end market cap, P/E, P/S, P/FCF, P/B). Write-if-changed keeps daily git churn
  near zero. Runs at the end of every daily update.
- **Share-count basis fix** (correctness): stored share counts mixed two conventions —
  Alpha Vantage counts are retroactively split-adjusted, EDGAR counts are as-reported.
  Pairing raw closes with mixed-basis counts inflated early market caps (AAPL 2006 ~28x).
  The exporter now normalizes every observation to a single basis using the split events
  in `prices_daily`, spike-guards corrupt points (~1000x units bugs in some EDGAR
  weighted-average entries), and recomputes all per-share/valuation series on the
  as-reported basis of each quarter. Validated: AAPL 2006 mktcap $75B / 2016 P/E 13.5 /
  2026 $4.3T; NVDA 2009 544M shares; MSFT 2016 P/E 25.5. NOTE: `per_quarter.parquet`'s
  own eps/ps columns still carry the mixed basis — migrating this fix into `derived.py`
  is a v0.6 item.
- `docs/charts.html` (new): per-ticker chart page — metric picker (up to 6, small
  multiples, one axis each), ticker-compare mode (one metric, up to 4 tickers),
  5/10/15/20y/Max ranges, log scale, data-table view, URL-addressable state
  (`charts.html?t=AAPL&m=pe_ttm&c=MSFT&p=40`). Chart.js vendored (`docs/vendor/`), no
  external CDN. Series palette CVD-validated for the dark surface.
- `docs/index.html`: tickers in the screener table now link to their history page.

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
