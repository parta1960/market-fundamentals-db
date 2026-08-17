/* v1.3 AI chat assistant — bring-your-own-key, four providers, app control.
 *
 * Keys are stored ONLY in this browser (localStorage) and sent ONLY to the
 * selected AI provider. Nothing is ever written to the repo or the site.
 *
 * The model gets: the metric catalog, the current view state, and the current
 * ticker's (plus compare tickers') data for the visible range. It can control
 * the app by emitting a fenced block:  ```app {"t":"NVDA","m":["pe_ttm"],
 * "p":40,"c":["AMD"]} ```  which the page applies (t=ticker, m=metrics,
 * p=quarters back (0=max), c=compare tickers).
 */
(() => {
  const LS_KEYS = "mfdb_ai_keys", LS_PROV = "mfdb_ai_prov",
        LS_MODELS = "mfdb_ai_models", LS_CHOSEN = "mfdb_ai_model_choice",
        LS_PASS = "mfdb_ai_pass", LS_HIST = "mfdb_ai_hist";
  // v1.6.0: password-gated proxy — provider keys live server-side (Netlify
  // env vars), so ONE StockLab password unlocks all four providers on any
  // device. Per-provider BYOK keys still work as a fallback.
  const PROXY = "https://stocklab-ai-proxy.netlify.app/.netlify/functions/ai";
  // fallback lists only — the live list is fetched from each provider's own
  // /models endpoint with your key, so new top models appear automatically.
  // Snapshot refreshed 2026-08-16 (v1.5.0); shown ONLY until a key is saved.
  const PROVIDERS = {
    claude:   { name: "Claude",   models: ["claude-fable-5", "claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"],
                rank: ["fable", "opus", "sonnet", "haiku"] },
    gemini:   { name: "Gemini",   models: ["gemini-3.1-pro-preview", "gemini-3.7-flash", "gemini-2.5-pro"],
                rank: ["pro", "flash"] },
    deepseek: { name: "DeepSeek", models: ["deepseek-v4-pro", "deepseek-v4-flash"],
                rank: ["v4-pro", "pro", "v4-flash", "reasoner", "flash", "chat"] },
    kimi:     { name: "Kimi",     models: ["kimi-k3", "kimi-k2.7-code", "kimi-k2.6"],
                rank: ["k4", "k3", "k2"] },
  };
  const store = {
    keys: JSON.parse(localStorage.getItem(LS_KEYS) || "{}"),
    saveKeys() { localStorage.setItem(LS_KEYS, JSON.stringify(this.keys)); },
    prov: localStorage.getItem(LS_PROV) || "claude",
    saveProv() { localStorage.setItem(LS_PROV, this.prov); },
    models: JSON.parse(localStorage.getItem(LS_MODELS) || "{}"),   // {prov:{ts,list}}
    saveModels() { localStorage.setItem(LS_MODELS, JSON.stringify(this.models)); },
    chosen: JSON.parse(localStorage.getItem(LS_CHOSEN) || "{}"),   // {prov:id}
    saveChosen() { localStorage.setItem(LS_CHOSEN, JSON.stringify(this.chosen)); },
    pass: localStorage.getItem(LS_PASS) || "",
    savePass() { localStorage.setItem(LS_PASS, this.pass); },
  };
  // conversation persists on this device across reloads and page changes
  // (v1.9.2). Last 40 turns; app-command blocks stripped when re-displayed.
  let history = [];   // [{role:"user"|"assistant", text}]
  let busy = false;
  function saveHist() {
    try { localStorage.setItem(LS_HIST, JSON.stringify(history.slice(-40))); }
    catch (e) { /* quota — keep the in-memory conversation anyway */ }
  }

  /* ---------- styles ---------- */
  const css = `
  #slBar { position:fixed; top:0; left:0; right:0; z-index:70;
    display:flex; gap:8px; align-items:center; padding:8px 12px;
    background:rgba(13,17,23,.94); backdrop-filter:blur(6px);
    border-bottom:1px solid #30363d; min-height:52px; box-sizing:border-box; }
  #slBar select { background:#0d1117; color:#e6edf3; border:1px solid #30363d;
    border-radius:6px; padding:6px 8px; font-size:12.5px; max-width:165px; }
  #slBarIn { flex:1; min-width:110px; background:#161b22; color:#e6edf3;
    border:1px solid #30363d; border-radius:8px; padding:8px 12px; font-size:13.5px; }
  #slBarIn::placeholder { color:#6e7681; }
  .slBarBtn { background:#161b22; color:#e6edf3; border:1px solid #30363d;
    border-radius:8px; padding:7px 11px; font-size:14px; cursor:pointer; }
  .slBarBtn:hover { border-color:#6e7681; }
  #slBarSend { background:#1f6feb; border-color:#1f6feb; color:#fff; font-weight:700; }
  #slBarMic.on { color:#f85149; border-color:#f85149; }
  #slBarPill { display:none; color:#9aa4b2; }
  #slBar.min #slBarIn, #slBar.min #aiProv, #slBar.min #aiModel,
  #slBar.min #slBarMic, #slBar.min #slBarSend, #slBar.min #slBarAi { display:none; }
  #slBar.min #slBarPill { display:inline-block; }
  @media (max-width: 820px) { #slBar { gap:6px; padding:8px 8px; } }
  #aiPanel { position:fixed; right:0; top:52px; bottom:0; width:min(420px,100vw);
    z-index:60; background:#161b22; border-left:1px solid #30363d; display:none;
    flex-direction:column; font-size:13.5px; }
  #aiPanel.open { display:flex; }
  #aiHead { display:flex; gap:8px; align-items:center; padding:10px 12px;
    border-bottom:1px solid #30363d; flex-wrap:wrap; }
  #aiHead select, #aiHead input, #aiHead button {
    background:#0d1117; color:#e6edf3; border:1px solid #30363d; border-radius:6px;
    padding:5px 8px; font-size:12.5px; }
  #aiModel { width:150px; }
  #aiHead button { cursor:pointer; }
  #aiClose { margin-left:auto; }
  #aiKeyRow, #aiPassRow { display:none; gap:6px; padding:8px 12px; border-bottom:1px solid #30363d; }
  #aiKeyRow.open, #aiPassRow.open { display:flex; }
  #aiKeyRow input, #aiPassRow input { flex:1; background:#0d1117; color:#e6edf3; border:1px solid #30363d;
    border-radius:6px; padding:6px 8px; font-size:12px; }
  #aiKeyRow button, #aiPassRow button { background:#0d1117; color:#58a6ff; border:1px solid #30363d;
    border-radius:6px; padding:6px 10px; cursor:pointer; }
  #aiMsgs { flex:1; overflow-y:auto; padding:12px; display:flex; flex-direction:column;
    gap:10px; }
  .aiMsg { max-width:92%; padding:8px 11px; border-radius:10px; white-space:pre-wrap;
    line-height:1.45; word-break:break-word; }
  .aiMsg.user { align-self:flex-end; background:#1f6feb; color:#fff; }
  .aiMsg.bot  { align-self:flex-start; background:#0d1117; border:1px solid #30363d;
    color:#e6edf3; }
  .aiMsg.err  { align-self:flex-start; background:#3d1418; border:1px solid #f85149;
    color:#ffb3ad; }
  .aiMsg.act  { align-self:flex-start; color:#3fb950; background:transparent;
    padding:0 4px; font-size:12px; }
  #aiInRow { display:flex; gap:8px; padding:10px 12px; border-top:1px solid #30363d; }
  #aiIn { flex:1; background:#0d1117; color:#e6edf3; border:1px solid #30363d;
    border-radius:8px; padding:8px 10px; font-size:13.5px; resize:none; height:60px; }
  #aiSend { background:#1f6feb; color:#fff; border:none; border-radius:8px;
    padding:0 16px; font-weight:600; cursor:pointer; }
  #aiSend:disabled { opacity:.5; }
  #aiNote { padding:4px 12px 10px; color:#6e7681; font-size:11px; }
  #aiVer { color:#6e7681; font-size:11px; }
  #aiClose { margin-left:auto; color:#e6edf3; background:#30363d !important;
    border-color:#484f58 !important; font-weight:600; }
  #aiClose:hover { background:#f85149 !important; border-color:#f85149 !important;
    color:#fff; }
  #slBarAi.on { background:#1f6feb; border-color:#1f6feb; color:#fff; }`;
  const st = document.createElement("style"); st.textContent = css;
  document.head.appendChild(st);

  /* ---------- UI ---------- */
  // v1.8.0: one FIXED top bar consolidates the menu, the AI entry box, the
  // provider/model pickers, dictation and send — stays put while scrolling,
  // minimizable with the >< button (state remembered per device).
  const bar = document.createElement("div");
  bar.id = "slBar";
  bar.innerHTML = `
    <span id="slMenuSlot"></span>
    <button class="slBarBtn" id="slBarAi" title="open / close the AI panel">🤖</button>
    <input id="slBarIn" placeholder="Ask StockLab AI — about any company's 20-year data, or tell it what to chart…">
    <select id="aiProv" title="AI provider"></select>
    <select id="aiModel" title="model — list auto-updates from the provider"></select>
    <button class="slBarBtn" id="slBarMic" title="dictate your question">🎤</button>
    <button class="slBarBtn" id="slBarSend" title="send to the AI">↑</button>
    <button class="slBarBtn" id="slBarPill">🤖 Ask StockLab AI</button>
    <button class="slBarBtn" id="slBarMin" title="minimize / expand the chat box">&gt;&lt;</button>`;
  document.body.prepend(bar);
  document.body.style.paddingTop = "56px";
  const panel = document.createElement("div");
  panel.id = "aiPanel";
  panel.innerHTML = `
    <div id="aiHead">
      <button id="aiKeyBtn" title="set the StockLab password or an API key">🔑 key</button>
      <button id="aiClear" title="erase the saved conversation">↺ clear</button>
      <span id="aiVer"></span>
      <button id="aiClose" title="close the assistant (Esc)">✕ Close</button>
    </div>
    <div id="aiPassRow">
      <input id="aiPassIn" type="password" placeholder="StockLab password — unlocks ALL providers (easiest)">
      <button id="aiPassSave">unlock</button>
    </div>
    <div id="aiKeyRow">
      <input id="aiKeyIn" type="password" placeholder="…or paste this provider's own API key (this browser only)">
      <button id="aiKeySave">save</button>
    </div>
    <div id="aiMsgs"></div>
    <div id="aiInRow">
      <textarea id="aiIn" placeholder="Ask about this company's data, or tell me to change the charts…"></textarea>
      <button id="aiSend">Send</button>
    </div>
    <div id="aiNote">One StockLab password (🔑) unlocks all providers — keys stay
    server-side. The model sees the data currently charted and can drive the app —
    try "compare NVDA and AMD gross margins over 15 years".</div>`;
  document.body.appendChild(panel);
  const el = id => document.getElementById(id);
  if (typeof STOCKLAB_VERSION !== "undefined")
    el("aiVer").textContent = "StockLab " + STOCKLAB_VERSION;

  /* ---------- top-bar behaviour (v1.8.0) ---------- */
  const barIn = el("slBarIn");
  // single place that opens/closes the assistant, so the 🤖 button state,
  // the Esc key and the ✕ Close button can never disagree (v1.9.2)
  function setPanel(open) {
    panel.classList.toggle("open", open);
    el("slBarAi").classList.toggle("on", open);
    if (open) { keyHint(); refreshModels(false); }
  }
  function sendFromBar() {
    const v = barIn.value.trim();
    setPanel(true);
    if (!v) return;
    barIn.value = "";
    el("aiIn").value = v;
    send();
  }
  el("slBarSend").onclick = sendFromBar;
  barIn.addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); sendFromBar(); } });
  el("slBarAi").onclick = () => setPanel(!panel.classList.contains("open"));
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && panel.classList.contains("open")) setPanel(false);
  });
  el("slBarPill").onclick = () => setMin(false);
  const LS_MIN = "mfdb_bar_min";
  function setMin(m) {
    bar.classList.toggle("min", m);
    localStorage.setItem(LS_MIN, m ? "1" : "0");
    el("slBarMin").textContent = m ? "<>" : "><";
    el("slBarMin").title = m ? "expand the chat box" : "minimize the chat box";
  }
  el("slBarMin").onclick = () => setMin(!bar.classList.contains("min"));
  setMin(localStorage.getItem(LS_MIN) === "1");
  // 🎤 dictation via the browser's speech recognition (where supported)
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { el("slBarMic").style.display = "none"; }
  else {
    let rec = null;
    el("slBarMic").onclick = () => {
      if (rec) { rec.stop(); return; }
      rec = new SR(); rec.interimResults = true; rec.continuous = false;
      const base = barIn.value;
      rec.onresult = ev => {
        let t = "";
        for (const r of ev.results) t += r[0].transcript;
        barIn.value = (base ? base + " " : "") + t;
      };
      rec.onend = () => { rec = null; el("slBarMic").classList.remove("on"); };
      rec.onerror = rec.onend;
      el("slBarMic").classList.add("on");
      rec.start();
    };
  }
  // narrow screens (v1.8.1): the provider/model pickers relocate into the
  // panel head so the send / minimize buttons always stay reachable on phones
  const mqNarrow = matchMedia("(max-width: 820px)");
  function placePickers() {
    const prov = el("aiProv"), model = el("aiModel");
    if (mqNarrow.matches) {
      const head = el("aiHead"), key = el("aiKeyBtn");
      head.insertBefore(prov, key); head.insertBefore(model, key);
    } else {
      bar.insertBefore(prov, el("slBarMic"));
      bar.insertBefore(model, el("slBarMic"));
    }
  }
  placePickers();
  if (mqNarrow.addEventListener) mqNarrow.addEventListener("change", placePickers);
  const provSel = el("aiProv"), modelIn = el("aiModel");
  Object.entries(PROVIDERS).forEach(([k, p]) => {
    const o = document.createElement("option"); o.value = k; o.textContent = p.name;
    provSel.appendChild(o);
  });
  provSel.value = store.prov;

  /* ----- model list: live from each provider's /models endpoint ----- */
  function rankModels(ids, prec) {
    const score = id => { const i = prec.findIndex(p => id.includes(p));
      return i < 0 ? prec.length : i; };
    return [...new Set(ids)].sort((a, b) => score(a) - score(b) ||
      b.localeCompare(a, undefined, { numeric: true }));
  }
  function setModelOptions(list) {
    modelIn.innerHTML = "";
    list.forEach(id => { const o = document.createElement("option");
      o.value = o.textContent = id; modelIn.appendChild(o); });
    const pick = store.chosen[store.prov];
    modelIn.value = list.includes(pick) ? pick : list[0];
  }
  async function fetchModels(prov, key) {
    const P = PROVIDERS[prov];
    let ids = [];
    if (prov === "claude") {
      const r = await fetch("https://api.anthropic.com/v1/models?limit=100", {
        headers: { "x-api-key": key, "anthropic-version": "2023-06-01",
          "anthropic-dangerous-direct-browser-access": "true" } });
      const j = await r.json(); if (!r.ok) throw new Error(j.error?.message || r.status);
      ids = (j.data || []).map(m => m.id);
    } else if (prov === "gemini") {
      const r = await fetch("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key=" + key);
      const j = await r.json(); if (!r.ok) throw new Error(j.error?.message || r.status);
      ids = (j.models || [])
        .filter(m => (m.supportedGenerationMethods || []).includes("generateContent"))
        .map(m => (m.name || "").replace("models/", ""))
        .filter(n => !/embed|aqa|imagen|veo|tts|audio|image|live/.test(n));
    } else {
      const base = prov === "deepseek" ? "https://api.deepseek.com"
                                       : "https://api.moonshot.ai/v1";
      const r = await fetch(base + "/models",
        { headers: { authorization: "Bearer " + key } });
      const j = await r.json(); if (!r.ok) throw new Error(j.error?.message || j.error || r.status);
      ids = (j.data || []).map(m => m.id);
    }
    return rankModels(ids, P.rank);
  }
  async function pcall(body) {   // call the password-gated proxy (v1.6.0)
    const r = await fetch(PROXY, { method: "POST",
      headers: { "content-type": "application/json",
                 "x-stocklab-pass": store.pass },
      body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
    return j;
  }
  const _noted = {};   // one status note per provider per page load, no spam
  async function refreshModels(force) {
    const prov = store.prov, key = store.keys[prov], viaProxy = !!store.pass;
    const cached = store.models[prov];
    setModelOptions((cached && cached.list.length ? cached.list
                     : PROVIDERS[prov].models));
    if (!key && !viaProxy) {
      if (!_noted[prov]) { _noted[prov] = 1;
        msg("act", PROVIDERS[prov].name + ": showing the BUILT-IN model list — " +
          "tap 🔑 and enter the StockLab password once (unlocks ALL providers), " +
          "or save this provider's API key, to load the live top-model list."); }
      return;
    }
    if (!force && cached && Date.now() - cached.ts < 864e5) return;  // 24h cache
    try {
      const list = viaProxy
        ? rankModels((await pcall({ prov, op: "models" })).models || [],
                     PROVIDERS[prov].rank)
        : await fetchModels(prov, key);
      if (list.length) {
        store.models[prov] = { ts: Date.now(), list }; store.saveModels();
        setModelOptions(list);
        msg("act", PROVIDERS[prov].name + " LIVE model list loaded (" +
          list.length + " available, top: " + list[0] + ").");
      }
    } catch (e) {
      if (!_noted[prov]) { _noted[prov] = 1;
        msg("err", PROVIDERS[prov].name + " model-list refresh failed (" +
          (e.message || e) + ") — showing the built-in list instead."); }
    }
  }
  modelIn.onchange = () => { store.chosen[store.prov] = modelIn.value;
    store.saveChosen(); };

  el("aiClose").onclick = () => setPanel(false);
  el("aiClear").onclick = () => {
    history = []; saveHist(); el("aiMsgs").innerHTML = "";
    msg("act", "Conversation cleared on this device."); keyHint();
  };
  provSel.onchange = () => { store.prov = provSel.value; store.saveProv();
    keyHint(); refreshModels(false); };
  el("aiKeyBtn").onclick = () => { el("aiKeyRow").classList.toggle("open");
    el("aiPassRow").classList.toggle("open"); };
  el("aiKeySave").onclick = () => {
    const v = el("aiKeyIn").value.trim();
    if (v) { store.keys[store.prov] = v; store.saveKeys(); el("aiKeyIn").value = "";
      el("aiKeyRow").classList.remove("open"); el("aiPassRow").classList.remove("open");
      msg("act", PROVIDERS[store.prov].name + " key saved on this device.");
      refreshModels(true); }
  };
  el("aiPassSave").onclick = async () => {
    const v = el("aiPassIn").value.trim();
    if (!v) return;
    store.pass = v; store.savePass(); el("aiPassIn").value = "";
    el("aiKeyRow").classList.remove("open"); el("aiPassRow").classList.remove("open");
    try {
      await pcall({ prov: "claude", op: "models" });
      msg("act", "✓ StockLab password accepted — all 4 providers unlocked on this device.");
      store.models = {}; store.saveModels();   // drop stale lists, refetch live
      refreshModels(true);
    } catch (e) {
      store.pass = ""; store.savePass();
      msg("err", "Password rejected: " + e.message);
    }
  };
  // hook for the site menu (v1.7.0): open the panel with both setup rows
  window.__ai = { setup() {
    setPanel(true);
    el("aiPassRow").classList.add("open"); el("aiKeyRow").classList.add("open");
  } };
  // restore the saved conversation (v1.9.2) — survives reloads and moving
  // between the screener and the charts page
  (function restoreHist() {
    let saved = [];
    try { saved = JSON.parse(localStorage.getItem(LS_HIST) || "[]"); }
    catch (e) { saved = []; }
    if (!Array.isArray(saved) || !saved.length) return;
    history = saved;
    for (const m of saved) {
      const txt = String(m.text || "").replace(/```app[\s\S]*?```/g, "").trim();
      if (txt) msg(m.role === "user" ? "user" : "bot", txt);
    }
    msg("act", "↑ earlier conversation restored (↺ clear erases it).");
  })();
  refreshModels(false);
  el("aiSend").onclick = send;
  el("aiIn").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });

  function keyHint() {
    if (!store.pass && !store.keys[store.prov])
      msg("act", "Tap 🔑 and enter the StockLab password once — it unlocks all " +
        "4 providers on this device (or paste a per-provider API key instead).");
  }
  function msg(cls, text) {
    const d = document.createElement("div");
    d.className = "aiMsg " + cls; d.textContent = text;
    el("aiMsgs").appendChild(d); el("aiMsgs").scrollTop = 1e9;
    return d;
  }

  /* ---------- context ---------- */
  function seriesRows(hist, keys, per) {
    const q = hist.quarters, n = q.length, from = per && n > per ? n - per : 0;
    const lines = ["quarter," + keys.join(",")];
    for (let i = from; i < n; i++)
      lines.push(q[i] + "," + keys.map(k => {
        const v = (hist.series[k] || [])[i];
        return v === null || v === undefined ? "" : v; }).join(","));
    return lines.join("\n");
  }
  async function buildContext() {
    if (!window.__app && window.__screener) {
      // screener (landing) page: give the model the current snapshot table
      const rows = window.__screener.rows().slice(0, 300);
      const cols = ["ticker", "name", "sector", "close", "pe_ttm", "ps_ttm",
        "pfcf_ttm", "pb", "gross_margin", "op_margin", "net_margin",
        "rev_yoy", "ni_yoy", "shares_yoy",
        "eps_gr", "rps_gr", "fps_gr"];   // linear-fit trend rates (v1.10.0)
      const csv = [cols.join(",")].concat(rows.map(r =>
        cols.map(c => r[c] === null || r[c] === undefined ? "" : r[c]).join(",")
      )).join("\n");
      return `Current page: StockLab screener — latest TTM snapshot of ` +
        `${rows.length} S&P 500 + Nasdaq-100 companies.\nCSV:\n${csv}\n`;
    }
    const A = window.__app, s = A.state();
    const man = A.MAN();
    const cat = man.metrics.map(m => `${m.k} (${m.label}, unit:${m.unit})`).join("; ");
    let ctx = `Current view: ticker=${s.t}, metrics=${s.metrics.join(",")}, ` +
      `quarters_back=${s.per || "max"}, compare=${s.cmp.join(",") || "none"}.\n` +
      `Metric catalog: ${cat}\n`;
    const wanted = [...new Set([...s.metrics, "revenue_ttm", "eps_ttm", "fcf_ttm",
      "pe_ttm", "gross_margin", "shares"])];
    for (const t of [s.t, ...s.cmp.slice(0, 3)]) {
      try {
        const h = await A.getHist(t);
        ctx += `\nDATA ${t} (${h.name}, ${h.sector}) quarterly CSV:\n` +
          seriesRows(h, wanted.filter(k => h.series[k]), s.per || 0) + "\n";
      } catch (e) { /* unknown ticker */ }
    }
    return ctx;
  }
  const SYSTEM = `You are the built-in analyst of a stock fundamentals web app
showing ~20 years of quarterly financials and valuation history for S&P 500 +
Nasdaq-100 companies. Be concise and numeric; cite quarters when quoting values.
Data provided is quarterly; TTM = trailing twelve months; ratios use unadjusted
quarter-end prices with same-date share counts. If asked to change what is
displayed (different ticker, metrics, range, or comparisons), reply briefly AND
include exactly one fenced block like:
\`\`\`app
{"t":"NVDA","m":["gross_margin","pe_ttm"],"p":60,"c":["AMD"]}
\`\`\`
where t=ticker, m=metric keys from the catalog (max 6), p=quarters back
(20=5y, 40=10y, 60=15y, 80=20y, 0=all), c=compare tickers (max 3, only with a
single metric). Only include the block when the user wants the view changed.
On the screener page the block opens the History Charts page with that view.
Not investment advice; data may contain gaps.`;

  /* ---------- providers ---------- */
  async function callClaude(key, model, sys, msgs) {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "content-type": "application/json", "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true" },
      body: JSON.stringify({ model, max_tokens: 1500, system: sys,
        messages: msgs.map(m => ({ role: m.role, content: m.text })) }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error?.message || r.status);
    return j.content.map(c => c.text || "").join("");
  }
  async function callGemini(key, model, sys, msgs) {
    const r = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`,
      { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({
          system_instruction: { parts: [{ text: sys }] },
          contents: msgs.map(m => ({ role: m.role === "assistant" ? "model" : "user",
            parts: [{ text: m.text }] })) }) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error?.message || r.status);
    return (j.candidates?.[0]?.content?.parts || []).map(p => p.text || "").join("");
  }
  async function callOpenAIStyle(base, key, model, sys, msgs) {
    const r = await fetch(base + "/chat/completions", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer " + key },
      body: JSON.stringify({ model, max_tokens: 1500, messages: [
        { role: "system", content: sys },
        ...msgs.map(m => ({ role: m.role, content: m.text }))] }) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error?.message || j.error || r.status);
    return j.choices?.[0]?.message?.content || "";
  }
  const CALLERS = {
    claude: (k, m, s, h) => callClaude(k, m, s, h),
    gemini: (k, m, s, h) => callGemini(k, m, s, h),
    deepseek: (k, m, s, h) => callOpenAIStyle("https://api.deepseek.com", k, m, s, h),
    kimi: (k, m, s, h) => callOpenAIStyle("https://api.moonshot.ai/v1", k, m, s, h),
  };

  /* ---------- app control ---------- */
  function applyAppBlock(text) {
    const m = text.match(/```app\s*([\s\S]*?)```/);
    if (!m) return text;
    try {
      const cmd = JSON.parse(m[1]);
      if (!window.__app) {
        // not on the charts page — navigate there with the requested view
        const u = new URLSearchParams();
        if (cmd.t) u.set("t", String(cmd.t).toUpperCase());
        if (Array.isArray(cmd.m) && cmd.m.length) u.set("m", cmd.m.join(","));
        if (cmd.p) u.set("p", cmd.p);
        if (Array.isArray(cmd.c) && cmd.c.length)
          u.set("c", cmd.c.map(x => String(x).toUpperCase()).join(","));
        msg("act", "✓ opening History Charts with that view…");
        setTimeout(() => { location.href = "charts.html?" + u.toString(); }, 1400);
        return text.replace(m[0], "").trim();
      }
      window.__app.apply(cmd);
      const bits = [];
      if (cmd.t) bits.push("ticker → " + cmd.t);
      if (cmd.m) bits.push("metrics → " + cmd.m.join(", "));
      if (cmd.p !== undefined) bits.push("range → " + (cmd.p ? cmd.p / 4 + "y" : "max"));
      if (cmd.c && cmd.c.length) bits.push("compare → " + cmd.c.join(", "));
      msg("act", "✓ applied: " + bits.join(" · "));
    } catch (e) { msg("err", "App command failed: " + e.message); }
    return text.replace(m[0], "").trim();
  }

  /* ---------- send ---------- */
  async function send() {
    if (busy) return;
    const q = el("aiIn").value.trim();
    if (!q) return;
    const key = store.keys[store.prov];
    if (!key && !store.pass) { msg("err", "Tap 🔑 and enter the StockLab " +
      "password (or a " + PROVIDERS[store.prov].name + " API key) once."); return; }
    el("aiIn").value = ""; msg("user", q);
    history.push({ role: "user", text: q }); saveHist();
    busy = true; el("aiSend").disabled = true;
    const wait = msg("act", "thinking…");
    try {
      const sys = SYSTEM + "\n\n" + await buildContext();
      const recent = history.slice(-12);
      const raw = store.pass
        ? (await pcall({ prov: store.prov, op: "chat",
            model: modelIn.value.trim(), system: sys,
            messages: recent.map(m => ({ role: m.role, content: m.text })) })).text
        : await CALLERS[store.prov](key, modelIn.value.trim(), sys, recent);
      wait.remove();
      const clean = applyAppBlock(raw);
      if (clean) msg("bot", clean);
      history.push({ role: "assistant", text: raw }); saveHist();
    } catch (e) {
      wait.remove();
      let hint = "";
      if (/failed to fetch/i.test(e.message))
        hint = " (This provider may not allow direct browser calls — try Claude or Gemini, or ask Claude-the-builder for the proxy option.)";
      if (/wrong stocklab password/i.test(e.message))
        hint = " (Re-enter the StockLab password via 🔑.)";
      else if (/401|invalid|auth/i.test(e.message))
        hint = " (Key rejected — re-enter it via 🔑, or the key may have expired.)";
      msg("err", PROVIDERS[store.prov].name + ": " + e.message + hint);
    }
    busy = false; el("aiSend").disabled = false;
  }
})();
