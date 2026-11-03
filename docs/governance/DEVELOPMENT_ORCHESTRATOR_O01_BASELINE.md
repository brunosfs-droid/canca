# Development Orchestrator — O01 baseline

Status: proposal pending review. 2026-11-03.

Repository: brunosfs-droid/canca. Baseline main SHA: eab8b16400ba78bff3ded2476b0272a7a32831c2.

Verified: 22 workflows, active main ruleset, 8 required checks, open PRs #267/#276/#280, governance closure PR #312 merged. Real EVE-NG E0 remains pending; do not merge PR #267. Governance dossier documents residual risks and requires owner sign-off.

Execution roadmap: O01 #314 baseline and architecture; O02 #315 webhook/CI event proof of concept; O03 #316 durable agent scheduler; O04 #317 protected supervised delivery; O05 #318 full qualification.

Architecture proposal: GitHub Issues/Projects V2 as planning system; Python event receiver and SQLite persistent transaction log; sandboxed agent adapter; GitHub Actions CI observer; fail-closed policy gate; auditable event ledger and budget guardrails. Start with one task at a time. Do not equate workflow success with all checks or external lab approval.

O01 remaining acceptance: inspect every workflow trigger and permissions, Projects V2 live field coverage, security controls, tokens and quotas, agent cost model, threat model, idempotent event schema, recovery tests and owner signoff. No autonomous merges or product development authorized by this document.
