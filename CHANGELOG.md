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

## v1.9.2 — 2026-08-17

- **The AI conversation is remembered** (`docs/chat.js`): the last 40 turns
  are saved in the browser and restored automatically — across reloads and
  when moving between the screener and the charts page. Restored messages are
  marked with a short note; app-command blocks are stripped when re-displayed.
  The model also receives the restored history, so follow-up questions like
  "and compare that to MSFT" work after a reload. Storage is per device;
  "↺ clear" erases it, as does Menu → Reset AI settings.
- **Closing the assistant is now obvious**: the unlabeled ✕ became a proper
  **"✕ Close"** button (highlighted red on hover), **Esc** closes the panel,
  and the 🤖 bar button is a true toggle that lights up blue while the
  assistant is open. All three paths go through one function, so the button
  state can never disagree with the panel.

## v1.9.1 — 2026-08-17

- **Linear fit added alongside the exponential fit** on every chart: dashed =
  exponential y=a·e^(b·t), dotted = linear y=c+m·t (least squares, all
  non-null points, R² in plain y-space, ≥6 points).
- **Minimalist parameter table drawn inside each chart** (top-left, over a
  clean strip reserved by chart padding so nothing collides): row "exp" with
  a, b, equivalent %/yr and R²; row "lin" with c, m/yr and R². Compare mode
  compacts to one row per ticker (exp %/yr + R², lin slope + R²). The old
  header text line is gone.
- Comparing the two R² values tells you at a glance whether a series is
  compounding (exp wins) or growing by a fixed amount per year (lin wins) —
  e.g. AAPL revenue TTM: exp R²=0.85 vs lin R²=0.98 → the last 20 years are
  closer to linear dollar growth than to constant-% compounding.
- Linear fit verified against an independent numpy fit (AAPL revenue TTM:
  c=$6.4B, m=+$22.8B/yr, R²=0.98 — exact match).

## v1.9.0 — 2026-08-16

- **Exponential fit on every chart** (`docs/charts.html`): each series gets a
  dashed fitted curve y=a·e^(b·t) with its parameters shown in the chart
  header — a (level at series start), b (continuous yearly rate), the
  equivalent compound %/yr, and R² (log-space). Least squares on ln(y) over
  the VISIBLE range, positive values only, ≥6 points required (series
  without enough positive data say "fit n/a"). Works in compare mode too
  (per-company dashed fits + parameter strip). Because fits are computed in
  the browser at draw time from the latest JSON, they update automatically
  every time new quarterly data lands — nothing to maintain.
- Verified against an independent numpy fit of the same data: identical to
  every displayed digit (AAPL revenue TTM: a=$43.1B, b=0.143/yr, +15.4%/yr,
  R²=0.846).

## v1.8.1 — 2026-08-16

- Responsive fixes from a full 4-viewport UX audit (1400/1024/768/390 px):
  - **Top bar no longer overflows on phones** — the send / minimize buttons
    were unreachable at phone widths (they sat at x≈630 on a 390-px screen).
    On narrow screens the provider/model pickers relocate into the AI panel
    header, the Menu button collapses to "☰", and bar spacing tightens.
  - Charts grid no longer forces sideways scrolling on phones
    (`minmax(min(430px,100%),1fr)`).
  - **Tables: first row AND first column now stay fixed while scrolling**
    (screener table + charts data table), per the standing preference —
    scrollable containers with sticky header and sticky ticker/quarter column.
  - 📈 favicon on both pages (was the browser default blank).

## v1.8.0 — 2026-08-16

- **Fixed top bar** on every page (stays put while scrolling): ☰ Menu at the
  TOP LEFT, and the AI consolidated into one strip — 🤖 panel toggle, the
  "Ask StockLab AI" input, provider + model dropdowns (the pickers now live
  on the bar, like a chat app), 🎤 **dictation** (browser speech recognition,
  hidden where unsupported), a blue **↑ send** button, and a **>< minimize**
  button that collapses the chat box to a small pill (state remembered per
  device; click the pill or <> to expand). The old floating AI button and the
  in-page chat box are gone — replaced by the bar. The AI panel now opens
  below the bar.
- Not adopted from the reference screenshot: file attachments ("+") and an
  effort/mode switch ("Auto") — neither maps to anything functional in
  StockLab today (the AI already receives the charted data automatically).

## v1.7.0 — 2026-08-16

- **☰ Menu button** (`docs/menu.js`, next to the AI button on every page):
  AI setup (opens the assistant with the password/key rows ready), Share this
  view (native share on phones, copy-link elsewhere), Screener / History
  Charts navigation, Changelog + methodology links, data-freshness readout,
  and "Reset AI settings on this device" (two-click confirm; clears the saved
  password/keys/model choices).
- **No more manual hard refresh**: every script include is now
  version-stamped (`chat.js?v=v1.7.0` …), so browsers automatically fetch the
  new code when a release lands — stale-cache confusion ("button does
  nothing", "still the old models") ends after this release rolls out.
  RELEASE CHECKLIST: bump the `?v=` stamp in BOTH html files each release.
- Diagnosis note: the reported dead 🤖 AI button reproduced on neither page
  against the deployed code (Playwright: panel opens via button and top bar,
  zero console errors) — consistent with the browser running cached v1.4.x
  files, which this release prevents going forward.

## v1.6.0 — 2026-08-16

- **AI without pasting API keys** (`proxy/`): new password-gated Netlify
  Function (`stocklab-ai-proxy.netlify.app`) holds the 4 provider keys
  server-side in env vars — never in the public repo/site. Enter the ONE
  StockLab password once per device (🔑 in the AI panel) and all providers +
  live top-model lists work, on desktop and phone. Per-provider BYOK keys
  still work as a fallback. Also fixes browser-CORS limits for DeepSeek/Kimi
  (calls now originate server-side).
- Verified end-to-end: wrong password → 401; live model lists for all 4
  providers; chat round-trips for Gemini (gemini-3.1-pro-preview) and
  DeepSeek. NOTE: Claude (no API credit balance) and Kimi (account suspended,
  insufficient balance) need account top-ups on the provider side — the
  plumbing is confirmed working.

## v1.5.0 — 2026-08-16

- **Diluted share counts**: new chartable metric "Shares (wtd-avg diluted)"
  (EDGAR weighted-average diluted, 501/515 tickers, median ~17y depth),
  split-adjusted to today's basis like all displayed share data. Guarded two
  ways: rolling-median spike filter + absolute anchor (diluted must be within
  0.5x–2x of the outstanding count that quarter — catches multi-quarter ~1000x
  units bugs in some filings, e.g. NVDA 2010-13).
- **Split markers on every chart**: the first data point after each stock split
  is drawn as a pink diamond (hover = ratio + date, e.g. "7:1 split on
  2014-06-09") so split handling is verifiable by eye. Works in compare mode
  (each ticker's own splits, labeled). Markers require data on both sides of
  the split; ticker JSONs now carry a `splits` array.
- **AI chat model lists**: built-in fallback lists refreshed to the current
  top models (Claude Fable 5 / Opus 5 / Sonnet 5; Gemini 3.1 Pro / 3.7 Flash;
  DeepSeek V4 Pro/Flash; Kimi K3). The panel now SAYS when it is showing the
  built-in list (no API key saved yet) or when a live refresh fails, instead
  of silently showing a stale list — save a key once (🔑) to get the live,
  auto-updating top-model list.

## v1.4.2 — 2026-08-16

- Hotfix: the Sunday universe refresh returned a company (CME) with a missing
  name; the exporter's fallback leaked Python `NaN` into
  `docs/data/history/manifest.json`, which is invalid JSON and broke the charts
  page ("Failed to load manifest"). Names/sectors are now sanitized to strings,
  and both JSON writers use `allow_nan=False` as a tripwire so invalid JSON can
  never be published silently again.

## v1.4.1 — 2026-08-16

- **Split-adjusted display basis** (`etl/history_export.py`): prices, share
  counts and all per-share series (EPS, revenue/share, FCF/share, book/share)
  are now presented split-adjusted to today's basis — continuous across splits
  and directly comparable to Yahoo Finance / Seeking Alpha. Fixes the apparent
  discontinuities in AAPL EPS at the 2014 7:1 and 2020 4:1 splits. Valuation
  ratios are computed on the internally consistent as-reported pair and are
  unchanged.
- **Top-10 cross-validation** vs stockanalysis.com quarterly statements:
  revenues EXACT to the dollar for AAPL, MSFT, NVDA, GOOGL, TSLA (latest two
  quarters each); AAPL split-adjusted closes match Yahoo at 2006/2012/2020
  checkpoints. Known definitional difference: our EPS = net income ÷ period-end
  share count; Yahoo/SA report weighted-average DILUTED EPS (typically 0–1%
  apart; up to ~9% for heavy issuers like TSLA). Diluted EPS = backlog item.

## v1.4.0 — 2026-08-16

- **Rebrand:** "Market Fundamentals Screener" → **StockLab** (titles + headers on
  both pages).
- **Version badge on every page** (`docs/version.js`, single source of truth,
  shown in each header and in the AI panel; bumped each release).
- **AI on every page:** chat box at the top of the landing page and charts page
  ("Ask StockLab AI…") — Enter opens the assistant and sends. On the screener
  page the assistant receives the full latest-ratios table as context; app
  commands there navigate to the History Charts page with the requested view.

## v1.3.1 — 2026-08-16

- `docs/chat.js`: model picker is now a dropdown fed LIVE from each provider's
  own `/models` API (Anthropic, Gemini, DeepSeek, Moonshot) using the user's
  key — new top models appear automatically, no site update needed. Ranked
  best-first per provider (Fable/Opus > Sonnet > Haiku; Pro > Flash; Reasoner >
  Chat; K4 > K3 > K2; newest version first), 24h cache, refreshed on panel
  open / provider switch / key save; per-provider choice remembered. Hardcoded
  fallback list only when no key or the fetch fails.

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
