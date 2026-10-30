# Cancã Projects V2 governance sync

A deliberately conservative audit for the **user-owned** Project #4.

## Setup
1. Create a **classic** GitHub PAT with `project` access (and `repo` only if the project/repository needs private repository access). Do **not** paste the token into a PR, Issue, chat or committed file.
2. Repository > Settings > Secrets and variables > Actions > New repository secret: `PROJECTS_TOKEN`.
3. Actions > Projects V2 governance audit > Run workflow. Leave `apply=false` on the first run; review the JSON artifact.
4. After checking the recommendations, rerun with `apply=true`.

The default `GITHUB_TOKEN` does not provide the user-level Projects V2 access required here. The code uses `gh api graphql`, with `GH_TOKEN` supplied only as a secret.

## Rules
- Scope: **only** `brunosfs-droid/canca` items in user Project #4.
- Fills **empty** Priority, Workstream and Target Release only. Never overwrites populated fields, Status, dates, owners, milestones or labels.
- Workstream from `area:r01`...`area:r06`, `area:product`, `area:security` or `dependencies`.
- Priority from explicit `priority:p0`...`priority:p3` labels only. No inferred urgency.
- Target Release from existing repository milestone, not version-name guesses. `Community Beta` -> Beta; Alpha gates and M-A...M-E -> Alpha.
- Missing/select-option mismatch is reported. A dry run has no writes. No automatic merges or Issue closure.
- Execute manually at first. A schedule can be added only after audit results and token permissions have been reviewed.

## Limitations
GitHub Project field values are not repository labels. A milestone date does not automatically set the Project's `Target date` field. The classification of historical collector issues as Alpha may need an explicit release exception; review audit output before applying.
