#!/usr/bin/env python3
"""Read-only Alpha readiness inventory from current GitHub issue/PR metadata.

This is a gate inventory, not certification of technical acceptance.
Closing an issue does NOT establish EVE-NG or recovery evidence.
"""
import argparse
import json
from pathlib import Path
import subprocess

REPOSITORY = "brunosfs-droid/canca"
GATES = (
    ("central_persistence", 63, "R03", "Central persistence and assessment lifecycle"),
    ("sql_writer_lab", 270, "R03", "EVE-NG operational SQL writer validation"),
    ("sql_writer_review", 267, "R03", "Verified SQL write operation"),
    ("recovery", 271, "R05", "Recovery, rollback and idempotent resume"),
    ("quality", 272, "R06", "Quality gates and reproducible benchmarks"),
    ("runbook", 273, "Operations", "Alpha operational runbook"),
    ("windows_collector", 1, "R02", "Windows collector lab validation"),
    ("linux_collector", 2, "R02", "Linux collector implementation"),
    ("ssh_validation", 17, "R02", "Credentialed SSH lab validation"),
    ("winrm_validation", 24, "R02", "Credentialed WinRM lab validation"),
)


def get_issue(number):
    result = subprocess.run(
        ["gh", "api", f"repos/{REPOSITORY}/issues/{number}"],
        text=True, capture_output=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Cannot inspect #{number}: " + result.stderr[:300])
    return json.loads(result.stdout)


def readiness(items):
    rows = []
    for key, number, workstream, description in GATES:
        issue = items[number]
        state = issue.get("state")
        if state not in ("open", "closed"):
            raise ValueError(f"Unknown state for #{number}")
        rows.append({
            "gate": key, "number": number, "workstream": workstream,
            "description": description, "github_state": state,
            "title": issue.get("title", ""),
            "url": issue.get("html_url", f"https://github.com/{REPOSITORY}/issues/{number}"),
            "evidence_status": "not_verified",
        })
    return {
        "schema_version": 1,
        "repository": REPOSITORY,
        "scope": "selected_alpha_gates",
        "gate_count": len(rows),
        "open_gates": sum(x["github_state"] == "open" for x in rows),
        "closed_gates": sum(x["github_state"] == "closed" for x in rows),
        "operational_homologation": "not_verified",
        "release_decision": "not_assessed",
        "warning": "GitHub state is not proof of EVE-NG or operational acceptance",
        "gates": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = readiness({number: get_issue(number) for _, number, _, _ in GATES})
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Alpha gate inventory: {data['gate_count']} tracked; {data['open_gates']} open")
    print("Operational readiness is NOT verified by this report.")


if __name__ == "__main__":
    main()
