"""GitHub uploader — commits a local staging tree to a repo via the REST API.

Runs on any machine with Python 3.8+ (stdlib only; no git required).
The token is read from ~/.mfdb/token.txt (never passed on the command line).

Usage:
  python gh_push.py push <staging_dir> "<commit message>" [--branch main]
  python gh_push.py dispatch <workflow_filename> [key=value ...]
  python gh_push.py runs [n]
  python gh_push.py watch [run_id]

`push` mirrors every file under <staging_dir> into the repo at the same
relative path (Git Data API: blobs -> tree -> commit -> ref update), so a
single commit can carry any number of files of any size (<100 MB each).
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

REPO = "parta1960/market-fundamentals-db"
API = "https://api.github.com"


def token():
    path = os.path.join(os.path.expanduser("~"), ".mfdb", "token.txt")
    with open(path) as f:
        return f.read().strip()


def api(method, path, data=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={"Authorization": "Bearer " + token(),
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "mfdb-uploader"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise SystemExit(f"GitHub API {e.code} on {method} {path}: {detail}")


def push(staging_dir, message, branch="main"):
    ref = api("GET", f"/repos/{REPO}/git/ref/heads/{branch}")
    base_commit_sha = ref["object"]["sha"]
    base_commit = api("GET", f"/repos/{REPO}/git/commits/{base_commit_sha}")

    entries = []
    for root, _, files in os.walk(staging_dir):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, staging_dir).replace(os.sep, "/")
            with open(full, "rb") as f:
                raw = f.read()
            raw = raw.replace(b"\r\n", b"\n")  # normalize Windows line endings
            blob = api("POST", f"/repos/{REPO}/git/blobs",
                       {"content": base64.b64encode(raw).decode(),
                        "encoding": "base64"})
            entries.append({"path": rel, "mode": "100644", "type": "blob",
                            "sha": blob["sha"]})
            print(f"  blob {rel} ({len(raw):,} bytes)")

    if not entries:
        raise SystemExit("staging dir is empty")
    tree = api("POST", f"/repos/{REPO}/git/trees",
               {"base_tree": base_commit["tree"]["sha"], "tree": entries})
    commit = api("POST", f"/repos/{REPO}/git/commits",
                 {"message": message, "tree": tree["sha"],
                  "parents": [base_commit_sha]})
    api("PATCH", f"/repos/{REPO}/git/refs/heads/{branch}",
        {"sha": commit["sha"]})
    print(f"pushed {len(entries)} files -> {commit['sha'][:10]} on {branch}")
    return commit["sha"]


def dispatch(workflow, *pairs):
    inputs = dict(p.split("=", 1) for p in pairs)
    api("POST", f"/repos/{REPO}/actions/workflows/{workflow}/dispatches",
        {"ref": "main", "inputs": inputs} if inputs
        else {"ref": "main"})
    print(f"dispatched {workflow} inputs={inputs}")


def runs(n=5):
    data = api("GET", f"/repos/{REPO}/actions/runs?per_page={n}")
    for r in data.get("workflow_runs", []):
        print(f"{r['id']}  {r['name'][:30]:30}  {r['status']:12} "
              f"{str(r['conclusion']):10}  {r['created_at']}")
    return data.get("workflow_runs", [])


def watch(run_id=None, interval=60):
    if run_id is None:
        rs = api("GET", f"/repos/{REPO}/actions/runs?per_page=1")["workflow_runs"]
        if not rs:
            raise SystemExit("no runs found")
        run_id = rs[0]["id"]
    while True:
        r = api("GET", f"/repos/{REPO}/actions/runs/{run_id}")
        print(f"{time.strftime('%H:%M:%S')}  {r['status']}  {r['conclusion']}")
        if r["status"] == "completed":
            print(r["html_url"])
            return r["conclusion"]
        time.sleep(interval)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "runs"
    if cmd == "push":
        branch = "main"
        args = sys.argv[2:]
        if "--branch" in args:
            i = args.index("--branch")
            branch = args[i + 1]
            args = args[:i] + args[i + 2:]
        push(args[0], args[1], branch)
    elif cmd == "dispatch":
        dispatch(*sys.argv[2:])
    elif cmd == "watch":
        watch(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        runs(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
