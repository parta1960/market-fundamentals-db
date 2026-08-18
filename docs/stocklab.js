/* StockLab shared module (v1.15.0)
 * - page navigation history (back / forward / latest) in the fixed top bar
 * - favorites (★) and named portfolios (▦) on every stock, kept in
 *   localStorage and listed in the ☰ menu
 * - saved screens (named screening tasks) for the screener page
 * - cross-device sync of favorites / portfolios / saved screens / AI chat
 *   through the StockLab proxy (needs the StockLab password once) — the same
 *   state appears on phone and desktop
 * - Yahoo Finance deep links per stock
 */
(() => {
  const LS = {
    favs: "mfdb_favs", ports: "mfdb_ports", screens: "mfdb_screens",
    hist: "mfdb_ai_hist", ts: "mfdb_sync_ts", pass: "mfdb_ai_pass",
  };
  const PROXY = "https://stocklab-ai-proxy.netlify.app/.netlify/functions/ai";
  const get = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; }
                          catch (e) { return d; } };
  const set = (k, v) => localStorage.setItem(k, JSON.stringify(v));

  /* ---------- styles ---------- */
  const css = `
  .slNavBtn { background:#161b22; color:#9aa4b2; border:1px solid #30363d;
    border-radius:8px; padding:7px 9px; font-size:13px; cursor:pointer; }
  .slNavBtn:hover { color:#e6edf3; border-color:#6e7681; }
  .slNavBtn[disabled] { opacity:.35; cursor:default; }
  @media (max-width: 600px) { #slNavLatest { display:none; } }
  .slStar { cursor:pointer; color:#6e7681; padding:0 2px; }
  .slStar.on { color:#e3b341; }
  .slStar:hover { color:#e3b341; }
  .slPort { cursor:pointer; color:#6e7681; padding:0 2px; font-size:12px; }
  .slPort:hover, .slPort.on { color:#58a6ff; }
  .slY { color:#6e7681; font-size:10px; text-decoration:none; padding:0 2px;
    border:1px solid #30363d; border-radius:4px; }
  .slY:hover { color:#a58fff; border-color:#a58fff; }
  #slPortPop { position:absolute; z-index:90; background:#161b22;
    border:1px solid #30363d; border-radius:10px; padding:8px 0; width:230px;
    box-shadow:0 8px 28px rgba(0,0,0,.6); font-size:13px; color:#e6edf3; }
  #slPortPop .pp { display:flex; gap:8px; align-items:center; padding:7px 14px;
    cursor:pointer; }
  #slPortPop .pp:hover { background:#1c2128; }
  #slPortPop .pp input { accent-color:#58a6ff; }
  #slPortPop .pnew { color:#58a6ff; border-top:1px solid #21262d; }
  #slPortPop .phead { padding:4px 14px 8px; color:#6e7681; font-size:11px;
    border-bottom:1px solid #21262d; }
`;
  const st = document.createElement("style"); st.textContent = css;
  document.head.appendChild(st);

  /* ---------- page navigation (v1.15.0) ---------- */
  const NAV = "sl_nav", MOVE = "sl_navmove";
  let nav = null;
  try { nav = JSON.parse(sessionStorage.getItem(NAV)); } catch (e) { /* - */ }
  if (!nav || !Array.isArray(nav.list)) nav = { list: [], i: -1 };
  const here = location.pathname.split("/").pop() + location.search || "index.html";
  if (sessionStorage.getItem(MOVE)) sessionStorage.removeItem(MOVE);
  else if (nav.list[nav.i] !== here) {
    nav.list = nav.list.slice(0, nav.i + 1);
    nav.list.push(here); nav.i = nav.list.length - 1;
    if (nav.list.length > 60) { nav.list.shift(); nav.i--; }
  }
  sessionStorage.setItem(NAV, JSON.stringify(nav));
  function goTo(idx) {
    if (idx < 0 || idx >= nav.list.length || idx === nav.i) return;
    nav.i = idx;
    sessionStorage.setItem(NAV, JSON.stringify(nav));
    sessionStorage.setItem(MOVE, "1");
    location.href = nav.list[idx];
  }
  function mountNav() {
    const bar = document.getElementById("slBar");
    if (!bar) { setTimeout(mountNav, 150); return; }
    const slot = document.getElementById("slMenuSlot");
    const wrap = document.createElement("span");
    wrap.style.cssText = "display:flex;gap:4px;align-items:center;";
    wrap.innerHTML = `
      <button class="slNavBtn" id="slNavBack" title="back to the previous view">◀</button>
      <button class="slNavBtn" id="slNavFwd" title="forward">▶</button>
      <button class="slNavBtn" id="slNavLatest" title="jump to the most recent view">⇥ latest</button>`;
    bar.insertBefore(wrap, slot ? slot.nextSibling : bar.firstChild);
    const B = id => document.getElementById(id);
    B("slNavBack").disabled = nav.i <= 0;
    B("slNavFwd").disabled = nav.i >= nav.list.length - 1;
    B("slNavLatest").disabled = nav.i >= nav.list.length - 1;
    B("slNavBack").onclick = () => goTo(nav.i - 1);
    B("slNavFwd").onclick = () => goTo(nav.i + 1);
    B("slNavLatest").onclick = () => goTo(nav.list.length - 1);
  }
  mountNav();

  /* ---------- favorites & portfolios ---------- */
  const favs = () => get(LS.favs, []);
  const ports = () => get(LS.ports, {});
  const isFav = t => favs().includes(t);
  function toggleFav(t) {
    const f = favs(), i = f.indexOf(t);
    i >= 0 ? f.splice(i, 1) : f.push(t);
    set(LS.favs, f); touch();
  }
  const inAnyPort = t => Object.values(ports()).some(l => l.includes(t));
  function togglePort(name, t) {
    const p = ports(); p[name] = p[name] || [];
    const i = p[name].indexOf(t);
    i >= 0 ? p[name].splice(i, 1) : p[name].push(t);
    set(LS.ports, p); touch();
  }
  function paint(root) {
    (root || document).querySelectorAll(".slStar").forEach(x => {
      const on = isFav(x.dataset.t);
      x.textContent = on ? "★" : "☆"; x.classList.toggle("on", on);
      x.title = on ? "remove from favorites" : "add to favorites";
    });
    (root || document).querySelectorAll(".slPort").forEach(x =>
      x.classList.toggle("on", inAnyPort(x.dataset.t)));
  }
  const yahoo = t => "https://finance.yahoo.com/quote/" + encodeURIComponent(t);
  const controlsHTML = t =>
    `<span class="slStar" data-t="${t}">☆</span>` +
    `<span class="slPort" data-t="${t}" title="add to a portfolio">▦</span>` +
    `<a class="slY" href="${yahoo(t)}" target="_blank" rel="noopener"` +
    ` title="open ${t} on Yahoo Finance">Y!</a>`;

  let pop = null;
  function closePop() { if (pop) { pop.remove(); pop = null; } }
  function openPortPop(btn) {
    closePop();
    const t = btn.dataset.t, p = ports();
    pop = document.createElement("div"); pop.id = "slPortPop";
    const items = Object.keys(p).sort().map(n =>
      `<label class="pp"><input type="checkbox" data-n="${n}"` +
      `${p[n].includes(t) ? " checked" : ""}> ${n} <span style="color:#6e7681">` +
      `(${p[n].length})</span></label>`).join("");
    pop.innerHTML = `<div class="phead">${t} → portfolio</div>` + items +
      `<div class="pp pnew" id="slPortNew">＋ New portfolio…</div>`;
    document.body.appendChild(pop);
    const r = btn.getBoundingClientRect();
    pop.style.left = Math.min(r.left, innerWidth - 240) + "px";
    pop.style.top = (r.bottom + scrollY + 4) + "px";
    pop.querySelectorAll("input[data-n]").forEach(cb =>
      cb.onchange = () => { togglePort(cb.dataset.n, t); paint(); });
    pop.querySelector("#slPortNew").onclick = () => {
      const n = (prompt("Name for the new portfolio:") || "").trim();
      if (!n) return;
      togglePort(n, t); paint(); closePop();
    };
  }
  document.addEventListener("click", e => {
    const s = e.target.closest(".slStar");
    if (s) { toggleFav(s.dataset.t); paint(); e.stopPropagation(); return; }
    const b = e.target.closest(".slPort");
    if (b) { openPortPop(b); e.stopPropagation(); return; }
    if (pop && !pop.contains(e.target)) closePop();
  });

  /* ---------- saved screens ---------- */
  const screens = () => get(LS.screens, {});
  function saveScreen(name, data) {
    const s = screens(); s[name] = data; set(LS.screens, s); touch();
  }
  function delScreen(name) {
    const s = screens(); delete s[name]; set(LS.screens, s); touch();
  }
  function delPort(name) {
    const p = ports(); delete p[name]; set(LS.ports, p); touch();
  }

  /* ---------- cross-device sync via the proxy (v1.15.0) ----------
   * One JSON blob {ts, favs, ports, screens, hist} lives server-side next to
   * the AI keys, gated by the same StockLab password. Newest timestamp wins:
   * on page load we pull; on any local change we push (debounced). */
  let pushTimer = null;
  async function pcall(body) {
    const pass = localStorage.getItem(LS.pass) || "";
    if (!pass) throw new Error("no pass");
    const r = await fetch(PROXY, { method: "POST",
      headers: { "content-type": "application/json", "x-stocklab-pass": pass },
      body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
    return j;
  }
  function snapshot() {
    return { ts: get(LS.ts, 0), favs: favs(), ports: ports(),
             screens: screens(), hist: get(LS.hist, []) };
  }
  function touch() {
    set(LS.ts, Date.now());
    clearTimeout(pushTimer);
    pushTimer = setTimeout(() => {
      pcall({ op: "sync_put", data: snapshot() }).catch(() => {});
    }, 2500);
  }
  async function pull() {
    try {
      const j = await pcall({ op: "sync_get" });
      const d = j.data;
      if (!d || typeof d.ts !== "number") return;
      const localTs = get(LS.ts, 0);
      if (d.ts <= localTs) {          // local is newer (or same) → push it up
        if (d.ts < localTs) pcall({ op: "sync_put", data: snapshot() }).catch(() => {});
        return;
      }
      if (Array.isArray(d.favs)) set(LS.favs, d.favs);
      if (d.ports && typeof d.ports === "object") set(LS.ports, d.ports);
      if (d.screens && typeof d.screens === "object") set(LS.screens, d.screens);
      if (Array.isArray(d.hist)) {
        set(LS.hist, d.hist);
        if (window.__ai && window.__ai.reloadHist) window.__ai.reloadHist();
      }
      set(LS.ts, d.ts);
      paint();
      document.dispatchEvent(new Event("slsync"));
    } catch (e) { /* offline / no pass / proxy not yet upgraded — local only */ }
  }
  setTimeout(pull, 800);

  window.__sl = { paint, controlsHTML, yahoo, favs, ports, screens,
                  saveScreen, delScreen, delPort, isFav, touch };
})();
