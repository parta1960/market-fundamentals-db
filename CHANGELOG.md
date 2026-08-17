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

## v1.17.0 — 2026-08-17

- **Rankings: stackable filter levels + explicit ⚡ Rank button** (user
  request). Four "Filter level" rows — each a field / ≥-or-≤ / value triple —
  stack with AND logic on top of the ranking: Fit R², %metric, slope, P/E,
  P/S, P/FCF, P/B, margin levels, y/y growth rates, share-count change, EPS
  and price. Companies missing a filtered value are excluded; the active
  levels are echoed under the button and in the status line.
- **Nothing recomputes until ⚡ Rank is pressed** — you compose the ranking
  and all filter levels first, then execute once. "Clear filters" resets all
  levels.
- **Search box removed from Rankings** (user request). It doubled as a target
  for the stray-text injection ("Hello" was silently filtering the table to
  zero rows); ticker lookup remains available on the screener, and the
  explicit-run model means no keystroke anywhere can change the ranking.
- The old standalone "Min R²" box is folded into filter level 1 (pre-selected
  to Fit R², value blank).

## v1.16.3 — 2026-08-17

- **Rankings: one "Rank by" selector with %metric first** (user feedback:
  "the first filter doesn't allow %EPS"). The metric dropdown and the
  separate "Order by" control are merged into a single list with two groups —
  "%metric — unitless, per year" (%EPS, %Rev/sh, %FCF/sh, %Book/sh, %GM,
  %OM) and "Slope — native units per year" — so %EPS is directly selectable
  and is now the DEFAULT ranking. Option value encodes metric:field
  (e.g. eps:pg); header clicks still re-sort any column.

## v1.16.2 — 2026-08-17

- **%metric made findable** (user feedback: "I don't see %EPS in the
  filtering"). Rankings gained an "Order by" selector — Slope / **%metric
  (unitless)** / Fit R² — so ranking by %EPS no longer requires knowing the
  column header is clickable. The screener's first criteria box placeholder
  now reads "e.g. %EPS > 10 · P/E < 20" and the help line leads with %EPS
  and %Rev/sh examples. Short names (%Rev/sh, %FCF/sh, %Book/sh, %GM, %OM,
  rps, fps, bps) added to the parser's synonyms, and ≥ / ≤ are now accepted
  operators (the help text uses them).

## v1.16.1 — 2026-08-17

- **Consistent, minimalist ☰ menu icons.** The mixed emoji (🤖 🔗 📋 📈 🏆 ★
  ▦ 💾 📜 🧪 🧹), which render differently on every OS and font, are replaced
  with one coherent inline-SVG icon set: stroke-only, single 1.7px weight,
  single 15px size, monochrome grey that brightens on hover (red for the
  destructive reset row). Dynamic rows (Favorites, portfolios, saved screens)
  use the same set — star, grid, bookmark — and their delete ✕ aligns
  right via flex instead of float. Zero external assets; the icons live in
  menu.js as ~20 short path strings.

## v1.16.0 — 2026-08-17

- **%metric — a unitless trend measure for every linear fit** (user request:
  "divide the slope by the TTM value"). For each of the 9 fitted series and
  3 windows, the database now stores `pg` = slope ÷ the series' LATEST value
  (e.g. %EPS = EPS slope $/yr ÷ current TTM EPS), expressed per year. Because
  it is unitless, companies of any size compare directly. Null when the
  latest value is ≤ 0 or < 25% of the series' typical magnitude (a percentage
  of ~nothing is noise). `trends_<w>.json` fields are now
  **[lg, lr, lm, pg, n]**; both UIs read the file's own `fields` list, so old
  and new data files load interchangeably.
- **Naming convention: `%<series>`** — %EPS, %Rev/sh, %FCF/sh, %Book/sh,
  %REV, %NI, %FCF, %GM, %OM. Used as column headers and understood by the
  screener's free-text boxes ("%EPS > 10"); plain "EPS growth > 15%" now also
  resolves to %EPS. The older slope-÷-mean rate stays in the database as
  `lg` ("EPS growth vs mean level") for anyone who wants it.
- **Rankings page** shows %metric in place of the old Growth %/yr column
  (header adapts per metric: "%EPS /yr", "%Rev/sh /yr", …), sortable like
  every other column, with the full fit in the tooltip.
- **Screener** trend columns are now %EPS / %Rev/sh / %FCF/sh; chart fit
  boxes gained a "% +x.x%/yr" cell computed over the visible range.
- **🎤 voice dictation removed entirely** (user request). The mic button and
  all SpeechRecognition code are gone — the site never touches a microphone.

## v1.15.0 — 2026-08-17

- **Page navigation** in the fixed top bar: ◀ back, ▶ forward and "⇥ latest"
  buttons step through the views you've visited this session (screener →
  rankings → a ticker's charts → …) and jump straight back to the newest one.
- **Favorites & portfolios.** Every stock — in the screener, the rankings and
  on its chart page — carries a ☆ star (favorite) and a ▦ button that opens a
  portfolio picker with an on-the-spot "＋ New portfolio…" option. The ☰ Menu
  now lists ★ Favorites and every portfolio (with counts, ✕ to delete);
  choosing one opens the screener filtered to just those stocks.
- **Saved screens.** New 💾 "Save screen" button stores the current free-text
  criteria + trend window under a name; saved screens appear in the ☰ Menu and
  re-apply on click (AI-interpreted criteria re-parse automatically).
- **Cross-device sync.** Favorites, portfolios, saved screens AND the AI
  conversation now sync between phone and desktop through the password-gated
  proxy (new `sync_get`/`sync_put` ops storing one JSON blob in Netlify Blobs
  — provider keys and the blob never touch the public site). Newest timestamp
  wins; everything still works purely locally until the StockLab password is
  entered on a device.
- **HAL-9000 AI button.** The 🤖 icon is now a glowing red eye (pure CSS
  radial gradient) that brightens when the panel is open.
- **Yahoo Finance links.** A small Y! chip next to every stock opens its Yahoo
  quote page in a new tab for side-by-side comparison.
- **Yahoo-style stock sections** on the charts page: a pill bar per ticker
  with Summary (key-numbers strip from OUR database: close, market cap, P/E,
  P/S, P/FCF, P/B, revenue/EPS/FCF TTM, margins, shares, splits, breaks),
  Chart, Statistics, Financials and Historical data (all internal), plus
  News / Profile / Analysis / Options / Holders / Community as deep links
  into the matching Yahoo tab — that content is Yahoo's own licensed data and
  scraping it into StockLab isn't feasible or permitted, so linking is the
  honest version of that feature.
- New shared module `docs/stocklab.js`; ☰ Menu also gained the 🏆 Rankings
  link.

## v1.14.0 — 2026-08-17

- **New Rankings tab** (`docs/rankings.html`, linked 🏆 from the screener and
  charts headers). Ranks every company by the SLOPE of its linear fit with the
  fit's R² alongside, colour-coded by trustworthiness: green ≥ 0.8 (the slope
  is a faithful summary of the series), amber 0.5–0.8 (real trend, real
  wobble), grey < 0.5 (the slope is not a reliable description). Defaults to
  EPS slope, 10-year window, descending; a dropdown re-ranks by Rev/share,
  FCF/share, Book/share or margin slopes, plus window selector (5y/10y/all),
  a Min-R² cutoff box, sector filter and search. Every column header
  re-sorts; tickers link to their history charts; first row and column stay
  frozen while scrolling. Reuses the existing `trends_<w>.json` +
  `latest_ratios.json` — no new data files, so rankings refresh automatically
  with each daily run.

## v1.13.0 — 2026-08-17

- **Exponential fits removed everywhere.** `_exp_trend()` is gone from
  `etl/history_export.py`; `expFit()` and its dashed dataset are gone from
  `docs/charts.html`; the `_eg` / `_er` / `_eb` fields, the three CAGR columns
  and every "exponential"/"CAGR" synonym are gone from `docs/index.html`. Each
  chart now carries one fit — the dotted linear one — and its corner table has
  one row (`c`, `m`/yr, R²) instead of two. Rationale for keeping the linear
  one: on these series it was usually the better-behaved of the two (the log-
  space R² of an exponential fit is not comparable with a plain-space R², and
  the positive-values-only rule silently dropped loss-making quarters).
- **Linear slope and R² are now first-class database fields.** `trends_<w>.json`
  stores four numbers per ticker per metric — `[growth %/yr, R², slope per year,
  n quarters]` — for 9 series (EPS, revenue/share, FCF/share, revenue, net
  income, FCF, gross margin, operating margin, book/share) across 3 windows
  (20q, 40q, all). Six of them are now VISIBLE screener columns (EPS,
  Rev/sh, FCF/sh × slope $/yr and fit R²), sortable, with the full fit in each
  cell's tooltip; all 36 remain screenable by name through the free-text boxes
  ("EPS fit R² ≥ 0.9", "revenue per share slope ≥ 1").
- **FIX — silent loss of a ticker's entire price history (found in AAPL).**
  On the 2026-08-17 run Alpha Vantage answered `200 OK` with an empty body
  `{}` for AAPL. `av_client._is_limited()` only recognises a limit message when
  it is the payload's *sole* key, so an empty body looked like success:
  `flatten_prices()` returned zero rows, AAPL was recorded in `done`, was
  therefore NOT carried forward, and the parts rewrite deleted its 20 years of
  prices. Consequences were silent and wide — no `close` series, no `splits`,
  and because `_factor_after()` then returns 1.0, every per-share series shipped
  on a MIXED basis (AAPL EPS read 13.23 → 3.35 across the 2020 4:1 split) and
  its EPS trend flipped from +13.5%/yr R²=0.93 to −5.7%/yr R²=0.22. Three
  independent guards added: `av_client.fetch(require=...)` rejects a payload
  that lacks the expected data key (retries, then raises); `_pull_prices()`
  treats zero rows as a failure, never a success; and `refresh_prices()` now
  compares each ticker's fresh row count with the previous parts and keeps the
  old history whenever a "refresh" comes back more than 10% shorter. A tripwire
  in `history_export.build()` names any ticker that reaches the exporter with no
  price history, so this class of fault can no longer ship unannounced.

## v1.12.0 — 2026-08-17

- **Structural-break (spin-off) detection.** `etl/history_export.py`
  `detect_breaks()` finds quarters where a company's revenue steps to a
  sustained new level — a spin-off, divestiture, deconsolidation or
  transforming acquisition. Detected FROM THE DATA (no hand-kept event list,
  so it covers every company and stays current): each quarter is compared
  with the same quarter a year earlier (seasonality cancels), the change must
  be step-like (prior year normal — so fast organic compounding is NOT
  flagged; AAPL, MSFT, INTC come back clean) and the new level must hold for
  about a year (filters one-quarter reporting glitches and COVID dips that
  snap back). 204 of 515 companies have at least one; ratios beyond 5x/0.2x
  are tagged "verify". Shipped in each ticker JSON as `breaks`.
- **Charts**: an amber dashed vertical line marks each break, with a tooltip
  ("structural break: revenue −45% …"). New **"fit after break"** control (on
  by default) restricts both fits to the data after the most recent break.
  The effect on Abbott, whose pharma arm became AbbVie on 1 Jan 2013:
  revenue/share fitted over all history gives **+1.7%/yr with R²=0.17**
  (meaningless — two different companies); fitted after the break it gives
  **+6.2%/yr with R²=0.89**. Compare mode marks post-break tickers with `*`.
- **Screener**: two new screenable fields, `Years since last structural break`
  and `Number of structural breaks`, so a screen can exclude companies whose
  fits span a corporate transformation — e.g. type `no structural break`
  (= none in 10 years), `years since spinoff > 15`, `structural breaks < 1`.
- Note on what is NOT detected: separations too small to move revenue 35%+
  (JNJ/Kenvue, MMM/Solventum) do not trigger — by design, since they don't
  distort a fit materially.

## v1.11.0 — 2026-08-17

- **Free-text screening.** The fixed filter boxes (Max P/E, Max P/FCF, Min rev
  growth …) are gone. In their place are six empty boxes that accept ANY
  criterion in plain language — `P/E < 20`, `EPS growth > 15%`, `price to
  sales under 4`, `gross margin at least 40`, `FCF per share trend > 10%`,
  `EPS R² > 0.9`, `shares shrinking`. Each box shows the interpretation it
  applied ("✓ EPS growth (linear fit) > 15.0%") so nothing is applied blindly,
  and the border turns green (understood) or red (not understood).
  A built-in parser handles the wording above instantly and offline; anything
  it can't map is sent to the AI assistant to translate into
  {field, operator, value} (needs the StockLab password once). The three
  presets now WRITE INTO the boxes instead of hiding their logic.
- **Both fit families are now in the database and screenable** (`etl/
  history_export.py` → `docs/data/trends_<window>.json`, one file per window,
  ~250 KB each, loaded on demand): for 9 series (EPS, revenue/share,
  FCF/share, revenue, net income, FCF, gross margin, operating margin,
  book/share) × 3 windows (5y / 10y / all), each with **linear** (growth %/yr,
  R², slope/yr) and **exponential** (growth %/yr, R², b) parameters plus the
  quarter count — 378 screenable numbers per company.
- Screener gains **EPS CAGR / Rev-sh CAGR / FCF-sh CAGR** columns (exponential
  fit) next to the existing linear trend columns; hovering any of them shows
  both fits side by side. Every other fit parameter is reachable through the
  criteria boxes and the AI (e.g. "revenue R2 > 0.95", "net income CAGR > 20%").
- Exponential parameters verified against an independent numpy fit (AAPL EPS
  10y: +15.78%/yr, b=0.1465, R²=0.934 — exact match); a combined screen was
  cross-checked against a direct pandas query over the same files (27 tickers,
  identical list).

## v1.10.0 — 2026-08-17

- **Trend growth columns on the screener**: EPS trend, Rev/sh trend and
  FCF/sh trend — each the slope of a least-squares LINE through that
  company's quarterly series, expressed as a rate per year (slope ÷ average
  level, i.e. the slope relative to the fitted mid-point). Sortable like any
  column; hovering a cell shows the raw slope per year, the fit's R², and how
  many quarters it used.
- **Trend window selector** (5 years / 10 years / all history, default 10y)
  recomputes all three columns instantly, plus two new filters: **Min EPS
  trend %/yr** and **Min trend R²** (how straight the trend actually is).
- Computed in the pipeline (`etl/history_export.py` → `docs/data/trends.json`,
  156 KB) from the SPLIT- and share-basis-CORRECTED per-share series that the
  charts use — not the mixed-basis columns in per_quarter. Regenerated by
  every daily run, so the columns stay current automatically.
- **Guard against nonsense rates**: when a company's average level sits near
  zero (EPS swinging across zero, e.g. WBD), slope ÷ mean explodes — those
  cells now show "–" instead of a fake −2600%/yr, while the tooltip still
  reports the slope and R². 472 of 512 tickers have a meaningful EPS trend %.
- Verified against an independent numpy fit (AAPL EPS 10y: +13.5%/yr,
  slope +$0.65/share/yr, R²=0.932 — exact match). The AI assistant also
  receives the three new columns as context.

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
