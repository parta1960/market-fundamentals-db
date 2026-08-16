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
  #slMenu .mi { display:block; width:100%; text-align:left; background:none;
    border:none; border-bottom:1px solid #21262d; color:#e6edf3;
    padding:11px 14px; font-size:13.5px; cursor:pointer;
    text-decoration:none; box-sizing:border-box; }
  #slMenu .mi:hover { background:#1c2128; }
  #slMenu .mhead { padding:10px 14px; color:#6e7681; font-size:11.5px;
    border-bottom:1px solid #21262d; }
  #slMenu .danger { color:#ffb3ad; }`;
  const st = document.createElement("style"); st.textContent = css;
  document.head.appendChild(st);

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
    <button class="mi" id="slAiSetup">🤖 AI setup — password &amp; API keys</button>
    <button class="mi" id="slShare">🔗 Share this view (copy link)</button>
    <a class="mi" href="index.html">📋 Screener</a>
    <a class="mi" href="charts.html">📈 History Charts</a>
    <a class="mi" target="_blank" rel="noopener"
       href="https://github.com/parta1960/market-fundamentals-db/blob/main/CHANGELOG.md">📜 Changelog (what's new)</a>
    <a class="mi" target="_blank" rel="noopener"
       href="https://github.com/parta1960/market-fundamentals-db">🧪 Methodology &amp; source data</a>
    <button class="mi danger" id="slAiReset">🧹 Reset AI settings on this device</button>`;
  document.body.appendChild(menu);
  const $ = id => document.getElementById(id);

  btn.onclick = () => {
    menu.classList.toggle("open");
    if (menu.classList.contains("open")) fillInfo();
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
    const b = $("slShare");
    try {
      if (navigator.share) { await navigator.share({ title: document.title, url }); return; }
      await navigator.clipboard.writeText(url);
      b.textContent = "✓ Link copied to clipboard";
    } catch (e) {
      prompt("Copy this link:", url);
    }
    setTimeout(() => { b.textContent = "🔗 Share this view (copy link)"; }, 2200);
  };

  $("slAiReset").onclick = () => {
    const b = $("slAiReset");
    if (b.dataset.arm !== "1") {
      b.dataset.arm = "1";
      b.textContent = "⚠ Click again to forget password & keys here";
      setTimeout(() => { b.dataset.arm = "0";
        b.textContent = "🧹 Reset AI settings on this device"; }, 4000);
      return;
    }
    ["mfdb_ai_keys", "mfdb_ai_prov", "mfdb_ai_models",
     "mfdb_ai_model_choice", "mfdb_ai_pass"].forEach(k => localStorage.removeItem(k));
    b.dataset.arm = "0";
    b.textContent = "✓ Cleared — reload the page";
    setTimeout(() => { b.textContent = "🧹 Reset AI settings on this device"; }, 2500);
  };
})();
