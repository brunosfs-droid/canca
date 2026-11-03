# Development Orchestrator — O01 baseline

Status: proposal pending review. 2026-11-03.

Repository: brunosfs-droid/canca. Baseline main SHA: eab8b16400ba78bff3ded2476b0272a7a32831c2.

Verified: 22 workflows, active main ruleset, 8 required checks, open PRs #267/#276/#280, governance closure PR #312 merged. Real EVE-NG E0 remains pending; do not merge PR #267. Governance dossier documents residual risks and requires owner sign-off.

Execution roadmap: O01 #314 baseline and architecture; O02 #315 webhook/CI event proof of concept; O03 #316 durable agent scheduler; O04 #317 protected supervised delivery; O05 #318 full qualification.

Architecture proposal: GitHub Issues/Projects V2 as planning system; Python event receiver and SQLite persistent transaction log; sandboxed agent adapter; GitHub Actions CI observer; fail-closed policy gate; auditable event ledger and budget guardrails. Start with one task at a time. Do not equate workflow success with all checks or external lab approval.

O01 remaining acceptance: inspect every workflow trigger and permissions, Projects V2 live field coverage, security controls, tokens and quotas, agent cost model, threat model, idempotent event schema, recovery tests and owner signoff. No autonomous merges or product development authorized by this document.

## Hosting and cost decision — 2026-11-03

Approved initial deployment: **user-managed local computer**, not AWS. This decision applies to the **internal Development Orchestrator**, not the Cancã product runtime.

- Monthly external services/API spending cap: **BRL 30**; target zero additional fixed infrastructure cost. Do not start billable unattended agent calls until metering and enforced budget cutoff are validated. A spending cap is a safety goal, not a guarantee of token costs or availability.
- Initial execution: single Python worker and SQLite on local storage; loopback-bound operator interface, no public inbound service by default. Prefer GitHub API polling first (respecting rate limits); consider authenticated webhooks only if secure ingress becomes worthwhile.
- Computer must be powered on, connected, and running the service for continuous operation. On shutdown/reboot/network loss, persist state, pause work safely, then reconcile GitHub and resume only eligible tasks when the process returns.
- No AWS resources or recurring hosting expense to be provisioned in O01/O02.
- O01 still must verify workstation OS, runtime installation, credentials, secret storage, startup mechanism and selected agent pricing before enabling unattended execution; do not publish local/private machine details.

This is a recorded implementation constraint, **not** authorization to make production changes or bypass protected PR checks.
