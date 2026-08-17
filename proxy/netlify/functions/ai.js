// StockLab AI proxy (v1.15.0).
// Provider API keys live ONLY in Netlify environment variables — never in the
// public site or repo. Every request must carry the StockLab password in the
// x-stocklab-pass header. Ops: {op:"models"}, {op:"chat"}, and — new in
// v1.15.0 — {op:"sync_get"} / {op:"sync_put", data} which keep ONE small JSON
// blob (favorites, portfolios, saved screens, AI conversation) in Netlify
// Blobs so the same state appears on every device that knows the password.
const ORIGINS = ["https://parta1960.github.io", "http://localhost:8777"];
const KEYS = { claude: "CLAUDE_KEY", gemini: "GEMINI_KEY",
               deepseek: "DEEPSEEK_KEY", kimi: "KIMI_KEY" };

const cors = o => ({
  "access-control-allow-origin": ORIGINS.includes(o) ? o : ORIGINS[0],
  "access-control-allow-methods": "POST,OPTIONS",
  "access-control-allow-headers": "content-type,x-stocklab-pass",
});

exports.handler = async (ev) => {
  const H = cors(ev.headers.origin || ev.headers.Origin || "");
  if (ev.httpMethod === "OPTIONS") return { statusCode: 204, headers: H, body: "" };
  if (ev.httpMethod !== "POST") return resp(405, { error: "POST only" }, H);
  const pass = ev.headers["x-stocklab-pass"] || "";
  if (!process.env.STOCKLAB_PASS || pass !== process.env.STOCKLAB_PASS)
    return resp(401, { error: "wrong StockLab password" }, H);
  let b;
  try { b = JSON.parse(ev.body || "{}"); }
  catch { return resp(400, { error: "bad json" }, H); }
  try {
    if (b.op === "sync_get") return resp(200, await syncGet(), H);
    if (b.op === "sync_put") return resp(200, await syncPut(b.data), H);
    const key = process.env[KEYS[b.prov] || ""];
    if (!key) return resp(400, { error: "no key configured for provider: " + b.prov }, H);
    const out = b.op === "models" ? await models(b.prov, key) : await chat(b, key);
    return resp(200, out, H);
  } catch (e) { return resp(502, { error: String(e.message || e) }, H); }
};

// ---- cross-device state sync (v1.15.0) — Netlify Blobs via the REST API.
// NETLIFY_TOKEN + SL_SITE_ID are set as env vars by netlify_deploy.py; the
// blob never leaves Netlify and is only reachable through this
// password-gated function.
const BLOB = () =>
  `https://api.netlify.com/api/v1/blobs/${process.env.SL_SITE_ID}/stocklab/state`;
const BH = () => ({ authorization: "Bearer " + process.env.NETLIFY_TOKEN });

async function syncGet() {
  if (!process.env.NETLIFY_TOKEN || !process.env.SL_SITE_ID)
    throw new Error("sync not configured");
  const r = await fetch(BLOB(), { headers: BH() });
  if (r.status === 404) return { data: null };
  if (!r.ok) throw new Error("blob get HTTP " + r.status);
  return { data: await r.json() };
}

async function syncPut(data) {
  if (!process.env.NETLIFY_TOKEN || !process.env.SL_SITE_ID)
    throw new Error("sync not configured");
  const body = JSON.stringify(data || {});
  if (body.length > 900000) throw new Error("state too large");
  const r = await fetch(BLOB(), { method: "PUT",
    headers: { ...BH(), "content-type": "application/json" }, body });
  if (!r.ok) throw new Error("blob put HTTP " + r.status);
  return { ok: true };
}

function resp(s, obj, H) {
  return { statusCode: s, body: JSON.stringify(obj),
           headers: { ...H, "content-type": "application/json" } };
}

async function jfetch(url, opt) {
  const r = await fetch(url, opt);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(
    (j.error && (j.error.message || j.error)) || ("HTTP " + r.status));
  return j;
}

async function models(prov, key) {
  if (prov === "claude") {
    const j = await jfetch("https://api.anthropic.com/v1/models?limit=100",
      { headers: { "x-api-key": key, "anthropic-version": "2023-06-01" } });
    return { models: (j.data || []).map(m => m.id) };
  }
  if (prov === "gemini") {
    const j = await jfetch("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key=" + key);
    return { models: (j.models || [])
      .filter(m => (m.supportedGenerationMethods || []).includes("generateContent"))
      .map(m => (m.name || "").replace("models/", ""))
      .filter(n => !/embed|aqa|imagen|veo|tts|audio|image|live/.test(n)) };
  }
  const base = prov === "deepseek" ? "https://api.deepseek.com"
                                   : "https://api.moonshot.ai/v1";
  const j = await jfetch(base + "/models",
    { headers: { authorization: "Bearer " + key } });
  return { models: (j.data || []).map(m => m.id) };
}

async function chat(b, key) {
  const msgs = b.messages || [];
  if (b.prov === "claude") {
    const j = await jfetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "content-type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01" },
      body: JSON.stringify({ model: b.model, max_tokens: 1500,
                             system: b.system, messages: msgs }) });
    return { text: (j.content || []).map(c => c.text || "").join("") };
  }
  if (b.prov === "gemini") {
    const j = await jfetch(
      "https://generativelanguage.googleapis.com/v1beta/models/" +
      encodeURIComponent(b.model) + ":generateContent?key=" + key, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: b.system }] },
        contents: msgs.map(m => ({
          role: m.role === "assistant" ? "model" : "user",
          parts: [{ text: m.content }] })) }) });
    const parts = (j.candidates && j.candidates[0] &&
                   j.candidates[0].content && j.candidates[0].content.parts) || [];
    return { text: parts.map(p => p.text || "").join("") };
  }
  const base = b.prov === "deepseek" ? "https://api.deepseek.com"
                                     : "https://api.moonshot.ai/v1";
  const j = await jfetch(base + "/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json",
               authorization: "Bearer " + key },
    body: JSON.stringify({ model: b.model, max_tokens: 1500, messages:
      [{ role: "system", content: b.system }, ...msgs] }) });
  return { text: (j.choices && j.choices[0] &&
                  j.choices[0].message && j.choices[0].message.content) || "" };
}
