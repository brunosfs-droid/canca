# GitHub Actions token permissions audit — 2026-11-02

Scope: 15 workflows in `.github/workflows` following PR #289.

- 13 workflows: `contents: read` only.
- `codeql.yml`: `contents: read`, `security-events: write`, `packages: read`, `actions: read`.
- `projects-v2-governance.yml`: read-only `GITHUB_TOKEN`, plus a separate `PROJECTS_TOKEN` secret for GitHub Projects V2 API access.

`tests/test_workflow_permissions.py` guards this current allowlist in the standard Python CI. Any expanded permission or job-level override should require an explicit security review and a deliberate test update.

## Remaining manual controls

1. Verify `PROJECTS_TOKEN` scopes, expiration and rotation; never expose its value in logs.
2. Verify repository Actions default workflow permissions and fork-PR approval settings.
3. Verify whether CODEOWNERS review is enforced by the active ruleset, rather than assuming it.
4. Review third-party action pinning by immutable SHA and avoid untrusted PR code with write-capable credentials.

This document records observed configuration; it does not attest to unseen GitHub account settings.
