"""Guard the GitHub Actions GITHUB_TOKEN permission baseline.

Only CodeQL may request security-events: write; all other workflows are
read-only at the top level. Projects V2 uses a separate scoped token.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
REQUIRED = {"contents": "read"}
CODEQL = {
    "contents": "read",
    "security-events": "write",
    "packages": "read",
    "actions": "read",
}


def parse_top_level_permissions(text):
    match = re.search(r"(?m)^permissions:\s*\n((?:^[ \t]+[^\n]*\n?)*)", text)
    if not match:
        raise AssertionError("Missing top-level permissions")
    result = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not re.fullmatch(r"  [A-Za-z-]+:\s*(?:read|write|none)\s*", line):
            raise AssertionError("Unsupported permissions format: " + line)
        key, val = line.strip().split(":", 1)
        if key in result:
            raise AssertionError("Duplicate permission: " + key)
        result[key] = val.strip()
    return result


class WorkflowPermissionPolicyTests(unittest.TestCase):
    def test_every_workflow_uses_approved_top_level_permissions(self):
        files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                expected = CODEQL if path.name == "codeql.yml" else REQUIRED
                self.assertEqual(parse_top_level_permissions(text), expected)
                self.assertNotRegex(text, r"(?m)^permissions:\s*(?:write-all|read-all)")
                # Job overrides must be reviewed explicitly, not silently added.
                self.assertEqual(len(re.findall(r"(?m)^\s+permissions:\s*$", text)), 0)

    def test_parser_rejects_broad_permissions(self):
        with self.assertRaises(AssertionError):
            parse_top_level_permissions("permissions:\n  contents: write\n  packages: write\n")


if __name__ == "__main__":
    unittest.main()
