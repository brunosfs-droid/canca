#!/usr/bin/env python3
"""Audit presence of CI governance controls without claiming operational closure."""
import argparse
import json
from pathlib import Path

CONTROLS = {
    "phase_1_security": [
        ".github/CODEOWNERS", ".github/workflows/codeql.yml",
        "tests/test_workflow_permissions.py"],
    "phase_2_quality": [
        ".github/workflows/python-ci.yml",
        ".github/workflows/python-static-security.yml",
        ".github/workflows/ruff-quality.yml",
        ".github/workflows/dependency-review.yml"],
    "phase_3_governance": [
        ".github/workflows/projects-v2-governance.yml",
        ".github/workflows/projects-v2-views.yml",
        "scripts/projects_v2_dashboard.py"],
    "phase_4_delivery": [
        ".github/workflows/release-preflight.yml",
        ".github/workflows/delivery-recovery-drill.yml",
        ".github/workflows/revert-drill.yml"],
}


def inventory(root):
    phases = {}
    for name, paths in CONTROLS.items():
        entries = [{"path": path, "present": (root / path).is_file()} for path in paths]
        phases[name] = {
            "controls": entries,
            "source_present": all(e["present"] for e in entries),
            "operational_evidence": "requires_review",
            "closed": False,
        }
    return {"schema_version": 1, "scope": "repository_governance_not_product_alpha",
            "phases": phases, "all_phases_closed": False,
            "warning": "Source presence and passing CI do not establish operational sign-off"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = inventory(args.root)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: data["source_present"] for name, data in report["phases"].items()}))
    if not all(x["source_present"] for x in report["phases"].values()):
        raise SystemExit("One or more declared governance controls are missing")


if __name__ == "__main__":
    main()
