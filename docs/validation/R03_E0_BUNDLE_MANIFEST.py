#!/usr/bin/env python3
"""Create a reproducible, non-destructive E0 source-bundle evidence manifest.

This tool DOES NOT qualify the bundle or mark operational E0 as passed.
It records only verified file bytes; review and redact before publishing.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="EVE-NG export file or evidence directory")
    parser.add_argument("--output", type=Path, required=True, help="manifest JSON output outside the bundle")
    args = parser.parse_args()
    root = args.bundle.resolve(strict=True)
    out = args.output.resolve()
    if not root.is_file() and not root.is_dir():
        parser.error("bundle must be a regular file or directory")
    paths = [root] if root.is_file() else sorted(root.rglob("*"))
    files = []
    for path in paths:
        if path.is_symlink():
            parser.error("symbolic links in evidence bundles are prohibited")
        if not path.is_file():
            continue
        relative = path.name if root.is_file() else path.relative_to(root).as_posix()
        if path.resolve() == out:
            parser.error("output cannot reside inside the evidence bundle")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        files.append({"relative_path": relative, "sha256": digest.hexdigest(), "size_bytes": path.stat().st_size})
    if not files:
        parser.error("bundle contains no regular files")
    manifest = {
        "type": "canca.r03.e0.bundle_manifest.v1",
        "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "inventory_only_not_homologated",
        "source_file_count": len(files),
        "files": files,
        "operational_e0": "pending",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        parser.error("output already exists; refusing to overwrite prior evidence")
    with out.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"Recorded SHA-256 for {len(files)} files. E0 remains PENDING. Review filenames before sharing.")

if __name__ == "__main__":
    main()
