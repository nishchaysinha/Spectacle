import time
from core.github_client import REST, S, gql

def get_contributors(owner: str, name: str, history_query) -> list:
    logins = set(); page = 1
    while True:
        url = f"{REST}/repos/{owner}/{name}/contributors"
        r = S.get(url, params={"per_page": 100, "page": page, "anon": "1"}, timeout=60)
        if r.status_code in (404, 401):
            break
        if r.status_code == 403 and "rate limit" in (r.text or "").lower():
            time.sleep(30); continue
        if r.status_code not in (200, 204):
            break
        arr = r.json() or []
        if not arr:
            break
        for u in arr:
            login = u.get("login")
            if login: logins.add(login)
        if 'rel="next"' not in (r.headers.get("Link") or ""):
            break
        page += 1
    if logins:
        return sorted(logins)

    after = None
    while True:
        d = gql(history_query, {"owner": owner, "name": name, "after": after})
        repo = d["repository"]
        if not repo or not repo["defaultBranchRef"] or not repo["defaultBranchRef"]["target"]:
            break
        hist = repo["defaultBranchRef"]["target"]["history"]
        for n in hist["nodes"]:
            au = n.get("author") or {}
            user = (au.get("user") or {}).get("login")
            if user: logins.add(user)
        if not hist["pageInfo"]["hasNextPage"]:
            break
        after = hist["pageInfo"]["endCursor"]
        if len(logins) > 500:
            break
    return sorted(logins)
