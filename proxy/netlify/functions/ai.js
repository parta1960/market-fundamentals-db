// StockLab AI proxy (v1.6.0).
// Provider API keys live ONLY in Netlify environment variables — never in the
// public site or repo. Every request must carry the StockLab password in the
// x-stocklab-pass header. Serves two ops: {op:"models"} and {op:"chat"}.
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
  const key = process.env[KEYS[b.prov] || ""];
  if (!key) return resp(400, { error: "no key configured for provider: " + b.prov }, H);
  try {
    const out = b.op === "models" ? await models(b.prov, key) : await chat(b, key);
    return resp(200, out, H);
  } catch (e) { return resp(502, { error: String(e.message || e) }, H); }
};

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
