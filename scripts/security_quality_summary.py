#!/usr/bin/env python3
"""Summarize local static-analysis JSON reports without mutating GitHub state."""
import argparse
from collections import Counter
import json
from pathlib import Path


def read_report(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeError, ValueError) as exc:
        return None, type(exc).__name__


def summarize(bandit, ruff, audits):
    output = {"schema_version": 1, "bandit": {}, "ruff": {}, "dependencies": {}}
    if bandit is None or not isinstance(bandit.get("results"), list):
        output["bandit"] = {"status": "unavailable"}
    else:
        counts = Counter(x.get("issue_severity", "UNKNOWN").upper() for x in bandit["results"])
        output["bandit"] = {
            "status": "scan_error" if bandit.get("errors") else "reported",
            "total": len(bandit["results"]), "by_severity": dict(sorted(counts.items())),
            "scanner_errors": len(bandit.get("errors", [])),
        }
    if ruff is None or not isinstance(ruff, list):
        output["ruff"] = {"status": "unavailable"}
    else:
        counts = Counter(x.get("code", "UNKNOWN") for x in ruff)
        output["ruff"] = {"status": "reported", "total": len(ruff),
                           "by_rule": dict(sorted(counts.items()))}
    for name, data in sorted(audits.items()):
        if data is None or not isinstance(data, dict) or not isinstance(data.get("dependencies"), list):
            output["dependencies"][name] = {"status": "unavailable"}
            continue
        vulns = sum(len(d.get("vulns", [])) for d in data["dependencies"])
        output["dependencies"][name] = {"status": "reported", "vulnerabilities": vulns,
                                        "packages": len(data["dependencies"])}
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bandit", type=Path, required=True)
    parser.add_argument("--ruff", type=Path, required=True)
    parser.add_argument("--audit", nargs=2, action="append", metavar=("NAME", "JSON"), default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bandit, _ = read_report(args.bandit)
    ruff, _ = read_report(args.ruff)
    audits = {name: read_report(Path(path))[0] for name, path in args.audit}
    result = summarize(bandit, ruff, audits)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    # Missing or malformed scans must not be reported as a clean bill of health.
    statuses = [result["bandit"]["status"], result["ruff"]["status"]]
    statuses += [v["status"] for v in result["dependencies"].values()]
    return 2 if any(status != "reported" for status in statuses) else 0


if __name__ == "__main__":
    raise SystemExit(main())
