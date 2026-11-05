import unittest
from unittest.mock import patch
import urllib.error
import analyze

class AnalyzerTests(unittest.TestCase):
    def test_valid_url(self):
        self.assertEqual(analyze.parse_repo("https://github.com/psf/requests.git"), ("psf", "requests"))
    def test_invalid_urls(self):
        for u in ["http://github.com/a/b", "https://evil.com/a/b", "https://github.com/a", "https://github.com/a/b/tree/main"]:
            with self.subTest(u=u), self.assertRaises(analyze.AnalyzerError):
                analyze.parse_repo(u)
    def test_empty(self):
        d = {"metadata": {"full_name": "x/y"}, "files": [], "tree_truncated": False, "manifests": {}, "contributors": [], "commits": []}
        a = analyze.analyze(d)
        self.assertEqual(a["complexity"], 0)
        self.assertIn("No recognized dependency manifest", analyze.render(d, a))
    def test_dependencies(self):
        d = {"metadata": {"full_name": "x/y"}, "files": [{"path": "src/app.ts"}], "tree_truncated": False, "manifests": {"package.json": '{"dependencies":{"react":"^18.0.0","foo":"1.0.0"}}'}, "contributors": [], "commits": []}
        a = analyze.analyze(d)
        self.assertEqual(len(a["dependencies"]), 2)
        self.assertIn("React", a["frameworks"])
        self.assertEqual(len(a["unpinned"]), 1)
    def test_rate_limit(self):
        err = urllib.error.HTTPError("url", 403, "rate limit", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaisesRegex(analyze.AnalyzerError, "rate limit"):
                analyze.request("/repos/psf/requests")
    def test_pep621_dependencies(self):
        manifest = """[project]
dependencies = ["requests>=2.0", "flask==3.0"]
"""
        deps = analyze.dependencies({"pyproject.toml": manifest})
        self.assertEqual(len(deps), 2)
        self.assertEqual({d[1] for d in deps}, {"requests", "flask"})

    def test_no_manifest(self):
        self.assertEqual(analyze.dependencies({}), [])

if __name__ == "__main__":
    unittest.main()
