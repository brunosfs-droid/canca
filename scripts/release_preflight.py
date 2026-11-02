#!/usr/bin/env python3
"""Read-only release preflight from GitHub commit checks; never create releases."""
import argparse
import json
import re
import subprocess

TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?$")


def evaluate(tag, sha, checks, existing_ref=None):
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Tag must be SemVer (e.g. v0.7.0-alpha.1)")
    if existing_ref is not None:
        raise ValueError("Ref already exists; refusing tag/release reuse")
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("Expected full commit SHA")
    names = {}
    for check in checks:
        name = check.get("name")
        if name:
            names.setdefault(name, []).append(check)
    # The manually dispatched preflight itself is not a prerequisite check.
    names.pop("preflight", None)
    passed = sorted(name for name, entries in names.items() if
                    any(x.get("status") == "completed" and x.get("conclusion") == "success"
                        for x in entries))
    failed = sorted(name for name, entries in names.items() if not
                    any(x.get("status") == "completed" and x.get("conclusion") == "success"
                        for x in entries))
    return {"schema_version": 1, "tag_candidate": tag, "commit": sha,
            "check_runs_passed": len(passed), "check_runs_not_successful": failed,
            "decision": "review_required", "publication": "not_performed",
            "limitations": "This preflight does not certify EVE-NG, release content, or deployment recovery."}


def github(endpoint):
    result = subprocess.run(["gh", "api", endpoint],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("GitHub API error: " + result.stderr[:350])
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    # Do not quietly interpret missing check data as success.
    checks_response = github(f"repos/brunosfs-droid/canca/commits/{args.sha}/check-runs?per_page=100")
    checks = checks_response["check_runs"]
    if checks_response.get("total_count", 0) > len(checks) or not checks:
        raise RuntimeError("Check results are missing or truncated")
    ref_exists = None
    ref_probe = subprocess.run(
        ["gh", "api", f"repos/brunosfs-droid/canca/git/ref/tags/{args.tag}"],
        capture_output=True, text=True, check=False,
    )
    if ref_probe.returncode == 0:
        ref_exists = True
    elif "404" not in ref_probe.stderr:
        raise RuntimeError("Could not verify tag absence: " + ref_probe.stderr[:300])
    report = evaluate(args.tag, args.sha, checks, existing_ref=ref_exists)
    with open(args.output, "w", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps(report, ensure_ascii=False))
    # Evidence collection succeeds even when the proposed release needs review.
    # The JSON explicitly records incomplete checks and never authorizes publication.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
