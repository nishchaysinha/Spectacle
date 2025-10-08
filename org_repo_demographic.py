#!/usr/bin/env python3
# org_repo_demographic.py
# Usage:
#   export GITHUB_TOKEN=ghp_xxx
#   python org_repo_demographic.py > inventory.csv
# Optional:
#   python org_repo_demographic.py --org your-org --workers 12

import os, sys, json, time, argparse, csv, concurrent.futures as fx, requests

GH = "https://api.github.com/graphql"
TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    print("GITHUB_TOKEN env var required", file=sys.stderr); sys.exit(1)

S = requests.Session()
S.headers.update({"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})

# ---- Detection rules ----
RULES = {
    "javascript": {
        "files": ["package.json"],
        "pkgs": {
            "express": "Express", "next": "Next.js", "nestjs": "NestJS", "nuxt": "Nuxt",
            "angular": "Angular", "@angular/core": "Angular", "sveltekit": "SvelteKit",
            "koa": "Koa", "hapi": "hapi", "remix": "Remix", "fastify": "Fastify"
        }
    },
    "python": {
        "files": ["pyproject.toml", "requirements.txt"],
        "pkgs": {"django": "Django", "flask": "Flask", "fastapi": "FastAPI",
                 "starlette": "Starlette", "tornado": "Tornado"}
    },
    "java": {
        "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "markers": {"spring-boot-starter": "Spring Boot", "spring-framework": "Spring",
                    "quarkus-": "Quarkus", "io.micronaut": "Micronaut"}
    },
    "ruby":   {"files": ["Gemfile"], "pkgs": {"rails": "Rails", "sinatra": "Sinatra"}},
    "php":    {"files": ["composer.json"], "pkgs": {"laravel/framework": "Laravel",
                                                    "symfony/framework-bundle": "Symfony",
                                                    "codeigniter4/framework": "CodeIgniter"}},
    "go":     {"files": ["go.mod"], "markers": {"github.com/gin-gonic/gin": "Gin",
                                                "github.com/labstack/echo": "Echo",
                                                "github.com/gofiber/fiber": "Fiber"}},
    "rust":   {"files": ["Cargo.toml"], "pkgs": {"actix-web": "Actix", "rocket": "Rocket", "axum": "Axum"}}
}
MANIFESTS = sorted({f for v in RULES.values() for f in v["files"]})

# ---- GraphQL ----
def gql(query, variables=None, retries=5):
    for i in range(retries):
        r = S.post(GH, json={"query": query, "variables": variables or {}}, timeout=60)
        if r.status_code == 200:
            data = r.json()
            if "errors" in data:
                if any("rate limit" in str(e).lower() for e in data["errors"]) and i < retries-1:
                    time.sleep(30); continue
                raise RuntimeError(str(data["errors"]))
            return data["data"]
        if r.status_code in (502,503,504) and i < retries-1:
            time.sleep(3*(i+1)); continue
        if r.status_code == 403 and "rate limit" in r.text.lower() and i < retries-1:
            time.sleep(60); continue
        r.raise_for_status()

REPO_LIST_Q = """
query($login:String!, $after:String){
  repositoryOwner(login:$login){
    repositories(first:100, after:$after, orderBy:{field:NAME, direction:ASC}){
      pageInfo{ hasNextPage endCursor }
      nodes{ name owner{login} nameWithOwner isArchived }
    }
  }
}
"""

REPO_SUMMARY_Q = """
query($owner:String!, $name:String!){
  repository(owner:$owner, name:$name){
    name
    url
    isArchived
    defaultBranchRef{ name }
    languages(first:20, orderBy:{field:SIZE, direction:DESC}){
      edges{ size node{ name } }
    }
    collaborators(first:50){
      nodes{ login }
    }
  }
}
"""

BLOB_Q = """
query($owner:String!, $name:String!, $expr:String!){
  repository(owner:$owner, name:$name){
    object(expression:$expr){ ... on Blob { text byteSize isBinary } }
  }
}
"""

def iter_repos(org):
    after = None
    while True:
        d = gql(REPO_LIST_Q, {"login": org, "after": after})
        nodes = d["repositoryOwner"]["repositories"]["nodes"]
        for n in nodes:
            yield {"owner": n["owner"]["login"], "name": n["name"]}
        pi = d["repositoryOwner"]["repositories"]["pageInfo"]
        if not pi["hasNextPage"]: break
        after = pi["endCursor"]

def repo_summary(owner, name):
    d = gql(REPO_SUMMARY_Q, {"owner": owner, "name": name})["repository"]
    if not d: return None
    langs_map = {e["node"]["name"]: e["size"] for e in (d["languages"]["edges"] or [])}
    languages = [[k, v] for k, v in sorted(langs_map.items(), key=lambda x: -x[1])]
    branch = d["defaultBranchRef"]["name"] if d["defaultBranchRef"] else "HEAD"
    contributors = []
    try:
        contributors = [n["login"] for n in (d.get("collaborators") or {}).get("nodes", []) if n.get("login")]
    except Exception:
        contributors = []
    return {
        "name": d["name"],
        "url": d["url"],
        "archived": d["isArchived"],
        "branch": branch,
        "languages": languages,
        "contributors": contributors
    }

def try_blob(owner, name, branch, path):
    d = gql(BLOB_Q, {"owner": owner, "name": name, "expr": f"{branch}:{path}"})
    obj = d["repository"]["object"]
    if not obj or obj.get("isBinary"): return None
    return obj.get("text") or ""

# ---- Framework detection (returns [(framework, evidence_file)]) ----
def detect_frameworks(owner, name, branch):
    evidence = {}
    for f in MANIFESTS:
        txt = try_blob(owner, name, branch, f)
        if txt: evidence[f] = txt

    found = []

    # JS/TS
    pj = evidence.get("package.json")
    if pj:
        try:
            pj_json = json.loads(pj)
            deps = set((pj_json.get("dependencies") or {}).keys()) | set((pj_json.get("devDependencies") or {}).keys())
            low = {d.lower() for d in deps}
        except Exception:
            low = set()
        for k, label in RULES["javascript"]["pkgs"].items():
            if k in low:
                found.append([label, "package.json"])

    # Python
    pblob = (evidence.get("pyproject.toml","") + "\n" + evidence.get("requirements.txt","")).lower()
    if pblob:
        for k, label in RULES["python"]["pkgs"].items():
            if k in pblob:
                # prefer specific file naming for evidence
                ev = "pyproject.toml" if k in (evidence.get("pyproject.toml","").lower()) else "requirements.txt"
                found.append([label, ev])

    # Java
    for f in ["pom.xml","build.gradle","build.gradle.kts"]:
        if f in evidence:
            low = evidence[f].lower()
            for k, label in RULES["java"]["markers"].items():
                if k in low:
                    found.append([label, f])

    # Ruby
    gf = evidence.get("Gemfile","").lower()
    if gf:
        for k, label in RULES["ruby"]["pkgs"].items():
            if f"gem '{k}'" in gf or f'gem "{k}"' in gf or f"gem {k}" in gf:
                found.append([label, "Gemfile"])

    # PHP
    comp = evidence.get("composer.json")
    if comp:
        try:
            reqs = set((json.loads(comp).get("require") or {}).keys())
        except Exception:
            reqs = set()
        for k, label in RULES["php"]["pkgs"].items():
            if k in reqs:
                found.append([label, "composer.json"])

    # Go
    gomod = evidence.get("go.mod","").lower()
    if gomod:
        for k, label in RULES["go"]["markers"].items():
            if k in gomod:
                found.append([label, "go.mod"])

    # Rust
    cargo = evidence.get("Cargo.toml","").lower()
    if cargo:
        for k, label in RULES["rust"]["pkgs"].items():
            if f'"{k}"' in cargo or f"{k} =" in cargo:
                found.append([label, "Cargo.toml"])

    # dedupe by (framework, evidence_file)
    seen = set()
    uniq = []
    for fw, ev in found:
        key = (fw, ev)
        if key not in seen:
            uniq.append([fw, ev])
            seen.add(key)
    return uniq

def process_repo(r):
    owner, name = r["owner"], r["name"]
    try:
        meta = repo_summary(owner, name)
        if not meta: return None
        frameworks = detect_frameworks(owner, name, meta["branch"])
        return {
            "repo": f"{owner}/{name}",
            "name": meta["name"],
            "url": meta["url"],
            "contributors": json.dumps(meta["contributors"], separators=(",",":")),
            "languages": json.dumps(meta["languages"], separators=(",",":")),
            "frameworks": json.dumps(frameworks, separators=(",",":")),
            "error": ""
        }
    except Exception as e:
        return {
            "repo": f"{owner}/{name}",
            "name": "",
            "url": f"https://github.com/{owner}/{name}",
            "contributors": "[]",
            "languages": "[]",
            "frameworks": "[]",
            "error": str(e)
        }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default="SuperSecretSecretOrg", help="GitHub org (default: SuperSecretSecretOrg)")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    repos = list(iter_repos(org=args.org))

    writer = csv.DictWriter(sys.stdout, fieldnames=[
        "repo","name","url","contributors","languages","frameworks","error"
    ])
    writer.writeheader()

    with fx.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(process_repo, repos, chunksize=5):
            if row: writer.writerow(row)

if __name__ == "__main__":
    main()
