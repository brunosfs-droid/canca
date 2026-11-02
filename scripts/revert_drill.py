#!/usr/bin/env python3
"""Non-destructive rehearsal of reverting a commit on an isolated test branch."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def run(*args, cwd=None):
    proc = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"git {args[0]} failed: " + proc.stderr[:300])
    return proc.stdout.strip()


def rehearse():
    with tempfile.TemporaryDirectory(prefix="canca-revert-") as td:
        root = Path(td)
        run("init", "-q", cwd=root)
        run("config", "user.name", "CI Revert Drill", cwd=root)
        run("config", "user.email", "ci-revert@example.invalid", cwd=root)
        marker = root / "revert-test.txt"
        marker.write_text("baseline\n", encoding="utf-8")
        run("add", "revert-test.txt", cwd=root)
        run("commit", "-qm", "baseline", cwd=root)
        initial_sha = run("rev-parse", "HEAD", cwd=root)
        marker.write_text("baseline\nnon-production change\n", encoding="utf-8")
        run("add", "revert-test.txt", cwd=root)
        run("commit", "-qm", "simulate pull request change", cwd=root)
        test_sha = run("rev-parse", "HEAD", cwd=root)
        run("revert", "--no-edit", test_sha, cwd=root)
        restored = marker.read_text(encoding="utf-8") == "baseline\n"
        clean = not run("status", "--porcelain", cwd=root)
        if not restored or not clean:
            raise RuntimeError("Revert did not restore the baseline cleanly")
        return {"schema_version": 1, "initial_commit": initial_sha,
                "test_commit": test_sha, "revert_commit": run("rev-parse", "HEAD", cwd=root),
                "restored": restored, "working_tree_clean": clean,
                "scope": "isolated_temp_git_repository",
                "remote_changes": False,
                "note": "Rehearsal only: does not revert any real Cancã PR or validate GitHub branch protections"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = rehearse()
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
