#!/usr/bin/env python3
"""Audits Projects V2 fields; only fills empty values with --apply. Python stdlib."""
import argparse
import json
import os
import subprocess
import sys

OWNER = "brunosfs-droid"
PROJECT_NUMBER = 4
REPOSITORY = "brunosfs-droid/canca"
FIELDS = ("Priority", "Workstream", "Target Release")

QUERY = """query($owner:String!, $number:Int!, $cursor:String) {
  user(login:$owner) {
    projectV2(number:$number) {
      id
      fields(first:100) { nodes {
        ... on ProjectV2SingleSelectField { id name options { id name } }
      } }
      items(first:100, after:$cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            ... on Issue { number title repository { nameWithOwner } milestone { title }
              labels(first:30) { nodes { name } } }
            ... on PullRequest { number title repository { nameWithOwner } milestone { title }
              labels(first:30) { nodes { name } } }
          }
          fieldValues(first:40) { nodes {
            ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2SingleSelectField { name } } }
          } }
        }
      }
    }
  }
}"""
MUTATION = """mutation($project:ID!, $item:ID!, $field:ID!, $option:String!) {
  updateProjectV2ItemFieldValue(input:{
    projectId:$project, itemId:$item, fieldId:$field,
    value:{singleSelectOptionId:$option}
  }) { projectV2Item { id } }
}"""

def graphql(query, variables):
    args = ["gh", "api", "graphql", "-f", "query=" + query]
    for key, value in variables.items():
        if value is None:
            continue
        args += ["-F" if isinstance(value, (int, bool)) else "-f", key + "=" + str(value)]
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode:
        raise RuntimeError("GraphQL request failed: " + proc.stderr[:600])
    data = json.loads(proc.stdout)
    if data.get("errors"):
        raise RuntimeError("GraphQL returned errors: " + json.dumps(data["errors"])[:600])
    return data["data"]

def classification(content):
    labels = {x["name"].lower() for x in content["labels"]["nodes"]}
    milestone = (content.get("milestone") or {}).get("title", "")
    workstream = next((f"R{n:02d}" for n in range(1, 7) if f"area:r0{n}" in labels), None)
    if not workstream:
        if "area:security" in labels or "dependencies" in labels:
            workstream = "Security"
        elif "area:product" in labels or milestone in ("Product Alpha", "Community Beta"):
            workstream = "Product"
    release = None
    if milestone == "Community Beta":
        release = "Beta"
    elif milestone in ("M-A · Isolation", "M-B · Collectors", "M-C · Model & Observations",
                       "M-D · Graph & Topology", "M-E · Recovery & Quality", "Product Alpha"):
        release = "Alpha"
    if "priority:p0" in labels:
        priority = "P0"
    elif "priority:p1" in labels:
        priority = "P1"
    elif "priority:p2" in labels:
        priority = "P2"
    elif "priority:p3" in labels:
        priority = "P3"
    else:
        priority = None
    return {"Priority": priority, "Workstream": workstream, "Target Release": release}

def audit_metrics(changes, inspected_items):
    """Aggregate only observed classifications; never infer missing priorities."""
    by_field = {name: 0 for name in FIELDS}
    by_action = {}
    for entry in changes:
        by_field[entry["field"]] += 1
        action = entry["action"]
        by_action[action] = by_action.get(action, 0) + 1
    return {
        "inspected_items": inspected_items,
        "field_values_inspected": inspected_items * len(FIELDS),
        "proposed_changes": len(changes),
        "missing_by_field": by_field,
        "actions": dict(sorted(by_action.items())),
    }


def gaps_without_suggestion(existing, proposed):
    return [name for name in FIELDS if not existing.get(name) and not proposed.get(name)]


def consistency_warnings(content, existing):
    """Report contradictions without making classification decisions."""
    labels = {row["name"].lower() for row in content["labels"]["nodes"]}
    warnings = []
    priority_labels = sorted(x for x in labels if x in
                             {"priority:p0", "priority:p1", "priority:p2", "priority:p3"})
    if len(priority_labels) > 1:
        warnings.append("multiple_priority_labels")
    areas = sorted(x for x in labels if x in
                   {"area:r01", "area:r02", "area:r03", "area:r04", "area:r05", "area:r06"})
    if len(areas) > 1:
        warnings.append("multiple_workstream_labels")
    milestone = (content.get("milestone") or {}).get("title", "")
    if milestone == "Community Beta" and existing.get("Target Release") == "Alpha":
        warnings.append("beta_milestone_alpha_release")
    if milestone in {"Product Alpha", "M-A · Isolation", "M-B · Collectors",
                     "M-C · Model & Observations", "M-D · Graph & Topology",
                     "M-E · Recovery & Quality"} and existing.get("Target Release") == "Beta":
        warnings.append("alpha_milestone_beta_release")
    return warnings


def triage_summary(changes, findings, missing_without_suggestion):
    """Provide deterministic, read-only queues for operator review."""
    queue = {}
    for entry in changes:
        if entry["action"] == "skipped_missing_option":
            key = ("missing_project_option", entry["number"])
            queue.setdefault(key, set()).add(entry["field"])
    for entry in findings:
        key = ("classification_conflict", entry["number"])
        queue.setdefault(key, set()).add(entry["rule"])
    return {
        "requires_manual_classification": dict(missing_without_suggestion),
        "review_items": [
            {"number": number, "reason": reason, "details": sorted(values)}
            for (reason, number), values in sorted(queue.items(), key=lambda x: (x[0][1], x[0][0]))
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write only missing field values")
    args = parser.parse_args()
    if not os.environ.get("GH_TOKEN"):
        sys.exit("GH_TOKEN is required (GitHub Projects access).")
    cursor = None
    audit = []
    inspected_items = 0
    missing_without_suggestion = {name: 0 for name in FIELDS}
    consistency_findings = []
    unclassified_items = []
    while True:
        project = graphql(QUERY, {"owner": OWNER, "number": PROJECT_NUMBER, "cursor": cursor})["user"]["projectV2"]
        if not project:
            sys.exit("Project not found or inaccessible")
        fields = {f["name"]: f for f in project["fields"]["nodes"] if f and f.get("name") in FIELDS}
        missing_fields = set(FIELDS) - set(fields)
        if missing_fields:
            sys.exit("Missing single-select fields: " + ", ".join(sorted(missing_fields)))
        items = project["items"]
        for item in items["nodes"]:
            content = item.get("content")
            if not content or content.get("repository", {}).get("nameWithOwner") != REPOSITORY:
                continue
            inspected_items += 1
            existing = {v["field"]["name"]: v["name"] for v in item["fieldValues"]["nodes"]
                        if v and v.get("field") and v.get("name")}
            proposed = classification(content)
            for warning in consistency_warnings(content, existing):
                consistency_findings.append({"number": content["number"], "rule": warning})
            gaps = gaps_without_suggestion(existing, proposed)
            for field_name in gaps:
                missing_without_suggestion[field_name] += 1
            if gaps:
                unclassified_items.append({"number": content["number"], "fields": gaps})
            for field_name, value in proposed.items():
                if not value or existing.get(field_name):
                    continue
                field = fields[field_name]
                options = {x["name"].lower(): x["id"] for x in field["options"]}
                option_id = options.get(value.lower())
                entry = {"number": content["number"], "field": field_name, "suggested": value,
                         "action": "skipped_missing_option" if not option_id else ("write" if args.apply else "dry_run")}
                if args.apply and option_id:
                    graphql(MUTATION, {"project":project["id"], "item":item["id"],
                                       "field":field["id"], "option":option_id})
                audit.append(entry)
        if not items["pageInfo"]["hasNextPage"]:
            break
        cursor = items["pageInfo"]["endCursor"]
    metrics = audit_metrics(audit, inspected_items)
    metrics["missing_without_suggestion"] = missing_without_suggestion
    metrics["consistency_findings_count"] = len(consistency_findings)
    metrics["missing_total_by_field"] = {
        name: metrics["missing_by_field"][name] + missing_without_suggestion[name]
        for name in FIELDS
    }
    print(json.dumps({"mode": "apply" if args.apply else "dry_run", "changes": audit,
                      "consistency_findings": consistency_findings,
                      "manual_triage": triage_summary(audit, consistency_findings, missing_without_suggestion),
                      "unclassified_items": unclassified_items,
                      "metrics": metrics},
                     indent=2, ensure_ascii=False))
    if any(a["action"] == "skipped_missing_option" for a in audit):
        sys.exit("One or more desired field options do not exist; no values were invented.")

if __name__ == "__main__":
    main()
