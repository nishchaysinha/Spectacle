#!/usr/bin/env python3
# repo_to_openapi.py
# CLI: clone <repo>@<branch> → tree → Gemini pick files → Gemini generate OpenAPI → openapi.yaml

import argparse, os, re, shutil, subprocess, sys, tempfile, textwrap, json
from pathlib import Path
from typing import List, Tuple

# --- Config via env ---
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MAX_BYTES = int(os.getenv("MAX_BYTES", 1_500_000))  # cap combined file content
TREE_ARGS = os.getenv("TREE_ARGS", "-a -I .git")

# --- Gemini client (new SDK) ---
try:
    from google import genai
    from google.genai import types as gx
except Exception as e:
    print("Install google-genai: pip install google-genai", file=sys.stderr)
    raise

def run(cmd: List[str], cwd: Path | None = None, timeout: int = 600) -> str:
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nSTDERR:\n{p.stderr}")
    return p.stdout

def ensure_bin(name: str):
    if shutil.which(name) is None:
        raise RuntimeError(f"Required binary not found: {name}")

def clone_repo(repo: str, branch: str, workdir: Path) -> Path:
    ensure_bin("git")
    dest = workdir / "repo"
    run(["git", "clone", "--depth", "1", "--branch", branch, repo, str(dest)])
    return dest

def tree_repr(repo_dir: Path) -> str:
    # Prefer `tree` for exact request; fallback to python if missing.
    if shutil.which("tree"):
        out = run(["tree", *TREE_ARGS.split(), "."], cwd=repo_dir)
    else:
        lines = []
        for p in sorted(repo_dir.rglob("*")):
            if ".git" in p.parts: 
                continue
            rel = p.relative_to(repo_dir)
            indent = "    " * (len(rel.parts)-1)
            lines.append(f"{indent}{rel.name}{'/' if p.is_dir() else ''}")
        out = ".\n" + "\n".join(lines)
    return out

def gemini_client() -> genai.Client:
    if not GOOGLE_API_KEY:
        raise RuntimeError("Set GOOGLE_API_KEY env var.")
    return genai.Client(api_key=GOOGLE_API_KEY)

def pick_candidate_files(client: genai.Client, repo_dir: Path, tree_text: str) -> List[str]:
    sys_prompt = (
        "You select source files that define HTTP APIs suitable for OpenAPI generation.\n"
        "Return a JSON array of relative filepaths. Do not include comments or prose."
    )
    user_prompt = f"""Repository tree:
```

{tree_text}

```

Rules:
- Only return a JSON array. Example: ["src/api/users.ts","app/routes.py"]
- Prefer files with routes/controllers/handlers, request/response models, middleware, server config.
- Include framework-specific files (Express/FastAPI/Flask/Django/Spring/ASP.NET/NestJS/Laravel/Gin/etc.).
- Exclude binaries, images, lockfiles, node_modules, build artifacts.
- Relative to repo root.
"""
    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=[sys_prompt, user_prompt],
        config=gx.GenerateContentConfig(temperature=0.1, max_output_tokens=2048)
    )
    text = resp.text.strip()
    # Extract JSON array robustly
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        # fallback: try to guess common paths
        patterns = ["route", "routes", "router", "controller", "api", "endpoint", "handler", "view", "server"]
        candidates = []
        for p in repo_dir.rglob("*"):
            if p.is_file() and not any(seg.startswith(".git") for seg in p.parts):
                name = p.name.lower()
                if any(k in name for k in patterns):
                    candidates.append(str(p.relative_to(repo_dir)))
        return sorted(set(candidates))[:200]
    try:
        arr = json.loads(m.group(0))
        if not isinstance(arr, list):
            raise ValueError
        # normalize and keep files that exist
        out = []
        for rel in arr:
            try:
                pr = (repo_dir / rel).resolve()
                if pr.is_file() and repo_dir in pr.parents:
                    out.append(str(pr.relative_to(repo_dir)))
            except Exception:
                continue
        return sorted(set(out))
    except Exception:
        return []

def read_files_bounded(repo_dir: Path, files: List[str], max_bytes: int) -> Tuple[str, List[str]]:
    buf = []
    used = 0
    used_files = []
    for rel in files:
        p = (repo_dir / rel).resolve()
        if not p.is_file() or repo_dir not in p.parents:
            continue
        try:
            data = p.read_bytes()
            if used + len(data) > max_bytes:
                # try partial chunk if small file exceeded slightly? skip to keep structure clean.
                continue
            text = ""
            try:
                text = data.decode("utf-8", errors="replace")
            except Exception:
                continue
            buf.append(f"{rel}\n{text}\n")
            used += len(data)
            used_files.append(rel)
        except Exception:
            continue
    return "".join(buf), used_files

def generate_openapi(client: genai.Client, file_bundle: str) -> str:
    sys_prompt = (
        "You are an API specification generator. Produce a valid OpenAPI 3.1 YAML for the given codebase. "
        "Infer paths, methods, parameters, request bodies, responses, and component schemas from the code. "
        "If unsure, mark TODO but keep spec valid."
    )
    user_prompt = textwrap.dedent(f"""
    Return only YAML. No backticks. No commentary.

    Requirements:
    - openapi: 3.1.0
    - info: title and version required
    - paths: include endpoints detected with summaries and operationIds
    - components.schemas: define reusable objects you infer
    - Use types that match code where possible
    - If base URL is unknown, omit servers or set a placeholder variable

    Source files and contents follow. Each file is prefixed by its relative path on one line, then full contents.

    {file_bundle}
    """).strip()
    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=[sys_prompt, user_prompt],
        config=gx.GenerateContentConfig(temperature=0.1, max_output_tokens=8192)
    )
    return resp.text.strip()

def main():
    ap = argparse.ArgumentParser(description="Generate OpenAPI spec from a repo branch using Gemini.")
    ap.add_argument("--repo", required=True, help="Git repo URL (https or ssh)")
    ap.add_argument("--branch", required=True, help="Git branch")
    ap.add_argument("--out", default="openapi.yaml", help="Output OpenAPI file")
    ap.add_argument("--max-bytes", type=int, default=MAX_BYTES, help="Max bytes of code to send in second prompt")
    args = ap.parse_args()

    client = gemini_client()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        repo_dir = clone_repo(args.repo, args.branch, td)

        print("Building tree...", file=sys.stderr)
        tree_text = tree_repr(repo_dir)

        print("Selecting candidate files via Gemini...", file=sys.stderr)
        candidates = pick_candidate_files(client, repo_dir, tree_text)
        if not candidates:
            print("No candidates from Gemini. Exiting.", file=sys.stderr)
            sys.exit(2)

        print(f"Reading {len(candidates)} files (bounded to {args.max_bytes} bytes)...", file=sys.stderr)
        bundle, used_files = read_files_bounded(repo_dir, candidates, args.max_bytes)
        if not used_files:
            print("No files included within byte budget. Increase --max-bytes.", file=sys.stderr)
            sys.exit(3)

        print(f"Generating OpenAPI from {len(used_files)} files...", file=sys.stderr)
        yaml_text = generate_openapi(client, bundle)

        # Minimal sanity: must contain 'openapi:' and 'paths:'
        if "openapi:" not in yaml_text or "\npaths:" not in yaml_text:
            print("Model output does not look like OpenAPI YAML. Writing anyway.", file=sys.stderr)

        Path(args.out).write_text(yaml_text, encoding="utf-8")
        print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
