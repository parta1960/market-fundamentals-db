/* StockLab auto-update checker (v1.26.0).
 *
 * GitHub Pages is static — there's no server push to a running tab. This
 * polls the tiny version.js file itself (cache-busted) on an interval and
 * whenever the tab regains focus, and compares the embedded
 * STOCKLAB_VERSION string against the one this page loaded with. If the
 * deployed site has moved on, it shows a one-click "reload" banner instead
 * of silently leaving the visitor on stale code/data.
 */
(() => {
  const CURRENT = typeof STOCKLAB_VERSION !== "undefined" ? STOCKLAB_VERSION : "";
  const POLL_MS = 5 * 60 * 1000;        // recheck every 5 min while the tab is open
  const MIN_GAP_MS = 60 * 1000;         // never recheck more than once a minute
  const BASE_PAD = "56px";              // matches the top bar padding set by chat.js
  const SHOWN_PAD = "100px";
  const DISMISS_KEY = "sl_upd_dismissed";

  let lastCheck = 0, shown = false, latest = "";

  const css = `
  #slUpdBar { position:fixed; top:56px; left:0; right:0; z-index:71;
    display:none; align-items:center; gap:10px; justify-content:center;
    flex-wrap:wrap; padding:9px 14px; background:#1f6feb; color:#fff;
    font-size:13px; font-weight:600; box-shadow:0 2px 10px rgba(0,0,0,.35); }
  #slUpdBar.show { display:flex; }
  #slUpdBar button { border:none; border-radius:6px; padding:6px 12px;
    font-size:12.5px; font-weight:700; cursor:pointer; }
  #slUpdReload { background:#fff; color:#1f6feb; }
  #slUpdReload:hover { background:#e6edf3; }
  #slUpdDismiss { background:transparent; color:#fff; font-weight:500;
    text-decoration:underline; padding:6px 4px; }
  @media (max-width: 560px) { #slUpdBar { font-size:12px; } }`;
  const st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);

  const bar = document.createElement("div");
  bar.id = "slUpdBar";
  bar.innerHTML = `<span id="slUpdMsg"></span>
    <button id="slUpdReload">Reload now</button>
    <button id="slUpdDismiss">later</button>`;
  document.body.appendChild(bar);

  function dismissedVersion() {
    try { return sessionStorage.getItem(DISMISS_KEY) || ""; } catch (e) { return ""; }
  }
  function remember(v) {
    try { sessionStorage.setItem(DISMISS_KEY, v); } catch (e) { /* ignore */ }
  }

  function showBar(v) {
    latest = v;
    if (shown) {
      document.getElementById("slUpdMsg").textContent =
        `StockLab ${v} is available (you're on ${CURRENT}).`;
      return;
    }
    shown = true;
    document.getElementById("slUpdMsg").textContent =
      `StockLab ${v} is available (you're on ${CURRENT}).`;
    bar.classList.add("show");
    document.body.style.paddingTop = SHOWN_PAD;
  }

  document.getElementById("slUpdReload").onclick = () => location.reload();
  document.getElementById("slUpdDismiss").onclick = () => {
    remember(latest);
    shown = false;
    bar.classList.remove("show");
    document.body.style.paddingTop = BASE_PAD;
  };

  async function check() {
    const now = Date.now();
    if (now - lastCheck < MIN_GAP_MS) return;
    lastCheck = now;
    try {
      const r = await fetch("version.js?_=" + now, { cache: "no-store" });
      if (!r.ok) return;
      const txt = await r.text();
      const m = txt.match(/STOCKLAB_VERSION\s*=\s*"([^"]+)"/);
      if (!m) return;
      const v = m[1];
      if (!v || v === CURRENT) return;
      if (v === dismissedVersion()) return;   // the visitor already said "later" for this one
      showBar(v);
    } catch (e) { /* offline, blocked, or a transient fetch failure — try again next cycle */ }
  }

  if (CURRENT) {
    setTimeout(check, 15000);   // small delay so this never competes with first paint
    setInterval(check, POLL_MS);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") check();
    });
  }
})();
