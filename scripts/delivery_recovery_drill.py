#!/usr/bin/env python3
"""Rehearse restoring critical delivery configuration from a trusted git SHA.

Operates only in a temporary directory; never changes local checkout or remote.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

FILES = (
    ".github/workflows/python-ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/projects-v2-governance.yml",
    ".github/workflows/release-preflight.yml",
    "scripts/release_preflight.py",
    "docs/governance/CI_CD_PHASE_CLOSURE.md",
)


def git_read(sha, path):
    result = subprocess.run(["git", "show", f"{sha}:{path}"],
                            capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Unable to recover {path} from requested commit")
    return result.stdout


def restore_and_verify(sha, files=FILES):
    if not sha or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("Full lowercase git commit SHA required")
    verified = []
    with tempfile.TemporaryDirectory(prefix="canca-delivery-recovery-") as root:
        for name in files:
            source = git_read(sha, name)
            destination = Path(root) / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source)
            restored = destination.read_bytes()
            if restored != source:
                raise RuntimeError(f"Recovery verification failed for {name}")
            verified.append({"file": name, "sha256": hashlib.sha256(restored).hexdigest(),
                             "bytes": len(restored)})
    return {"schema_version": 1, "source_sha": sha, "files_verified": len(verified),
            "files": verified, "local_restore_rehearsal": "passed",
            "remote_repository_modified": False,
            "limitation": "No remote rollback, branch-protection bypass or application restore was executed"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = restore_and_verify(args.sha)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Restored and verified {report['files_verified']} delivery files in an isolated temporary directory")


if __name__ == "__main__":
    main()
