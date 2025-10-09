# 🕶️ Spectacle

Spectacle is an open‑source CLI that builds a **tech‑stack inventory** for GitHub repositories. It reports **languages**, **frameworks**, and **contributors** for each repo using GitHub GraphQL + REST APIs and lightweight manifest scanning.
(This is an AI Generated README but this will essentially extend to become a tool which generates an OpenAPI Spec(hence "Spec"tacle) yaml file for all repositories in an Org additional future feature that im thinking of developing is automated MCP Server Generation for an entire orgs APIs)
(Feel Free to contribute to this really appreciate the help, currently i am pushing shit to the main branch because solo developer i aint doing allat i will start creating feature branches when this repo is decent atleast on its initial use case for my initial setup i will be using the gemini api but will be making that modular eventually)

---

## Features

* Scan an entire **GitHub organization** or a custom **JSON list** of repos
* Detect **frameworks** from manifests (e.g., `package.json`, `requirements.txt`, `go.mod`)
* Summarize **languages** via GitHub Linguist data
* Collect **contributors** per repository (REST + commit history fallback)
* **Parallel** execution with a configurable worker pool
* Modular code and extensible rules in `configs/`

---

## Requirements

* Python 3.9+
* GitHub Personal Access Token with `repo` and `read:org` scopes

```bash
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_yourtokenhere
```

---

## Directory Structure

```
Spectacle/
├── core/
│   ├── github_client.py     # GraphQL/REST helpers
│   ├── contributors.py      # Contributors gathering
│   ├── detection.py         # Framework detection + manifest scan
│   └── __init__.py
├── configs/
│   ├── rules.py             # Language/framework rules
│   └── gql_queries.py       # GraphQL queries
├── inventory.py             # CLI entrypoint
├── requirements.txt
└── USAGE.md                 # Extended usage guide
```

---

## Installation

```bash
git clone https://github.com/<your-username>/spectacle.git
cd spectacle
pip install -r requirements.txt
```

Set your token:

```bash
export GITHUB_TOKEN=ghp_yourtokenhere
```

---

## Quick Start

### Scan an organization

```bash
python inventory.py --org my-org > spectacle_inventory.csv
```

### Scan a curated list (JSON mode)

**Format A — object map**

```json
{
  "octocat/hello-world": "main",
  "octo-org/web-service": "production",
  "openai/openai-cookbook": "master"
}
```

**Format B — array of objects**

```json
[
  { "repo": "octocat/hello-world", "branch": "main" },
  { "repo": "octo-org/web-service", "branch": "staging" },
  { "repo": "openai/openai-cookbook", "branch": "master" }
]
```

Run either format with:

```bash
python inventory.py --repos-json repos.json > spectacle_inventory.csv
```

---

## CLI Options

| Option                | Description                                               | Default  |
| --------------------- | --------------------------------------------------------- | -------- |
| `--org <ORG>`         | GitHub organization name                                  | None     |
| `--repos-json <PATH>` | JSON file listing `repo → branch` or `[ {repo, branch} ]` | None     |
| `--workers <N>`       | Number of threads for concurrent scanning                 | `12`     |
| `--no-progress`       | Disable tqdm progress bar                                 | disabled |

---

## Output

Spectacle writes **CSV** to `stdout`.

Columns:

* `repo` — `owner/repo`
* `name` — repository name
* `url` — GitHub URL
* `branch` — repo branch
* `contributors` — JSON array of usernames
* `languages` — JSON array of `[language, bytes]`
* `frameworks` — JSON array of `[framework, evidence_path]`
* `error` — error message if any

Example:

```csv
repo,name,url,branch,contributors,languages,frameworks,error
octocat/hello-world,hello-world,https://github.com/octocat/hello-world,main,["octocat"],[ ["Go",23102] ],[ ["Fiber","go.mod"] ],
octo-org/web-service,web-service,https://github.com/octo-org/web-service,dev,["alice","bob"],[ ["Python",47834] ],[ ["FastAPI","requirements.txt"] ],
```

---

## Extending Detection Rules

Framework rules live in `configs/rules.py`. Add new entries under a language’s `pkgs` or `markers`, and include the manifest filenames in `TARGET_FILENAMES` if needed.

Example addition:

```python
"python": {
  "files": ["pyproject.toml", "requirements.txt"],
  "pkgs": {
    "flask": "Flask",
    "fastapi": "FastAPI",
    "quart": "Quart"  # new
  }
}
```

---

## Tips

* Lower `--workers` if you encounter rate limits
* Save errors separately: `python inventory.py --org my-org > result.csv 2> errors.log`
* Fine‑grained tokens can increase repository visibility

---

## Contributing

Issues and PRs are welcome. Please open an issue to discuss substantial changes before submitting a PR.

---

## License

MIT License. See `LICENSE` for details.
