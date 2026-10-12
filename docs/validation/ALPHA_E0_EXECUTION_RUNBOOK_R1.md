# Alpha E0 — Operator runbook R1

**NOT RUN. NO-GO.** Preparation only; never infer LAB PASS from CI.

## Preconditions

- Pin candidate commit, EVE-NG topology export/digest, operating system images/versions, operator approval of private IPv4 scopes, and UTC time.
- Verify correct DNS/time, routing, storage, available snapshots and restricted evidence directory.
- Credentials reside only in the approved Secret Provider or local operator credential vault; never in Git, screenshots, console logs or evidence manifest.
- Restrict outbound networks; have a stop switch and rollback snapshot verified before AUTH/FULL runs.

## Execution order

1. E0-01 offline package/import and integrity/sidecar rejection.
2. E0-04 unreachable/denied targets fail closed before authenticated scans.
3. E0-05 workspace A/B isolation (same IP/object, store, exports, cache, grants).
4. E0-06 cancel/drain/lease and stale-generation rejections; ensure child processes are reaped.
5. E0-02 WinRM and E0-03 SSH on **explicitly authorized** LAB targets only.
6. E0-07 import/reconciliation and history from verified evidence.
7. E0-08 recovery from matched DB/store snapshot.
8. E0-09 audit/redaction and E0-10 rollback/reproducibility.

For each gate save test ID, exact commit, environment version, UTC, command (redacted), actual outcome, SHA-256 evidence hash, independent reviewer and issue reference. Record FAIL/BLOCKED/NOT RUN accurately; do not set PASS based solely on automation. Stop immediately on unintended probing, secret disclosure, workspace leakage or cancellation failure.
