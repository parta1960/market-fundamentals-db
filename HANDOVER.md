# StockLab — Handover

**What it is:** a fundamentals + valuation database and screener for the
S&P 500 + Nasdaq-100 (~518 tickers), updated automatically every weekday after
the US close, with a static web front-end on GitHub Pages. Current version is
in `docs/version.js` (`STOCKLAB_VERSION`); see `CHANGELOG.md` for the full
per-release history. This file is the reproduce-and-continue guide.

## Goals
- Clean, split-adjusted quarterly fundamentals + daily prices for the index,
  with derived per-share series, margins, growth rates, valuation ratios, and
  least-squares trend fits — all screenable and chartable.
- Zero-touch daily refresh; everything static and same-origin (no CORS).
- An in-app multi-model AI assistant on every page.

## Architecture
- **Data source:** Alpha Vantage (prices + fundamentals; premium key) and SEC
  EDGAR (shares outstanding, filed dates). Macro data from FRED.
- **ETL (`etl/`, Python):** `daily_update.py` orchestrates: refresh prices for
  all tickers → (Mondays) rebuild universe → `derived.build()` (per-quarter
  metrics + `latest_ratios`) → `history_export.build()` (per-ticker history +
  trend fits) → `peg.build()` (PEG variants). `av_client.py` throttles/guards
  AV calls; `full_backfill.py` is the one-time/weekly deep sweep.
- **Trend fits:** `trends_<w>.json` per ticker per metric = `[lg, lr, lm, pg, n]`
  (growth-vs-mean, R², slope/yr, %metric = slope÷latest, quarters).
- **Front-end (`docs/`, static):** `index.html` = Rankings screener (landing);
  `screener.html` = full Stock List (free-text criteria); `charts.html` =
  per-stock history + AI analyst report; `macro.html` = macro/market
  correlations; `rankings.html` = redirect stub. Shared: `version.js`,
  `menu.js` (☰ menu), `stocklab.js` (favorites/portfolios/screens/sync),
  `chat.js` (AI assistant), `vendor/chart.umd.min.js`.
- **AI proxy (Netlify, `proxy/`):** `stocklab-ai-proxy.netlify.app` holds the
  provider keys server-side (env vars) and gates on the StockLab password; ops
  `models`/`chat`/`sync_get`/`sync_put`. Cross-device state in Netlify Blobs.

## Data files (docs/data/)
- `latest_ratios.json` — one row/ticker: close, P/E, P/S, P/FCF, P/B, margins,
  y/y growth, %metric columns, and (v1.20.0) `peg_cagr3/cagr5/lin/yoy`,
  `peg_fwd`, `fwd_pe`.
- `history/<T>.json` — quarterly series + splits + structural breaks.
- `trends_{20,40,0}.json` — trend fits per window (5y/10y/all).
- `macro/{meta,series,corr}.json` — (v1.21.0) FRED macro series + correlation
  study vs the market.

## Deployment
- **Hosting:** GitHub Pages from `docs/` on `main` (repo
  `parta1960/market-fundamentals-db`). Netlify only for the AI proxy.
- **Daily job:** `.github/workflows/daily-update.yml` (cron weekdays post-close;
  `ALPHAVANTAGE_API_KEY` from Actions secret). Dispatchable on demand.
- **Code releases** are pushed PC-side (the sandbox cannot push): a patch is
  built in the working tree, transferred to `~/.mfdb`, an `apply_<ver>.py`
  rebuilds each file from `raw.githubusercontent` at the deployed SHA + the
  patch, sha256-gates every file, writes `outbox/DEPLOY.json`
  (optionally `"dispatch":"daily-update.yml"`), then `auto_push.py` uploads.
- **Secrets:** never in the repo or client code. AV/GitHub/Netlify/FRED keys
  live only in `~/.mfdb/*` on the PC and in Actions/Netlify env vars. AI
  provider keys live only in Netlify env. The browser never holds a key —
  AI calls go through the proxy; macro data is pre-fetched server-side and
  served as static JSON.

## Env-var / key names (values are NOT stored here)
`ALPHAVANTAGE_API_KEY`, `FRED_API_KEY`, `STOCKLAB_PASS`, `NETLIFY_TOKEN`,
`SL_SITE_ID`, and per-provider AI keys (`CLAUDE_KEY`, `GEMINI_KEY`,
`DEEPSEEK_KEY`, `KIMI_KEY`).

## UI conventions
- Version string shown on every page (`.sl-ver`). Tables freeze the first row
  and first column (`position: sticky`). Every page carries the bottom AI
  chat box (`chat.js`). Menu order: Rankings (home) · Stock List · History
  Charts · Macro; plus Favorites / Portfolios / saved screens.

## Known gaps / next steps
- **No off-site backup** of the repo/data yet (top infra risk) — planned
  Actions→Drive export.
- **Site password gate:** the Pages site is not yet client-side gated; the AI
  features are password-gated at the proxy, but the pages themselves are
  public. Add a StatiCrypt-style gate if the data must be private.
- Macro refresh is currently generated on demand (FRED key is PC-side, not in
  Actions); wire `FRED_API_KEY` into the workflow to automate monthly.
- Roadmap: Russell 1000/2000 expansion; PEG/forward columns + rankings;
  diluted EPS; EV multiples; point-in-time index membership (removes
  survivorship bias).

## Changelog
See `CHANGELOG.md` (top = newest).
