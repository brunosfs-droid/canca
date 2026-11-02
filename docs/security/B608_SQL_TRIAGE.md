# Bandit B608 — SQL construction triage (2026-11-02)

Source: Bandit baseline from PR #281, 82 total findings; nine B608 medium-severity findings.
This review records the initial source-level assessment, **not** an assertion that every
SQL construction path has been proven safe.

| File | Original Bandit line(s) | Construction pattern | Assessment |
| --- | --- | --- | --- |
| persistence/P01_Assessment_Lifecycle.py | 76, 89, 108 | `EVENT_COLUMNS` is a module-level constant tuple; values use `%s` placeholders | Likely benign; test against malicious values |
| persistence/P01_Asset_Registry.py | 250, 347, 366 | Repeated `(kind=%s AND value=%s)` clauses or constant column tuples; values passed separately | Likely benign if the number of clauses is bounded and input structure validated |
| persistence/P01_Findings.py | 224 | Constant local column tuple; bound parameters | Likely benign |
| persistence/P01_Workspace.py | 205 | Table and column names selected from literal category allowlist; identifiers and pagination validated | Tested by `test_sql_security_regression.py` |
| persistence/P01_Workspace_Model.py | 190 | Repeated placeholder clauses from signal count; signal values passed separately | Review signal count bounds and input validation |

## Security requirements

- Never concatenate user-provided table names, column names, predicates or raw values into SQL.
- Preserve driver parameterization for values and explicit allowlists for identifiers.
- Keep all nine findings visible until per-path validation is sufficient.
- Avoid broad Bandit B608 suppression. If a suppression is eventually justified, scope it
  to a reviewed occurrence and link to evidence.
- Include workspace isolation and injection attempts in PostgreSQL integration tests.
- No production schema changes or network/database access in this PR.

## Follow-up

Add database-backed tests for all remaining B608 sites, including malformed signals,
long OR-clause lists and cross-workspace access. Consider SQL composition helpers only
when they reduce risk without destabilizing existing persistence contracts.
