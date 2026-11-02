#!/usr/bin/env python3
"""Audit or provision named Projects V2 views. Dry-run by default.

No item-field updates, deletions, or changes to existing views are performed.
Requires GH_TOKEN with the appropriate Projects access only when executed.
"""
import argparse
import json
import os
import subprocess

OWNER = "brunosfs-droid"
NUMBER = 4
DESIRED = (
    ("Governance · Overview", "TABLE_LAYOUT"),
    ("Governance · Priorities", "TABLE_LAYOUT"),
    ("Governance · Workstreams", "TABLE_LAYOUT"),
    ("Governance · Releases", "TABLE_LAYOUT"),
)

QUERY = """query($owner:String!, $number:Int!) {
  user(login:$owner) {
    projectV2(number:$number) {
      id
      views(first:100) { pageInfo { hasNextPage } nodes { id name layout } }
    }
  }
}"""
CREATE = """mutation($project:ID!, $name:String!, $layout:ProjectV2ViewLayout!) {
  createProjectV2View(input:{projectId:$project,name:$name,layout:$layout}) {
    projectV2View { id name layout }
  }
}"""


def graphql(query, variables):
    args = ["gh", "api", "graphql", "-f", "query=" + query]
    for name, value in variables.items():
        args += ["-F" if isinstance(value, int) else "-f", name + "=" + str(value)]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("GraphQL request failed: " + result.stderr[:500])
    response = json.loads(result.stdout)
    if response.get("errors"):
        raise RuntimeError("GraphQL returned errors: " + json.dumps(response["errors"])[:500])
    return response["data"]


def plan(existing, desired=DESIRED):
    """Never duplicate or overwrite existing view names."""
    names = {view["name"]: view for view in existing}
    output = []
    for name, layout in desired:
        view = names.get(name)
        if view is None:
            output.append({"name": name, "layout": layout, "action": "create"})
        elif view["layout"] != layout:
            output.append({"name": name, "layout": layout, "action": "review_layout_mismatch",
                           "existing_layout": view["layout"]})
        else:
            output.append({"name": name, "layout": layout, "action": "already_exists"})
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Create absent views; existing views are never changed")
    args = parser.parse_args()
    if not os.environ.get("GH_TOKEN"):
        parser.error("GH_TOKEN with Projects access is required")
    data = graphql(QUERY, {"owner": OWNER, "number": NUMBER})
    project = (data.get("user") or {}).get("projectV2")
    if not project:
        raise RuntimeError("Projects V2 board not found or token lacks access")
    views = project["views"]
    if views["pageInfo"]["hasNextPage"]:
        raise RuntimeError("View listing truncated; refusing to create duplicates")
    actions = plan(views["nodes"])
    if any(x["action"] == "review_layout_mismatch" for x in actions):
        raise RuntimeError("View layout mismatch requires manual review before any creation")
    for item in actions:
        if item["action"] == "create":
            if args.apply:
                graphql(CREATE, {"project": project["id"], "name": item["name"],
                                "layout": item["layout"]})
                item["action"] = "created"
            else:
                item["action"] = "would_create"
    print(json.dumps({"mode": "apply" if args.apply else "dry_run",
                      "project_url": f"https://github.com/users/{OWNER}/projects/{NUMBER}",
                      "views": actions}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
