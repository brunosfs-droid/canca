#!/usr/bin/env python3
"""Verify an R03 E0 SHA-256 manifest against the original evidence bundle."""
import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.bundle.is_symlink():
        parser.error("bundle root must not be a symbolic link")
    root = args.bundle.resolve(strict=True)
    if not root.is_file() and not root.is_dir():
        parser.error("bundle must be a regular file or directory")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if manifest["type"] != "canca.r03.e0.bundle_manifest.v1":
            raise ValueError("unsupported manifest")
        entries = manifest["files"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("empty manifest")
        expected = {}
        for item in entries:
            name = item["relative_path"]
            path = PurePosixPath(name)
            if not isinstance(name, str) or not name or path.is_absolute() or any(p in (".", "..") for p in name.split("/")) or str(path) != name or name in expected:
                raise ValueError("unsafe or duplicate relative path")
            if not isinstance(item["size_bytes"], int) or item["size_bytes"] < 0:
                raise ValueError("invalid size")
            sha = item["sha256"]
            if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
                raise ValueError("invalid SHA-256")
            expected[name] = (item["size_bytes"], sha)
        if manifest["source_file_count"] != len(expected):
            raise ValueError("file count mismatch")
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        actual = {}
        for file in files:
            if file.is_symlink():
                raise ValueError("symlink not permitted")
            if not file.is_file():
                continue
            name = file.name if root.is_file() else file.relative_to(root).as_posix()
            digest = hashlib.sha256()
            with file.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            actual[name] = (file.stat().st_size, digest.hexdigest())
        if actual != expected:
            raise ValueError("bundle contents differ from manifest")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"FAIL: evidence bundle verification: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {len(actual)} files match SHA-256 manifest; operational E0 remains PENDING")
    return 0

if __name__ == "__main__":
    sys.exit(main())
