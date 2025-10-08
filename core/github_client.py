import os, sys, time, requests

GH = "https://api.github.com/graphql"
REST = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    print("GITHUB_TOKEN env var required", file=sys.stderr); sys.exit(1)

S = requests.Session()
S.headers.update({"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})

def gql(query, variables=None, retries=5):
    for i in range(retries):
        r = S.post(GH, json={"query": query, "variables": variables or {}}, timeout=60)
        if r.status_code == 200:
            data = r.json()
            if "errors" in data:
                msg = str(data["errors"])
                if "rate limit" in msg.lower() and i < retries-1:
                    time.sleep(30); continue
                raise RuntimeError(msg)
            return data["data"]
        if r.status_code in (502,503,504) and i < retries-1:
            time.sleep(3*(i+1)); continue
        if r.status_code == 403 and "rate limit" in (r.text or "").lower() and i < retries-1:
            time.sleep(60); continue
        r.raise_for_status()

def iter_repos(org, repo_list_query):
    after = None
    while True:
        d = gql(repo_list_query, {"login": org, "after": after})
        nodes = d["repositoryOwner"]["repositories"]["nodes"]
        for n in nodes:
            yield {"owner": n["owner"]["login"], "name": n["name"]}
        pi = d["repositoryOwner"]["repositories"]["pageInfo"]
        if not pi["hasNextPage"]: break
        after = pi["endCursor"]

def repo_summary(owner, name, summary_query):
    d = gql(summary_query, {"owner": owner, "name": name})["repository"]
    if not d: return None
    langs_map = {e["node"]["name"]: e["size"] for e in (d["languages"]["edges"] or [])}
    languages = [[k, v] for k, v in sorted(langs_map.items(), key=lambda x: -x[1])]
    branch = d["defaultBranchRef"]["name"] if d["defaultBranchRef"] else "HEAD"
    return {"name": d["name"], "url": d["url"], "archived": d["isArchived"], "branch": branch, "languages": languages}

def get_head(owner, name, head_query):
    d = gql(head_query, {"owner": owner, "name": name})["repository"]
    if not d or not d["defaultBranchRef"]:
        return "HEAD", None
    return d["defaultBranchRef"]["name"], d["defaultBranchRef"]["target"]["oid"]

def get_branch_oid(owner, name, branch):
    """REST: branch -> commit oid (sha). Returns None if missing."""
    url = f"{REST}/repos/{owner}/{name}/branches/{branch}"
    r = S.get(url, timeout=60)
    if r.status_code != 200:
        return None
    try:
        return (r.json().get("commit") or {}).get("sha")
    except Exception:
        return None

def list_tree_paths(owner, name, tree_oid, target_filenames):
    url = f"{REST}/repos/{owner}/{name}/git/trees/{tree_oid}"
    r = S.get(url, params={"recursive": "1"}, timeout=60)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    items = r.json().get("tree", []) or []
    out = []
    for it in items:
        if it.get("type") != "blob": continue
        p = it.get("path","")
        base = p.rsplit("/",1)[-1]
        if base in target_filenames:
            out.append(p)
    return out

def try_blob(owner, name, branch, path, blob_query):
    d = gql(blob_query, {"owner": owner, "name": name, "expr": f"{branch}:{path}"})
    obj = d["repository"]["object"]
    if not obj or obj.get("isBinary"): return None
    return obj.get("text") or ""
