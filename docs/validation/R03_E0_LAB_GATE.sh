#!/usr/bin/env bash
# E0 operator gate: verify authentic bundle bytes before running destructive
# PostgreSQL integration tests on an explicitly disposable lab database.
set -Eeuo pipefail
if [[ $# -ne 2 || -z "${1:-}" || -z "${2:-}" ]]; then
  echo "Usage: bash docs/validation/R03_E0_LAB_GATE.sh BUNDLE MANIFEST" >&2
  exit 2
fi
if [[ ! -f docs/validation/R03_E0_VERIFY_MANIFEST.py || ! -f docs/validation/R03_E0_PREFLIGHT.sh ]]; then
  echo "BLOCKED: run from repository root" >&2
  exit 2
fi
if [[ "${CANCA_E0_DISPOSABLE_DB:-}" != "YES" || -z "${CANCA_E0_EXPECTED_DB:-}" || -z "${CANCA_E0_LAB_ID:-}" ]]; then
  echo "BLOCKED: disposable DB confirmation, expected DB and lab identity are required" >&2
  exit 2
fi
python docs/validation/R03_E0_VERIFY_MANIFEST.py --bundle "$1" --manifest "$2"
echo "E0 bundle integrity verified; starting guarded disposable PostgreSQL preflight"
bash docs/validation/R03_E0_PREFLIGHT.sh
echo "E0 lab gate: preflight PASS. Real import/restore and operational sign-off still PENDING."
