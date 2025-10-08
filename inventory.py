#!/usr/bin/env python3
import sys, json, argparse, csv, concurrent.futures as fx
from tqdm.auto import tqdm

from configs.rules import RULES, TARGET_FILENAMES
from configs.gql_queries import REPO_LIST_Q, REPO_SUMMARY_Q, HEAD_Q, BLOB_Q, CONTRIB_HISTORY_Q
from core.github_client import iter_repos, repo_summary
from core.contributors import get_contributors
from core.detection import detect_frameworks

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
            meta["branch"],
            RULES, TARGET_FILENAMES,
            HEAD_Q, BLOB_Q,
            branch_override=branch_override
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

def load_repos_from_json(path):
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default="SuperSecretSecretOrganization", help="GitHub org")
    ap.add_argument("--repos-json", help="Path to JSON mapping of repos to branches")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--no-progress", action="store_true", help="Disable tqdm progress bar")
    args = ap.parse_args()

    # Collect repos (show a tiny spinner-like bar only if --repos-json not used)
    if args.repos_json:
        repos = load_repos_from_json(args.repos_json)
    else:
        repos = list(iter_repos(args.org, REPO_LIST_Q))

    writer = csv.DictWriter(sys.stdout, fieldnames=[
        "repo","name","url","contributors","languages","frameworks","error"
    ])
    writer.writeheader()

    errors = 0
    disable_pbar = args.no_progress or not sys.stderr.isatty()

    with fx.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(process_repo, r) for r in repos]
        with tqdm(total=len(futures), desc="Scanning repos", unit="repo", disable=disable_pbar) as pbar:
            for fut in fx.as_completed(futures):
                row = fut.result()
                if row:
                    if row.get("error"):
                        errors += 1
                    writer.writerow(row)
                pbar.update(1)
                if not disable_pbar:
                    pbar.set_postfix_str(f"errors={errors}")

if __name__ == "__main__":
    main()
