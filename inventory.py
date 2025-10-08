#!/usr/bin/env python3
import sys, json, argparse, csv, concurrent.futures as fx
from configs.rules import RULES, TARGET_FILENAMES
from configs.gql_queries import REPO_LIST_Q, REPO_SUMMARY_Q, HEAD_Q, BLOB_Q, CONTRIB_HISTORY_Q
from core.github_client import iter_repos, repo_summary
from core.contributors import get_contributors
from core.detection import detect_frameworks

def load_repos_from_json(path):
    """
    Accepts either:
      - dict: { "owner/name": "branch", ... }
      - list: [{ "repo": "owner/name", "branch": "prod" }, ...]
    Returns: [{owner, name, branch}]
    """
    with open(path, "r") as f:
        data = json.load(f)
    out = []
    if isinstance(data, dict):
        for full, br in data.items():
            if "/" not in full: continue
            owner, name = full.split("/", 1)
            out.append({"owner": owner, "name": name, "branch": br})
    elif isinstance(data, list):
        for item in data:
            full = item.get("repo", "")
            br = item.get("branch", None)
            if "/" not in full: continue
            owner, name = full.split("/", 1)
            out.append({"owner": owner, "name": name, "branch": br})
    return out

def process_repo(r):
    owner, name = r["owner"], r["name"]
    branch_override = r.get("branch")
    try:
        meta = repo_summary(owner, name, REPO_SUMMARY_Q)
        if not meta:
            return None
        try:
            contributors = get_contributors(owner, name, CONTRIB_HISTORY_Q)
        except Exception:
            contributors = []
        frameworks = detect_frameworks(
            owner, name,
            meta["branch"],               # summary branch
            RULES, TARGET_FILENAMES,
            HEAD_Q, BLOB_Q,
            branch_override=branch_override  # override if provided
        )
        return {
            "repo": f"{owner}/{name}",
            "name": meta["name"],
            "url": meta["url"],
            "contributors": json.dumps(contributors, separators=(",",":")),
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
    ap.add_argument("--org", default="SuperSecretSecretOrganization", help="GitHub org")
    ap.add_argument("--repos-json", help="Path to JSON mapping of repos to branches")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    if args.repos_json:
        repos = load_repos_from_json(args.repos_json)
    else:
        repos = list(iter_repos(args.org, REPO_LIST_Q))

    writer = csv.DictWriter(sys.stdout, fieldnames=[
        "repo","name","url","contributors","languages","frameworks","error"
    ])
    writer.writeheader()

    with fx.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(process_repo, repos, chunksize=5):
            if row:
                writer.writerow(row)

if __name__ == "__main__":
    main()
