"""StockLab v1.6.0 — deploy the AI proxy to Netlify (stdlib only, run on PC).

Reads:
  ~/.mfdb/netlify_token.txt         Netlify personal access token (one line)
  ~/.mfdb/ai_provider_keys.json     {"CLAUDE_KEY":..., "GEMINI_KEY":...,
                                     "DEEPSEEK_KEY":..., "KIMI_KEY":...,
                                     "STOCKLAB_PASS":...}
  ~/.mfdb/proxy/ai.js               the function source
  ~/.mfdb/proxy/index.html          placeholder page

Does: find-or-create site SITE_NAME, upsert env vars, digest-deploy the file +
function, wait until the deploy is ready, then smoke-test the endpoint.
"""
import hashlib
import io
import json
import os
import time
import urllib.request
import zipfile

SITE_NAME = "stocklab-ai-proxy"
API = "https://api.netlify.com/api/v1"
MF = os.path.expanduser("~/.mfdb")
TOKEN = open(os.path.join(MF, "netlify_token.txt")).read().strip()
SECRETS = json.load(open(os.path.join(MF, "ai_provider_keys.json")))


def call(method, path, body=None, ctype="application/json", raw=False):
    url = path if path.startswith("http") else API + path
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
    rq = urllib.request.Request(url, data=data, method=method)
    rq.add_header("Authorization", "Bearer " + TOKEN)
    if body is not None:
        rq.add_header("Content-Type", ctype)
    with urllib.request.urlopen(rq, timeout=120) as r:
        txt = r.read()
        return txt if raw else (json.loads(txt) if txt else {})


def main():
    # 1) site
    sites = call("GET", "/sites?name=" + SITE_NAME)
    site = next((s for s in sites if s["name"] == SITE_NAME), None)
    if site is None:
        site = call("POST", "/sites", {"name": SITE_NAME})
        print("created site", site["name"])
    sid = site["id"]
    print("site:", site["ssl_url"] or site["url"])

    # 2) env vars (upsert)
    acct = site["account_slug"]
    for k, v in SECRETS.items():
        body = [{"key": k, "scopes": ["functions"],
                 "values": [{"value": v, "context": "all"}]}]
        try:
            call("POST", f"/accounts/{acct}/env?site_id={sid}", body)
            print("env set:", k)
        except urllib.error.HTTPError as e:
            if e.code in (409, 422):
                call("PUT", f"/accounts/{acct}/env/{k}?site_id={sid}",
                     {"key": k, "scopes": ["functions"],
                      "values": [{"value": v, "context": "all"}]})
                print("env updated:", k)
            else:
                raise

    # 3) digest deploy: 1 file + 1 function
    html = open(os.path.join(MF, "proxy", "index.html"), "rb").read()
    fsha = hashlib.sha1(html).hexdigest()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(MF, "proxy", "ai.js"), "ai.js")
    zbytes = buf.getvalue()
    zsha = hashlib.sha256(zbytes).hexdigest()
    dep = call("POST", f"/sites/{sid}/deploys",
               {"files": {"/index.html": fsha}, "functions": {"ai": zsha}})
    did = dep["id"]
    call("PUT", f"/deploys/{did}/files/index.html", html,
         ctype="application/octet-stream")
    call("PUT", f"/deploys/{did}/functions/ai?runtime=js", zbytes,
         ctype="application/octet-stream")
    for _ in range(60):
        st = call("GET", f"/deploys/{did}")
        if st["state"] == "ready":
            break
        if st["state"] == "error":
            raise SystemExit("deploy failed: " + json.dumps(st)[:400])
        time.sleep(3)
    print("deploy state:", st["state"])

    # 4) smoke test: wrong password must 401; right password must list models
    base = (site["ssl_url"] or site["url"]).rstrip("/")
    ep = base + "/.netlify/functions/ai"
    def hit(pass_, body):
        rq = urllib.request.Request(ep, data=json.dumps(body).encode(),
                                    method="POST")
        rq.add_header("Content-Type", "application/json")
        rq.add_header("x-stocklab-pass", pass_)
        try:
            with urllib.request.urlopen(rq, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    print("bad-pass check:", hit("wrong", {"prov": "claude", "op": "models"})[0])
    for prov in ("claude", "gemini", "deepseek", "kimi"):
        code, j = hit(SECRETS["STOCKLAB_PASS"], {"prov": prov, "op": "models"})
        tops = (j.get("models") or [])[:3]
        print(f"{prov}: HTTP {code} models[:3]={tops} err={j.get('error')}")
    print("ENDPOINT:", ep)


if __name__ == "__main__":
    main()
