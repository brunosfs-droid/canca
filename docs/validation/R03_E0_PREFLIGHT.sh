#!/usr/bin/env bash
# R03 automated E0 preflight. Destructive tests: disposable database ONLY.
set -Eeuo pipefail

if [[ "${CANCA_E0_DISPOSABLE_DB:-}" != "YES" ]]; then
  echo "BLOCKED: set CANCA_E0_DISPOSABLE_DB=YES for an isolated, disposable PostgreSQL database." >&2
  exit 2
fi
for name in PGHOST PGDATABASE PGUSER; do
  if [[ -z "${!name:-}" ]]; then
    echo "BLOCKED: missing $name" >&2
    exit 2
  fi
done
if [[ -z "${CANCA_E0_EXPECTED_DB:-}" || "${PGDATABASE}" != "${CANCA_E0_EXPECTED_DB}" ]]; then
  echo "BLOCKED: set CANCA_E0_EXPECTED_DB to the exact disposable PGDATABASE name." >&2
  exit 2
fi
if [[ "${PGDATABASE}" == "postgres" || "${PGDATABASE}" == "template0" || "${PGDATABASE}" == "template1" ]]; then
  echo "BLOCKED: PostgreSQL maintenance database cannot be used for E0." >&2
  exit 2
fi
for name in PGSERVICE PGSERVICEFILE PGHOSTADDR PGOPTIONS PGDATABASE_URI; do
  if [[ -n "${!name:-}" ]]; then
    echo "BLOCKED: $name must be unset for E0 preflight" >&2
    exit 2
  fi
done
if [[ ! -f persistence/P01_PostgreSQL.py || ! -f tests/test_interface_writer_postgres.py ]]; then
  echo "BLOCKED: run from repository root" >&2
  exit 2
fi

# The integration suite drops/recreates canca schema in setUp.
# Never point this at a shared, staging, or production database.
sha="$(git rev-parse HEAD)"
echo "R03 automated preflight"
echo "commit=$sha"
echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "database and credentials intentionally not printed"
export CANCA_TEST_WORKSPACE_POSTGRES=1

python -m unittest discover -s tests -p 'test_interface*postgres.py' -v
echo "R03 automated preflight: PASS"
echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Operational E0 bundle validation, real imports, recovery and restore remain PENDING."
