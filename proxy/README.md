# StockLab AI proxy (v1.6.0)

Password-gated Netlify Function that lets the public StockLab site use the
maintainer's AI provider accounts WITHOUT exposing any API key.

- `netlify/functions/ai.js` — the function. Two ops, both POST with header
  `x-stocklab-pass`: `{prov, op:"models"}` → `{models:[...]}` and
  `{prov, op:"chat", model, system, messages}` → `{text}`.
  Providers: claude, gemini, deepseek, kimi. CORS-locked to the Pages site.
- Keys + the StockLab password live ONLY in Netlify env vars
  (`CLAUDE_KEY`, `GEMINI_KEY`, `DEEPSEEK_KEY`, `KIMI_KEY`, `STOCKLAB_PASS`)
  — never in this repo (the repo is public).
- `netlify_deploy.py` — stdlib deployer run on the maintainer PC. Reads
  `~/.mfdb/netlify_token.txt` and `~/.mfdb/ai_provider_keys.json`; creates
  the `stocklab-ai-proxy` site, upserts env vars, digest-deploys, smoke-tests.
- Live endpoint: `https://stocklab-ai-proxy.netlify.app/.netlify/functions/ai`.
  `docs/chat.js` uses it whenever a StockLab password is saved in the browser
  (localStorage `mfdb_ai_pass`); per-provider BYOK keys remain the fallback.

To rotate a provider key or the password: edit `~/.mfdb/ai_provider_keys.json`
on the PC and rerun `python ~/.mfdb/proxy/netlify_deploy.py`.
