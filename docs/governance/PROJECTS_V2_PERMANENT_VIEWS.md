# Permanent governance views — Cancã

The `Projects V2 permanent views` workflow inspects Project #4. With explicit apply=true, it creates missing named table views; default is dry-run. It never edits existing views, labels, milestones or item fields.

| View | Recommended manual configuration |
| --- | --- |
| Governance · Overview | Show Status, Priority, Workstream, Target Release and milestone |
| Governance · Priorities | Group by Priority |
| Governance · Workstreams | Group by Workstream |
| Governance · Releases | Group by Target Release |

After creation, configure grouping, filtering and charts in the GitHub Projects UI and save. The script creates only named view shells and does not configure groupings, charts or filters. The Projects Insights pane supports saved charts independently from the GitHub Actions audit summary.

After updating fields, rerun the Projects V2 governance audit with apply=false to refresh coverage evidence.
