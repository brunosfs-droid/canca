#!/usr/bin/env python3
"""Generate a read-only governance dashboard from an existing Projects V2 audit."""
import argparse
from collections import Counter
import json
from pathlib import Path


def dashboard(audit):
    if not isinstance(audit, dict) or not isinstance(audit.get("metrics"), dict):
        raise ValueError("Invalid governance audit")
    metrics = audit["metrics"]
    inspected = metrics.get("inspected_items")
    missing = metrics.get("missing_total_by_field")
    if type(inspected) is not int or inspected < 0 or not isinstance(missing, dict):
        raise ValueError("Missing coverage metrics")
    fields = ("Priority", "Workstream", "Target Release")
    if any(type(missing.get(k)) is not int or missing[k] < 0 or missing[k] > inspected for k in fields):
        raise ValueError("Invalid field counts")
    conflicts = audit.get("consistency_findings", [])
    unclassified = audit.get("unclassified_items", [])
    if not isinstance(conflicts, list) or not isinstance(unclassified, list):
        raise ValueError("Invalid findings")
    return {
        "schema_version": 1,
        "source_mode": audit.get("mode", "unknown"),
        "inspected_items": inspected,
        "classification_coverage": {
            k: {"assigned": inspected - missing[k], "missing": missing[k],
                "percent": round(100 * (inspected - missing[k]) / inspected, 2) if inspected else None}
            for k in fields
        },
        "consistency_findings": len(conflicts),
        "consistency_by_rule": dict(sorted(Counter(x["rule"] for x in conflicts).items())),
        "unclassified_items": len(unclassified),
        "manual_triage": audit.get("manual_triage", {}),
        "source": "projects-audit.json",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = dashboard(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
