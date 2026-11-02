#!/usr/bin/env python3
"""Render a human-readable GitHub Actions summary from a verified dashboard."""
import argparse
import json
from pathlib import Path


def render(dashboard):
    fields = dashboard["classification_coverage"]
    rows = ["## Projects V2 — Governance Dashboard", "",
            f"Items inspected: **{dashboard['inspected_items']}**", "",
            "| Field | Assigned | Missing | Coverage |",
            "| --- | ---: | ---: | ---: |"]
    for name in ("Priority", "Workstream", "Target Release"):
        item = fields[name]
        percent = "N/A" if item["percent"] is None else f"{item['percent']:.2f}%"
        rows.append(f"| {name} | {item['assigned']} | {item['missing']} | {percent} |")
    rows += ["", f"Consistency findings: **{dashboard['consistency_findings']}**",
             f"Items needing classification review: **{dashboard['unclassified_items']}**",
             "", "This report is read-only; see the JSON artifacts for full evidence."]
    return "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.write_text(render(result), encoding="utf-8")


if __name__ == "__main__":
    main()
