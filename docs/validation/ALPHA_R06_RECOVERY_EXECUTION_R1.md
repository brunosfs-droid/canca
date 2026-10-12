# Alpha R06 — Recovery execution contract R1

Status: **NOT RUN**. This is an execution plan, not proof of restore.

## Independent restore acceptance

1. Pin main commit, migration checksums and source database/store snapshot SHA-256.
2. Provision an isolated target with **different** PostgreSQL instance, store root and credential scope; do not reuse production secrets.
3. Capture inventories of roles/grants/RLS/TLS and migration versions before and after restore.
4. Restore DB and artifact store as a matched pair. Reject mixed epochs, altered receipt hashes, missing files, unknown roles or permissions broadened by restore.
5. Verify old workspace lease/generation is invalid; only explicitly reauthorized identity may open a workspace. Check same IP/object IDs do not leak into a second workspace.
6. Execute read-only evidence verification, replay, rollback on injected failure, and isolated smoke tests.
7. Record timings, bytes transferred, hashes, PostgreSQL versions, RTO/RPO observations, errors, operator and independent reviewer.

## Automatic stop conditions

Unexpected network probing, secret exposure, relaxed RLS, missing audit records, inconsistent DB/store revisions, invalid checksums, stale token accepted or incorrect restoration scope.

## Acceptance

A PASS requires the target environment, command/output evidence, hashes, independent reviewer and successful negative tests. Existing synthetic same-cluster checks do not satisfy the independent cross-cluster gate. E0-08 remains NOT RUN until operated.

## Required failure injection and negative control

Repeat on a disposable target with (a) missing raw evidence, (b) corrupted evidence hash, (c) a revoked SQL role and (d) stale workspace generation. All must be denied without partial activation. Compare original and restored inventory counts, role grants, collection receipt digests and workspace revisions. Store evidence outside the public repository.
