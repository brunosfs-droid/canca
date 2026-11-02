#!/usr/bin/env python3
"""Fail PR checks for HIGH Bandit issues on added Python lines only.

Existing findings outside the PR diff remain visible in the Bandit artifact.
This is an incremental gate, not a full codebase security attestation.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def changed_lines(base):
    proc = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--unified=0", "--diff-filter=ACMR",
         base + "...HEAD", "--", "*.py"],
        check=True, capture_output=True, text=True,
    )
    changed = {}
    filename = None
    for row in proc.stdout.splitlines():
        if row.startswith("+++ b/"):
            filename = row[6:]
        elif row.startswith("+++ /dev/null"):
            filename = None
        elif filename and row.startswith("@@"):
            match = HUNK.match(row)
            if not match:
                raise ValueError("Unexpected diff hunk: " + row)
            start = int(match.group(1))
            count = int(match.group(2) or "1")
            changed.setdefault(filename, set()).update(range(start, start + count))
    return changed


def new_high_findings(report, added):
    findings = []
    for item in report.get("results", []):
        if item.get("issue_severity", "").upper() != "HIGH":
            continue
        path = item.get("filename", "").removeprefix("./")
        line = item.get("line_number")
        if isinstance(line, int) and line in added.get(path, set()):
            findings.append(item)
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        if not isinstance(report, dict) or not isinstance(report.get("results"), list):
            raise ValueError("Invalid Bandit report structure")
        if report.get("errors"):
            raise ValueError("Bandit reported scanner errors")
        findings = new_high_findings(report, changed_lines(args.base))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print("::error::Bandit gate could not complete: " + str(exc))
        return 2
    for item in findings:
        print(f"::error file={item['filename']},line={item['line_number']}::"
              f"New HIGH Bandit finding {item.get('test_id', 'unknown')}")
    print(f"New HIGH severity findings on added Python lines: {len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
