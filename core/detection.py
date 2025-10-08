import json, re
from core.parsing import norm_pkg, parse_requirements
from core.github_client import get_head, get_branch_oid, list_tree_paths, try_blob

def detect_frameworks(owner, name, branch_from_summary, rules, target_filenames, q_head, q_blob, branch_override=None):
    # Choose branch + tree OID
    branch = branch_override or branch_from_summary or "HEAD"
    oid = None
    if branch_override:
        oid = get_branch_oid(owner, name, branch_override)
    if not oid:
        # default branch fallback via GraphQL
        _, oid = get_head(owner, name, q_head)

    evidence = {}
    if oid:
        paths = list_tree_paths(owner, name, oid, target_filenames)
        for p in paths:
            txt = try_blob(owner, name, branch, p, q_blob)
            if txt:
                evidence[p] = txt
    else:
        for mf in target_filenames:
            txt = try_blob(owner, name, branch, mf, q_blob)
            if txt:
                evidence[mf] = txt

    pairs = []

    # JS/TS
    for path, txt in evidence.items():
        if path.endswith("package.json"):
            try:
                pj = json.loads(txt)
                deps = set((pj.get("dependencies") or {}).keys()) | set((pj.get("devDependencies") or {}).keys())
                low = {norm_pkg(d) for d in deps}
            except Exception:
                low = set()
            for k, label in rules["javascript"]["pkgs"].items():
                if norm_pkg(k) in low:
                    pairs.append([label, path])

    # Python by dir
    by_dir = {}
    for path, txt in evidence.items():
        root = path.rsplit("/",1)[0] if "/" in path else ""
        by_dir.setdefault(root, {}).update({path.rsplit("/",1)[-1]: txt})
    for root, files in by_dir.items():
        names=set()
        if "pyproject.toml" in files:
            names |= {norm_pkg(x) for x in re.findall(
                r'(?m)^\s*["\']?([A-Za-z0-9_.-]+)["\']?\s*(?:[=><!~]=|,|\]|#|$)', files["pyproject.toml"]
            )}
        if "requirements.txt" in files:
            names |= parse_requirements(files["requirements.txt"])
        for k, label in rules["python"]["pkgs"].items():
            if norm_pkg(k) in names:
                ev = "pyproject.toml" if "pyproject.toml" in files else ("requirements.txt" if "requirements.txt" in files else "")
                ev_path = f"{root}/{ev}" if root and ev else (ev or root or "")
                pairs.append([label, ev_path or (root or "deps")])

    # Java
    for path, txt in evidence.items():
        if path.endswith(("pom.xml","build.gradle","build.gradle.kts")):
            low = txt.lower()
            for k, label in rules["java"]["markers"].items():
                if k in low:
                    pairs.append([label, path])

    # Ruby
    for path, txt in evidence.items():
        if path.endswith("Gemfile"):
            low = txt.lower()
            for k, label in rules["ruby"]["pkgs"].items():
                if re.search(rf"\bgem\s+['\"]{re.escape(k)}['\"]", low):
                    pairs.append([label, path])

    # PHP
    for path, txt in evidence.items():
        if path.endswith("composer.json"):
            try:
                reqs = set((json.loads(txt).get("require") or {}).keys())
            except Exception:
                reqs = set()
            for k, label in rules["php"]["pkgs"].items():
                if k in reqs:
                    pairs.append([label, path])

    # Go
    for path, txt in evidence.items():
        if path.endswith("go.mod"):
            low = txt.lower()
            for k, label in rules["go"]["markers"].items():
                if k in low:
                    pairs.append([label, path])

    # Rust
    for path, txt in evidence.items():
        if path.endswith("Cargo.toml"):
            low = txt.lower()
            for k, label in rules["rust"]["pkgs"].items():
                if re.search(rf'\b{re.escape(k)}\b\s*=', low) or f'"{k}"' in low:
                    pairs.append([label, path])

    seen=set(); uniq=[]
    for fw, ev in pairs:
        key=(fw, ev)
        if key not in seen:
            uniq.append([fw, ev]); seen.add(key)
    return uniq
