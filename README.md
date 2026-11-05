# GitHub Repository Analyzer CLI

**AI Hackathon — Task 4, Track B (40 marks)**

A command-line tool that uses the public GitHub REST API to produce a verifiable terminal report for **any public GitHub repository**. Includes live demo evidence from two different public repositories, automated tests, and clear disclosures where data is incomplete.

## Start here

**Requirements:** Python 3.11+ and internet access. External libraries: **none** (Python standard library only).

```bash
git clone https://github.com/sardaribraheem/work2.git
cd work2

python -m unittest -v test_analyzer
python analyze.py https://github.com/psf/requests
python analyze.py https://github.com/pallets/flask --json flask-output.json
```

The `--json` flag writes the full analyzed data as JSON; the human-readable report always prints to the terminal.

**Optional GitHub token:** Requests run without a token, but unauthenticated GitHub API rate limits are stricter. To raise the limit, set `GITHUB_TOKEN` in your own environment. Do **not** put it in source code, chats, commits or screenshots.

```bash
# macOS / Linux
export GITHUB_TOKEN="YOUR_TOKEN"
# PowerShell:
# $env:GITHUB_TOKEN="YOUR_TOKEN"
```

The tool automatically reads `GITHUB_TOKEN` from the environment and does not print it.

## Architecture: five separate stages

| Stage | Input | Output | Validation |
|---|---|---|---|
| 1. Parse | Public GitHub URL | Owner and repository | HTTPS GitHub hostname; exactly two path segments |
| 2. Fetch | Repository identity | Metadata, default-branch tree, selected manifests, recent commits, contributors | HTTP errors converted to plain messages |
| 3. Analyze | API responses | Language counts, folder distribution, framework evidence, parsed dependencies, structural score, commit counts | Explicitly label unknowns or truncated data |
| 4. Render | Computed metrics | Five-part terminal report and optional JSON | Formula and evidence shown in output |
| 5. Verify | Test cases and two public repositories | Unit-test output and live demo report files | GitHub Actions regenerates real evidence |

### Report sections

1. **Tech stack** — detected programming languages by source extension and recognized frameworks by dependency manifest evidence. Counts are **files**, not bytes.
2. **File structure** — file count, extension distribution and main top-level directories. Directory **purposes are not inferred** from names alone.
3. **Code complexity** — one reproducible **structural complexity proxy**, not actual cyclomatic complexity:
   ```text
   min(30, files / 20)
   + min(20, maximum path depth * 4)
   + min(20, recognized languages * 5)
   + min(30, parsed dependencies / 2)
   ```
   Range 0–100; larger scores indicate larger, deeper and more varied structure. Not a quality or defect score.
4. **Dependency health** — actual direct declarations in supported manifests. Flags broad or unpinned versions as **reproducibility risks**. It does **not** query current package versions, vulnerabilities or maintainer activity, so those properties remain unknown. Recognizes `requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pubspec.yaml`, `composer.json`, and `Gemfile`. Some forms of dependency declarations are outside the parser's supported syntax.
5. **Contribution activity** — recent commits grouped by month using the API, plus major contributors. The chart reflects up to 300 **retrieved recent** commits, not automatically the whole history.

## Live demonstration evidence

The GitHub Actions workflow [verify.yml](.github/workflows/verify.yml) runs the Python tests, invokes the **real CLI with live GitHub API requests**, and commits the unedited output and JSON analysis. The data is not invented.

| Public repository | Terminal report | JSON output |
|---|---|---|
| [Python Requests](https://github.com/psf/requests) | [demos/requests.txt](demos/requests.txt) | [demos/requests.json](demos/requests.json) |
| [Flask](https://github.com/pallets/flask) | [demos/flask.txt](demos/flask.txt) | [demos/flask.json](demos/flask.json) |

**Note:** These reports are point-in-time snapshots. They can change when code, dependencies or contributions change.

## Failure handling / robustness

| Case | Behavior |
|---|---|
| Invalid URL or nested GitHub URL | Clear error and nonzero exit |
| Repository not found / inaccessible | Clear HTTP 404 explanation |
| GitHub API rate limit (403/429) | Clear message to use a token or retry |
| No dependency manifest | Report says health cannot be determined |
| Tree truncated by GitHub | Report labels file analysis as incomplete |
| No recognized source language | Report says none recognized |
| No commits or contributors returned | Report indicates unavailable results |
| Very large or unreadable dependency manifest | Skipped instead of crashing; output may be incomplete |

To run tests: `python -m unittest -v test_analyzer`.

## AI development process and submission

1. Planned distinct stages and the five required sections from the task specification.
2. Built a working Python CLI using the standard library and GitHub API.
3. Added unit tests and live two-repository demonstration workflow.
4. Reviewed first live outputs and identified incomplete `pyproject.toml` dependency extraction; extended parser and tests, then regenerated demos.
5. Documented what the computed scores **do and do not establish**.

### Deliverables

- **Source:** `analyze.py`
- **Tests:** `test_analyzer.py`
- **README:** this file
- **Live reports:** `demos/requests.txt`, `demos/flask.txt` and JSON counterparts
- **Complete unedited AI chat export:** export the **actual conversation in ChatGPT** as PDF/text; not reconstructable from repository code. Add it to your final hackathon submission without altering messages.

**Selected track: B — GitHub Repository Analyzer CLI.** Track A is intentionally not implemented.
