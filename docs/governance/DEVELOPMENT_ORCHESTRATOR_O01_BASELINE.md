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

## WSL2 Ubuntu host decision — 2026-11-04

**Confirmed host:** Windows 11 with Ubuntu on WSL2. This replaces the earlier generic local-computer assumption. No AWS infrastructure.

**Proposed boundary**
- Ubuntu WSL2 owns the Python virtualenv, source worktree, SQLite database and restricted agent workspace. Use the Linux ext4 filesystem (for example, `~/canca-dev-orchestrator`), **not** `/mnt/c` for the SQLite database.
- Windows Task Scheduler may launch the WSL distribution on user logon; use a non-elevated dedicated startup task after explicit local validation. A systemd service inside Ubuntu manages the worker with restart policy. Do **not** assume systemd services keep the WSL VM alive after all interactive/background processes exit.
- Initial connection to GitHub uses authenticated API polling (no inbound ports, port forwarding, public listener or webhook tunnel). Use rate-limit-aware polling, bounded concurrency and backoff. Migrate to verified webhook delivery later only if warranted.
- Persist state and checkpoint before planned Windows shutdown. After a power cut, reconcile GitHub run/PR/SHA and leases before resuming. Windows sleep/hibernation is not continuous execution.
- Do not run as `root`; no global Windows admin privileges, no credentials in plaintext config or Git. Use OS-protected credential storage where available and test GitHub App/token scope before unattended execution.
- Secrets/agent execution must remain separated; do not send privileged tokens to untrusted PR builds. Prefer sandboxed subprocess/container with constrained access.
- Monthly paid service/API budget **BRL 30 maximum**, with verified pre-call metering and fail-closed cutoff. Do not enable paid autonomous work merely because WSL2 runs.

**Local read-only preflight (operator, NOT executed by GitHub or this document)**

PowerShell:
```powershell
wsl --status
wsl --version
wsl -l -v
```
Ubuntu:
```bash
cat /etc/os-release
uname -r
ps -p 1 -o comm=
systemctl is-system-running
python3 --version
git --version
df -h ~
```
`systemctl is-system-running` may return `degraded` due to unrelated services; inspect before changing settings. Systemd is supported in current WSL2; if disabled, plan an explicit later configuration change (`/etc/wsl.conf` with `[boot] systemd=true`) and a controlled WSL shutdown/restart. Do not change it as part of read-only preflight.

**O01 acceptance additions**
- [ ] Record Windows build, WSL version, Ubuntu release, Linux filesystem capacity and systemd state from sanitized operator output.
- [ ] Select service user, virtualenv location and systemd unit hardening; draft Windows scheduled-start command without installing it.
- [ ] Design backup/restore for SQLite with a transactional checkpoint, retention and manual recovery drill.
- [ ] Demonstrate Windows logon/start, sleep/shutdown and WSL termination recovery in isolated tests during O05.
- [ ] Obtain operator authorization before modifying Windows Task Scheduler, systemd, WSL config, credentials, network exposure or paid API access.
