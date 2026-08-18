/* StockLab menu (v1.7.0) — ☰ settings/utilities button on every page.
 * Items: AI setup (opens the assistant's password/key rows), share the
 * current view, page links, version + data-freshness info, and a reset for
 * AI settings saved on this device. */
(() => {
  const css = `
  #slMenuBtn { background:#21262d; color:#e6edf3; border:1px solid #30363d;
    border-radius:8px; padding:7px 12px; font-size:13.5px; font-weight:600;
    cursor:pointer; white-space:nowrap; }
  #slMenuBtn.fallback { position:fixed; left:12px; top:10px; z-index:75; }
  #slMenu { position:fixed; left:12px; top:56px; z-index:75; width:270px;
    background:#161b22; border:1px solid #30363d; border-radius:10px;
    box-shadow:0 8px 28px rgba(0,0,0,.6); display:none; overflow:hidden;
    font-size:13.5px; }
  #slMenu.open { display:block; }
  #slMenu .mi { display:flex; align-items:center; gap:11px; width:100%;
    text-align:left; background:none;
    border:none; border-bottom:1px solid #21262d; color:#e6edf3;
    padding:11px 14px; font-size:13.5px; cursor:pointer;
    text-decoration:none; box-sizing:border-box; }
  #slMenu .mi:hover { background:#1c2128; }
  #slMenu .mi svg { flex:none; color:#9aa4b2; }
  #slMenu .mi:hover svg { color:#e6edf3; }
  #slMenu .danger, #slMenu .danger svg { color:#ffb3ad; }
  #slMenu .mcount { color:#6e7681; }
  #slMenu .mdel { margin-left:auto; color:#6e7681; cursor:pointer;
    padding:0 2px; font-size:12px; }
  #slMenu .mdel:hover { color:#f85149; }
  #slMenu .mhead { padding:10px 14px; color:#6e7681; font-size:11.5px;
    border-bottom:1px solid #21262d; }`;
  const st = document.createElement("style"); st.textContent = css;
  document.head.appendChild(st);

  // v1.16.1 — one consistent, minimalist icon set (stroke-only inline SVG,
  // single weight and size) instead of mixed emoji that render differently
  // on every OS.
  const ic = d => `<svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="1.7" stroke-linecap="round"
    stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const IC = {
    key: ic('<path d="M21 2l-2 2m-7.6 7.6a5.5 5.5 0 1 1-7.8 7.8 5.5 5.5 0 0 1 7.8-7.8zm0 0L15.5 7.5m3 3L22 7l-3-3"/>'),
    share: ic('<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>'),
    list: ic('<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>'),
    chart: ic('<path d="M23 6l-9.5 9.5-5-5L1 18"/><path d="M17 6h6v6"/>'),
    rank: ic('<path d="M18 20V10M12 20V4M6 20v-6"/>'),
    star: ic('<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/>'),
    grid: ic('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>'),
    save: ic('<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>'),
    doc: ic('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>'),
    book: ic('<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'),
    trash: ic('<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>'),
  };

  const btn = document.createElement("button");
  btn.id = "slMenuBtn"; btn.textContent = "☰ Menu";
  // v1.8.0: lives at the TOP LEFT, inside the fixed bar's menu slot
  const slot = document.getElementById("slMenuSlot");
  if (slot) slot.appendChild(btn);
  else { btn.classList.add("fallback"); document.body.appendChild(btn); }
  // narrow screens: icon-only label so the bar fits on phones (v1.8.1)
  const mqM = matchMedia("(max-width: 820px)");
  const setLbl = () => { btn.textContent = mqM.matches ? "☰" : "☰ Menu"; };
  setLbl();
  if (mqM.addEventListener) mqM.addEventListener("change", setLbl);

  const ver = typeof STOCKLAB_VERSION !== "undefined" ? STOCKLAB_VERSION : "";
  const menu = document.createElement("div");
  menu.id = "slMenu";
  menu.innerHTML = `
    <div class="mhead" id="slMenuInfo">StockLab ${ver}</div>
    <button class="mi" id="slAiSetup">${IC.key}AI setup — password &amp; API keys</button>
    <button class="mi" id="slShare">${IC.share}Share this view (copy link)</button>
    <a class="mi" href="index.html">${IC.rank}Rankings (home)</a>
    <a class="mi" href="screener.html">${IC.list}Stock List</a>
    <a class="mi" href="charts.html">${IC.chart}History Charts</a>
    <div id="slMenuDyn"></div>
    <a class="mi" target="_blank" rel="noopener"
       href="https://github.com/parta1960/market-fundamentals-db/blob/main/CHANGELOG.md">${IC.doc}Changelog (what's new)</a>
    <a class="mi" target="_blank" rel="noopener"
       href="https://github.com/parta1960/market-fundamentals-db">${IC.book}Methodology &amp; source data</a>
    <button class="mi danger" id="slAiReset">${IC.trash}Reset AI settings on this device</button>`;
  document.body.appendChild(menu);
  const $ = id => document.getElementById(id);

  // v1.15.0: favorites, portfolios and saved screens — rebuilt on every open
  function fillDyn() {
    const dyn = $("slMenuDyn");
    if (!window.__sl) { dyn.innerHTML = ""; return; }
    const favN = window.__sl.favs().length;
    const ports = window.__sl.ports(), screens = window.__sl.screens();
    // v1.17.3: Favorites / portfolios open a clean LIST VIEW (the stock-list
    // page in list mode — just the stocks, none of the screening clutter).
    // v1.18.0: that page moved to screener.html (index.html = Rankings now).
    let h = `<a class="mi" href="screener.html?list=fav">${IC.star}Favorites` +
            ` <span class="mcount">(${favN})</span></a>`;
    for (const n of Object.keys(ports).sort())
      h += `<a class="mi" href="screener.html?port=${encodeURIComponent(n)}">${IC.grid}${n}` +
           ` <span class="mcount">(${ports[n].length})</span>` +
           `<span class="mdel" data-kind="port" data-n="${n}" title="delete this portfolio">✕</span></a>`;
    for (const n of Object.keys(screens).sort())
      h += `<a class="mi" href="screener.html?screen=${encodeURIComponent(n)}">${IC.save}${n}` +
           `<span class="mdel" data-kind="screen" data-n="${n}" title="delete this saved screen">✕</span></a>`;
    dyn.innerHTML = h;
    dyn.querySelectorAll(".mdel").forEach(x => x.onclick = e => {
      e.preventDefault(); e.stopPropagation();
      if (!confirm(`Delete ${x.dataset.kind === "port" ? "portfolio" : "saved screen"} "${x.dataset.n}"?`)) return;
      x.dataset.kind === "port" ? window.__sl.delPort(x.dataset.n)
                                : window.__sl.delScreen(x.dataset.n);
      fillDyn();
    });
  }

  btn.onclick = () => {
    menu.classList.toggle("open");
    if (menu.classList.contains("open")) { fillInfo(); fillDyn(); }
  };
  document.addEventListener("click", e => {
    if (!menu.contains(e.target) && e.target !== btn)
      menu.classList.remove("open");
  });

  let asOf = null;
  async function fillInfo() {
    if (asOf === null) {
      try {
        const r = await fetch("data/history/manifest.json");
        asOf = (await r.json()).as_of || "";
      } catch (e) { asOf = ""; }
    }
    $("slMenuInfo").textContent = "StockLab " + ver +
      (asOf ? " · data through " + asOf : "");
  }

  $("slAiSetup").onclick = () => {
    menu.classList.remove("open");
    if (window.__ai) window.__ai.setup();
    else alert("AI assistant is still loading — try again in a second.");
  };

  $("slShare").onclick = async () => {
    const url = location.href;
    const b = $("slShare"), orig = b.innerHTML;
    try {
      if (navigator.share) { await navigator.share({ title: document.title, url }); return; }
      await navigator.clipboard.writeText(url);
      b.textContent = "✓ Link copied to clipboard";
    } catch (e) {
      prompt("Copy this link:", url);
    }
    setTimeout(() => { b.innerHTML = orig; }, 2200);   // restores icon + label
  };

  const resetOrig = $("slAiReset").innerHTML;
  $("slAiReset").onclick = () => {
    const b = $("slAiReset");
    if (b.dataset.arm !== "1") {
      b.dataset.arm = "1";
      b.textContent = "⚠ Click again to forget password & keys here";
      setTimeout(() => { b.dataset.arm = "0"; b.innerHTML = resetOrig; }, 4000);
      return;
    }
    ["mfdb_ai_keys", "mfdb_ai_prov", "mfdb_ai_models",
     "mfdb_ai_model_choice", "mfdb_ai_pass", "mfdb_ai_hist"].forEach(k => localStorage.removeItem(k));
    b.dataset.arm = "0";
    b.textContent = "✓ Cleared — reload the page";
    setTimeout(() => { b.innerHTML = resetOrig; }, 2500);
  };
})();
