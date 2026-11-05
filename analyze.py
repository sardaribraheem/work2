"""GitHub Repository Analyzer — Task 4 Track B.

Uses GitHub's public REST API. No third-party dependencies.
"""
import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
MANIFESTS = {"requirements.txt", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "Gemfile", "composer.json", "pubspec.yaml"}
SKIP = {"node_modules", "vendor", ".git", "dist", "build", "__pycache__"}
EXTENSIONS = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".dart": "Dart", ".go": "Go", ".rs": "Rust", ".java": "Java", ".cpp": "C++", ".c": "C", ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".html": "HTML", ".css": "CSS", ".ipynb": "Jupyter Notebook", ".swift": "Swift", ".kt": "Kotlin"}
FRAMEWORKS = {"next": "Next.js", "react": "React", "vue": "Vue", "angular": "Angular", "express": "Express", "django": "Django", "flask": "Flask", "fastapi": "FastAPI", "flutter": "Flutter", "firebase": "Firebase", "pytest": "pytest", "vite": "Vite", "tailwindcss": "Tailwind CSS"}
class AnalyzerError(Exception):
    pass

def parse_repo(url):
    p = urllib.parse.urlsplit(url.strip())
    if p.scheme != "https" or p.hostname not in {"github.com", "www.github.com"} or p.username or p.password or p.port:
        raise AnalyzerError("Invalid URL: expected https://github.com/owner/repository")
    parts = [x for x in p.path.strip("/").split("/") if x]
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in parts):
        raise AnalyzerError("Invalid URL: provide a repository URL, not a file or profile URL")
    owner, name = parts
    name = re.sub(r"\.git$", "", name)
    if not name or name in {".", ".."}:
        raise AnalyzerError("Invalid repository name")
    return owner, name

def request(path, token=None, params=None):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "hackathon-repo-analyzer", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise AnalyzerError("Repository or resource not found (404), or access denied") from exc
        if exc.code in (403, 429):
            raise AnalyzerError("GitHub API rate limit or access restriction (HTTP %s). Try GITHUB_TOKEN or retry later." % exc.code) from exc
        raise AnalyzerError("GitHub API returned HTTP %s" % exc.code) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise AnalyzerError("Network/API response error: %s" % exc) from exc

def fetch(repo_url, token=None):
    owner, name = parse_repo(repo_url)
    root = "/repos/%s/%s" % (owner, name)
    metadata = request(root, token)
    if metadata.get("private"):
        raise AnalyzerError("Only public repositories are supported")
    branch = metadata.get("default_branch")
    if not branch:
        raise AnalyzerError("Repository has no default branch")
    commit = request(root + "/commits/" + urllib.parse.quote(branch, safe=""), token)
    tree = request(root + "/git/trees/" + commit["commit"]["tree"]["sha"], token, {"recursive": 1})
    files = [x for x in tree.get("tree", []) if x.get("type") == "blob" and not any(part in SKIP for part in x["path"].split("/"))]
    manifests = {}
    for item in files:
        path = item["path"]
        if path.rsplit("/", 1)[-1] in MANIFESTS and item.get("size", 0) <= 150000 and len(manifests) < 25:
            try:
                import base64
                raw = request(root + "/contents/" + urllib.parse.quote(path, safe="/"), token, {"ref": branch})
                if raw.get("encoding") == "base64":
                    manifests[path] = base64.b64decode(raw["content"]).decode("utf-8", "replace")
            except AnalyzerError:
                manifests[path] = None
    # GitHub's contributors endpoint may be unavailable for some repositories.
    try:
        contributors = request(root + "/contributors", token, {"per_page": 10})
    except AnalyzerError:
        contributors = []
    commits = []
    for page in range(1, 4):
        try:
            batch = request(root + "/commits", token, {"per_page": 100, "page": page})
        except AnalyzerError:
            break
        if not isinstance(batch, list) or not batch:
            break
        commits.extend(batch)
        if len(batch) < 100:
            break
    return {"metadata": metadata, "files": files, "tree_truncated": bool(tree.get("truncated")), "manifests": manifests, "contributors": contributors, "commits": commits, "commit_sample_limit": 300}

def dependencies(manifests):
    """Parse direct dependencies from common formats; never claim full coverage."""
    found = []
    for path, content in manifests.items():
        if content is None:
            continue
        filename = path.rsplit("/", 1)[-1]
        if filename == "package.json":
            try:
                obj = json.loads(content)
                for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
                    for name, version in obj.get(section, {}).items():
                        found.append((path, name, str(version)))
            except (ValueError, AttributeError):
                pass
        elif filename == "requirements.txt":
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith(("-", "git+", "http")):
                    match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*(.*)$", line)
                    if match:
                        found.append((path, match.group(1), match.group(2).split("#")[0].strip() or "unconstrained"))
        elif filename in ("pyproject.toml", "Cargo.toml"):
            try:
                import tomllib
                obj = tomllib.loads(content)
                if filename == "pyproject.toml":
                    for spec in obj.get("project", {}).get("dependencies", []):
                        match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*(.*)$", spec)
                        if match:
                            found.append((path, match.group(1), match.group(2).strip() or "unconstrained"))
                    for group, specs in obj.get("project", {}).get("optional-dependencies", {}).items():
                        for spec in specs:
                            match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*(.*)$", spec)
                            if match:
                                found.append((path, match.group(1), match.group(2).strip() or "unconstrained"))
                    for name, constraint in obj.get("tool", {}).get("poetry", {}).get("dependencies", {}).items():
                        if name.lower() != "python":
                            found.append((path, name, str(constraint)))
                else:
                    for group in ("dependencies", "dev-dependencies", "build-dependencies"):
                        for name, spec in obj.get(group, {}).items():
                            version = spec if isinstance(spec, str) else spec.get("version", "Not specified")
                            found.append((path, name, str(version)))
            except (ImportError, ValueError, TypeError, AttributeError):
                pass
        elif filename == "pubspec.yaml":
            section = None
            for line in content.splitlines():
                if line in ("dependencies:", "dev_dependencies:"):
                    section = line
                elif line and not line.startswith((" ", "#")):
                    section = None
                elif section:
                    m = re.match(r"^  ([A-Za-z0-9_]+):\s*(.*)$", line)
                    if m and m.group(1) != "flutter":
                        found.append((path, m.group(1), m.group(2) or "nested specification"))
        elif filename == "go.mod":
            for line in content.splitlines():
                m = re.match(r"^\s*([\w.-]+\.[\w./-]+)\s+(v\S+)", line)
                if m:
                    found.append((path, m.group(1), m.group(2)))
        elif filename == "composer.json":
            try:
                obj = json.loads(content)
                for group in ("require", "require-dev"):
                    for name, constraint in obj.get(group, {}).items():
                        found.append((path, name, str(constraint)))
            except (ValueError, AttributeError):
                pass
        elif filename == "Gemfile":
            for line in content.splitlines():
                match = re.match(r'^\s*gem\s+["\']([^"\']+)["\']\s*(?:,\s*["\']([^"\']+)["\'])?', line)
                if match:
                    found.append((path, match.group(1), match.group(2) or "unconstrained"))
    return found

def analyze(data):
    files = data["files"]
    extensions = collections.Counter()
    folders = collections.Counter()
    languages = collections.Counter()
    for item in files:
        path = item["path"]
        directory = path.split("/")[0] if "/" in path else "(root)"
        folders[directory] += 1
        suffix = os.path.splitext(path)[1].lower() or "(none)"
        extensions[suffix] += 1
        if suffix in EXTENSIONS:
            languages[EXTENSIONS[suffix]] += 1
    deps = dependencies(data["manifests"])
    framework_evidence = {}
    for path, content in data["manifests"].items():
        if content:
            for name, label in FRAMEWORKS.items():
                if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", content, re.I):
                    framework_evidence.setdefault(label, path)
    # Transparent heuristic: file count, directory count, file-type variety, dependency count.
    # Score is structural complexity (0-100), NOT cyclomatic complexity or code quality.
    n = len(files)
    depth = max((path["path"].count("/") for path in files), default=0)
    factors = {"file_volume": min(30, n / 20), "directory_depth": min(20, depth * 4), "language_variety": min(20, len(languages) * 5), "dependency_volume": min(30, len(deps) / 2)}
    score = round(sum(factors.values()), 1)
    unpinned = [(p, name, v) for p, name, v in deps if v in ("*", "latest", "unconstrained", "") or v.startswith((">=", "^", "~", "~=", ">"))]
    monthly = collections.Counter()
    for commit in data["commits"]:
        try:
            date = commit["commit"]["author"]["date"][:7]
            if re.fullmatch(r"\d{4}-\d{2}", date):
                monthly[date] += 1
        except (KeyError, TypeError):
            continue
    return {"languages": languages, "extensions": extensions, "folders": folders, "frameworks": framework_evidence, "dependencies": deps, "unpinned": unpinned, "complexity": score, "factors": factors, "monthly": monthly}

def render(data, a):
    m = data["metadata"]
    lines = ["=" * 68, "GITHUB REPOSITORY ANALYZER | TRACK B", "=" * 68, "Repository: " + m.get("full_name", "Unknown"), "Description: " + (m.get("description") or "Not specified"), "Default branch: " + str(m.get("default_branch", "Unknown")), "Stars: %s | Forks: %s" % (m.get("stargazers_count", "?"), m.get("forks_count", "?")), ""]
    lines += ["[1] TECH STACK (file-count evidence, not GitHub byte percentages)"]
    lines += ["  %s: %s source files" % (k, v) for k, v in a["languages"].most_common(12)] or ["  No recognized source language"]
    lines += ["  %s (evidence: %s)" % (k, v) for k, v in sorted(a["frameworks"].items())] or ["  No recognized framework evidence"]
    lines += ["", "[2] FILE STRUCTURE", "  Files analyzed: %s%s" % (len(data["files"]), " (INCOMPLETE: GitHub tree truncated)" if data["tree_truncated"] else ""), "  Major areas:"]
    lines += ["    %s: %s files" % (k, v) for k, v in a["folders"].most_common(12)]
    lines += ["  File types: " + (", ".join("%s=%s" % x for x in a["extensions"].most_common(12)) or "None")]
    lines += ["  Directory purposes are not inferred without evidence.", "", "[3] STRUCTURAL COMPLEXITY", "  Score: %.1f / 100 (higher = more structurally complex)" % a["complexity"]]
    lines += ["  %s: %.1f" % x for x in a["factors"].items()]
    lines += ["  Formula: min(30,files/20) + min(20,max_depth*4) +", "           min(20,recognized_languages*5) + min(30,dependencies/2)", "  This is NOT cyclomatic complexity or a maintainability grade.", "", "[4] DEPENDENCY HEALTH"]
    if not data["manifests"]:
        lines += ["  No recognized dependency manifest found; health cannot be determined."]
    else:
        lines += ["  Manifests: " + ", ".join(data["manifests"])]
        lines += ["  Parsed dependencies: %s" % len(a["dependencies"])]
        lines += ["    %s %s (%s)" % (name, version, path) for path, name, version in a["dependencies"][:35]]
        if len(a["dependencies"]) > 35:
            lines += ["  ... %s additional dependencies omitted from display" % (len(a["dependencies"]) - 35)]
        lines += ["  Loose/unpinned constraints detected: %s" % len(a["unpinned"])]
        lines += ["  Health definition: tighter version constraints reduce uncontrolled updates;", "  freshness, CVEs, and maintenance status are NOT checked."]
        if not a["dependencies"]:
            lines += ["  No dependencies parsed; health is undetermined (parser supports npm, pip, Dart and Go)."]
    lines += ["", "[5] CONTRIBUTION ACTIVITY (up to 300 recent commits)", "  Monthly commits in retrieved sample:"]
    if a["monthly"]:
        for month, count in sorted(a["monthly"].items())[-12:]:
            lines += ["  %s | %-35s %d" % (month, "#" * min(35, count), count)]
    else:
        lines += ["  No commit dates available"]
    contributors = data["contributors"]
    lines += ["  Top contributors: " + (", ".join("%s (%s)" % (x.get("login", "unknown"), x.get("contributions", "?")) for x in contributors[:8]) if isinstance(contributors, list) and contributors else "Unavailable")]
    lines += ["  Note: chart covers retrieved commits, not necessarily full history.", "=" * 68]
    return "\n".join(lines)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze any public GitHub repository.")
    parser.add_argument("url", help="https://github.com/owner/repo")
    parser.add_argument("--json", dest="json_path", help="Save full structured report as JSON")
    args = parser.parse_args(argv)
    try:
        data = fetch(args.url, os.getenv("GITHUB_TOKEN"))
        analysis = analyze(data)
        print(render(data, analysis))
        if args.json_path:
            def serialize(x):
                if isinstance(x, collections.Counter):
                    return dict(x)
                raise TypeError(type(x).__name__)
            output = {"repository": data["metadata"].get("full_name"), "analysis": analysis, "tree_truncated": data["tree_truncated"], "commits_sampled": len(data["commits"])}
            with open(args.json_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, default=serialize)
            print("JSON saved:", args.json_path)
        return 0
    except (AnalyzerError, OSError) as exc:
        print("Error:", exc, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
