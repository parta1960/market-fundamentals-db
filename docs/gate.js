/* StockLab site password gate (v1.23.0).
 *
 * Client-side gate: every page loads this first; until the correct password is
 * entered it shows an opaque overlay. On success a flag is stored so the gate
 * stays unlocked on this device. The password is the StockLab password (the
 * same one used for the AI); only its SHA-256 hash is embedded here (one-way,
 * safe to expose — brute-forcing a 15-char random password is infeasible).
 *
 * NOTE: this is LIGHT protection appropriate for public market data — it hides
 * the pages from casual visitors, but the content still lives in the page
 * source, so it is not cryptographically private. For true privacy the pages
 * would need to be encrypted (StatiCrypt-style). */
(() => {
  const HASH = "9fa2e853d2c9592e104ba318a6cecd0e853312fded7b7227458efda3a23650d2";
  const KEY = "sl_gate_ok";
  function authed() { try { return localStorage.getItem(KEY) === HASH; } catch (e) { return false; } }
  if (authed()) return;

  const ov = document.createElement("div");
  ov.id = "slGate";
  ov.style.cssText = "position:fixed;inset:0;z-index:99999;background:#0d1117;" +
    "display:flex;align-items:center;justify-content:center;" +
    "font:14px -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e6edf3";
  ov.innerHTML =
    '<div style="text-align:center;width:300px;max-width:86vw">' +
      '<div style="font-size:22px;font-weight:600;margin-bottom:2px">📈 StockLab</div>' +
      '<div style="color:#9aa4b2;font-size:12.5px;margin-bottom:16px">Enter the password to continue</div>' +
      '<input id="slGatePw" type="password" placeholder="Password" autocomplete="current-password" ' +
        'style="width:100%;padding:10px 12px;border-radius:8px;border:1px solid #30363d;' +
        'background:#161b22;color:#e6edf3;font-size:14px;box-sizing:border-box">' +
      '<div id="slGateErr" style="color:#f85149;font-size:12px;height:16px;margin:7px 0"></div>' +
      '<button id="slGateBtn" style="width:100%;padding:10px;border-radius:8px;border:none;' +
        'background:#1f6feb;color:#fff;font-weight:600;font-size:14px;cursor:pointer">Enter</button>' +
    '</div>';

  async function sha256(s) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
    return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
  }

  function mount() {
    (document.body || document.documentElement).appendChild(ov);
    const pw = ov.querySelector("#slGatePw");
    const btn = ov.querySelector("#slGateBtn");
    const err = ov.querySelector("#slGateErr");
    async function submit() {
      let h = "";
      try { h = await sha256(pw.value); } catch (e) { err.textContent = "Secure context required (use https)."; return; }
      if (h === HASH) {
        try { localStorage.setItem(KEY, HASH); } catch (e) {}
        ov.remove();
      } else {
        err.textContent = "Incorrect password";
        pw.value = ""; pw.focus();
      }
    }
    btn.onclick = submit;
    pw.addEventListener("keydown", e => { if (e.key === "Enter") submit(); });
    setTimeout(() => pw.focus(), 30);
  }
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
