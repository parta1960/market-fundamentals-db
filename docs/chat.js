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
  const LS_KEYS = "mfdb_ai_keys", LS_PROV = "mfdb_ai_prov";
  const PROVIDERS = {
    claude:   { name: "Claude",   model: "claude-sonnet-4-5" },
    gemini:   { name: "Gemini",   model: "gemini-2.5-flash" },
    deepseek: { name: "DeepSeek", model: "deepseek-chat" },
    kimi:     { name: "Kimi",     model: "kimi-k3" },
  };
  const store = {
    keys: JSON.parse(localStorage.getItem(LS_KEYS) || "{}"),
    saveKeys() { localStorage.setItem(LS_KEYS, JSON.stringify(this.keys)); },
    prov: localStorage.getItem(LS_PROV) || "claude",
    saveProv() { localStorage.setItem(LS_PROV, this.prov); },
  };
  let history = [];   // [{role:"user"|"assistant", text}]
  let busy = false;

  /* ---------- styles ---------- */
  const css = `
  #aiFab { position:fixed; right:18px; bottom:18px; z-index:50; background:#1f6feb;
    color:#fff; border:none; border-radius:24px; padding:12px 18px; font-size:14px;
    font-weight:600; cursor:pointer; box-shadow:0 4px 14px rgba(0,0,0,.5); }
  #aiPanel { position:fixed; right:0; top:0; bottom:0; width:min(420px,100vw);
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
  #aiKeyRow { display:none; gap:6px; padding:8px 12px; border-bottom:1px solid #30363d; }
  #aiKeyRow.open { display:flex; }
  #aiKeyRow input { flex:1; background:#0d1117; color:#e6edf3; border:1px solid #30363d;
    border-radius:6px; padding:6px 8px; font-size:12px; }
  #aiKeyRow button { background:#0d1117; color:#58a6ff; border:1px solid #30363d;
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
  #aiNote { padding:4px 12px 10px; color:#6e7681; font-size:11px; }`;
  const st = document.createElement("style"); st.textContent = css;
  document.head.appendChild(st);

  /* ---------- UI ---------- */
  const fab = document.createElement("button");
  fab.id = "aiFab"; fab.textContent = "🤖 AI";
  document.body.appendChild(fab);
  const panel = document.createElement("div");
  panel.id = "aiPanel";
  panel.innerHTML = `
    <div id="aiHead">
      <select id="aiProv"></select>
      <input id="aiModel" title="model name">
      <button id="aiKeyBtn" title="set API key for this provider">🔑 key</button>
      <button id="aiClear" title="clear conversation">↺</button>
      <button id="aiClose">✕</button>
    </div>
    <div id="aiKeyRow">
      <input id="aiKeyIn" type="password" placeholder="paste API key (stored only in this browser)">
      <button id="aiKeySave">save</button>
    </div>
    <div id="aiMsgs"></div>
    <div id="aiInRow">
      <textarea id="aiIn" placeholder="Ask about this company's data, or tell me to change the charts…"></textarea>
      <button id="aiSend">Send</button>
    </div>
    <div id="aiNote">Key lives only in this browser. Model sees the data currently
    charted. It can drive the app — try "compare NVDA and AMD gross margins over
    15 years".</div>`;
  document.body.appendChild(panel);
  const el = id => document.getElementById(id);
  const provSel = el("aiProv"), modelIn = el("aiModel");
  Object.entries(PROVIDERS).forEach(([k, p]) => {
    const o = document.createElement("option"); o.value = k; o.textContent = p.name;
    provSel.appendChild(o);
  });
  provSel.value = store.prov; modelIn.value = PROVIDERS[store.prov].model;

  fab.onclick = () => { panel.classList.add("open"); keyHint(); };
  el("aiClose").onclick = () => panel.classList.remove("open");
  el("aiClear").onclick = () => { history = []; el("aiMsgs").innerHTML = ""; keyHint(); };
  provSel.onchange = () => { store.prov = provSel.value; store.saveProv();
    modelIn.value = PROVIDERS[store.prov].model; keyHint(); };
  el("aiKeyBtn").onclick = () => el("aiKeyRow").classList.toggle("open");
  el("aiKeySave").onclick = () => {
    const v = el("aiKeyIn").value.trim();
    if (v) { store.keys[store.prov] = v; store.saveKeys(); el("aiKeyIn").value = "";
      el("aiKeyRow").classList.remove("open"); msg("act", PROVIDERS[store.prov].name + " key saved on this device."); }
  };
  el("aiSend").onclick = send;
  el("aiIn").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });

  function keyHint() {
    if (!store.keys[store.prov])
      msg("act", "No " + PROVIDERS[store.prov].name + " key on this device yet — tap 🔑 key to add it once.");
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
    if (!key) { msg("err", "No " + PROVIDERS[store.prov].name +
      " API key on this device. Tap 🔑 key and paste it once."); return; }
    el("aiIn").value = ""; msg("user", q);
    history.push({ role: "user", text: q });
    busy = true; el("aiSend").disabled = true;
    const wait = msg("act", "thinking…");
    try {
      const sys = SYSTEM + "\n\n" + await buildContext();
      const recent = history.slice(-12);
      const raw = await CALLERS[store.prov](key, modelIn.value.trim(), sys, recent);
      wait.remove();
      const clean = applyAppBlock(raw);
      if (clean) msg("bot", clean);
      history.push({ role: "assistant", text: raw });
    } catch (e) {
      wait.remove();
      let hint = "";
      if (/failed to fetch/i.test(e.message))
        hint = " (This provider may not allow direct browser calls — try Claude or Gemini, or ask Claude-the-builder for the proxy option.)";
      if (/401|invalid|auth/i.test(e.message))
        hint = " (Key rejected — re-enter it via 🔑, or the key may have expired.)";
      msg("err", PROVIDERS[store.prov].name + ": " + e.message + hint);
    }
    busy = false; el("aiSend").disabled = false;
  }
})();
