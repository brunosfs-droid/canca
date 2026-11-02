# Governance and CI/CD phase closure — Cancã

This checklist covers **the repository development and delivery process**, not
functional approval of the Cancã Alpha or EVE-NG operational homologation.

## Phase 1 — Repository security
- [ ] Verify main branch protection and required checks are active
- [ ] Verify Dependabot, secret protections, and code scanning settings
- [ ] Verify workflow token permissions and private secrets are not exposed
- [ ] Archive the configuration evidence and review exceptions

## Phase 2 — CI quality and security
- [ ] Validate Python CI, CodeQL, dependency review, pip-audit, Ruff and Bandit
- [ ] Identify which checks are actually required by branch protection
- [ ] Review advisory findings separately from blockers
- [ ] Preserve test and vulnerability reports and document accepted residual risk

## Phase 3 — Governance and reporting
- [ ] Confirm four permanent GitHub Projects views and saved Insights charts
- [ ] Run Projects V2 audit with apply=false and archive reports
- [ ] Review remaining unclassified project items by state and release
- [ ] Validate evidence summaries and record token expiration/rotation policy

## Phase 4 — Release and delivery recovery
- [ ] Execute read-only release-preflight workflow from main
- [ ] Review preflight JSON, main SHA and complete required status checks
- [ ] Validate release tag uniqueness and version naming conventions
- [ ] Document and rehearse rollback of repository configuration through a PR
- [ ] Validate restore from a known Git commit and revert of a non-production test PR
- [ ] Record who authorizes tagging and release publication; keep manual approval
- [ ] Publish release notes only after checklist sign-off

## Explicitly deferred to the subsequent Cancã product cycle
- [ ] EVE-NG credentialed collection, Windows/Linux/SSH/WinRM
- [ ] SQL writer functional homologation and persistence lifecycle
- [ ] Product runtime recovery, idempotent resume and operational rollback
- [ ] Product Alpha release Go/No-Go with independently verified lab evidence

**Release preflight is evidence collection only.** It never creates a tag,
release, deployment, or approval. A passing CI check is not the same as verified
operational recovery. Phase closure requires recorded evidence for each item,
not merely a successful merge.
