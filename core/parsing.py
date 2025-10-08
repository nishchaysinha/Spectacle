import re
_PEP503 = re.compile(r"[^a-z0-9]+")

def norm_pkg(s: str) -> str:
    return _PEP503.sub("-", s.strip().lower())

def parse_requirements(txt: str):
    pkgs=set()
    for line in txt.splitlines():
        line=line.strip()
        if not line or line.startswith("#"): continue
        line=line.split(" ; ")[0].split(";")[0]
        line=line.split(" --hash=")[0]
        line=line.split(" #")[0]
        for sep in ["==",">=","<=","~=","!=","==="," >",">","<"]:
            if sep in line: line=line.split(sep,1)[0]; break
        if "[" in line and "]" in line: line=line.split("[",1)[0]
        if line: pkgs.add(norm_pkg(line))
    return pkgs
