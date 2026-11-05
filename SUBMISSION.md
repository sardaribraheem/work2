# Hackathon Task 4 — Track B Submission

## Selected track

**Track B: GitHub Repository Analyzer CLI** (40 marks). Track A is not part of this submission.

## Working source

- [analyze.py](analyze.py) — GitHub REST API client, metadata and file-tree retrieval, dependency analysis, complexity scoring, activity chart and terminal output
- [test_analyzer.py](test_analyzer.py) — automated edge-case and dependency-parser tests
- [README.md](README.md) — usage, methods, formula, assumptions and limitations
- [.github/workflows/verify.yml](.github/workflows/verify.yml) — automated tests, real API-based demos, commits reports back to repository

## Demo 1: Requests

Input URL: https://github.com/psf/requests

Full terminal report: [demos/requests.txt](demos/requests.txt)

Full structured JSON: [demos/requests.json](demos/requests.json)

## Demo 2: Flask

Input URL: https://github.com/pallets/flask

Full terminal report: [demos/flask.txt](demos/flask.txt)

Full structured JSON: [demos/flask.json](demos/flask.json)

## Verification

The workflow executes `python -m unittest -v test_analyzer`, followed by the exact CLI commands used for both demonstrations, on an Ubuntu runner with Python 3.11. The reports are created by the running program from live GitHub API responses and committed back as evidence. A failing test stops the pipeline before report generation.

Testing includes valid and invalid repository URL forms, empty repositories, manifest-free projects, npm dependency parsing, PEP 621 `pyproject.toml` parsing, and simulated API rate-limit errors.

The initial demonstration runs exposed a flaw: `pyproject.toml` was recognized but its direct dependencies were not parsed. The parser was extended, the first regression-test fixture had an escaped-newline bug, the raw CI logs were inspected, and the fixture was fixed. The subsequent GitHub Actions run succeeded and regenerated the demo reports. This is genuine iteration and review evidence.

## Security and limitations

- Public repositories only; no repo-specific hardcoded analysis.
- Optional `GITHUB_TOKEN` is read from an environment variable; not committed.
- Code complexity is an explicitly defined **structural proxy**, not cyclomatic complexity.
- Dependency health is version constraint/reproducibility analysis, **not** live CVE or outdated-release checking.
- File-tree truncation, missing manifests, absent languages and incomplete activity must be disclosed rather than guessed.
- Contribution chart covers at most 300 fetched recent commits.
- Scores and counts are tied to the selected repositories at execution time and can change.

## Mandatory remaining evidence: original AI chats

The rubric also requires **the complete, unedited AI conversation export**. Export the actual ChatGPT discussion used to build this tool, as PDF, Markdown or text. Do not generate a recreated conversation or omit failed steps. Place that export beside this repository when submitting to the organizers.

Suggested final submission:

1. GitHub repository URL: https://github.com/sardaribraheem/work2
2. Full unedited ChatGPT conversation export (attached separately)
3. Demo reports and JSON from `demos/` (or links to these repo files)
4. README and this submission index
