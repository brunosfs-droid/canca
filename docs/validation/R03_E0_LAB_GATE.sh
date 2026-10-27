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
# The integration suite is destructive on the disposable database only.
# Re-check the source evidence after it completes, so accidental edits made
# during the test window are not mistaken for a stable E0 input.
python docs/validation/R03_E0_VERIFY_MANIFEST.py --bundle "$1" --manifest "$2"
echo "E0 lab gate: preflight PASS. Real import/restore and operational sign-off still PENDING."
# Explicitly prevent this synthetic/preflight gate from being treated as full
# operational E0 sign-off, regardless of the process exit status.
if [[ -n "${CANCA_E0_RESULT_PATH:-}" ]]; then
  if [[ -e "${CANCA_E0_RESULT_PATH}" ]]; then
    echo "BLOCKED: refusing to overwrite prior E0 result file" >&2
    exit 2
  fi
  CANCA_E0_RESULT_PATH="${CANCA_E0_RESULT_PATH}" python - <<'PY'
import datetime
import json
import os
from pathlib import Path

target = Path(os.environ["CANCA_E0_RESULT_PATH"])
result = {
    "type": "canca.r03.e0.lab_gate_result.v1",
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "preflight": "passed",
    "bundle_integrity_before_and_after": "passed",
    "real_collection_import": "pending",
    "operational_recovery": "pending",
    "operational_backup_restore": "pending",
    "operational_e0": "pending",
}
with target.open("x", encoding="utf-8") as output:
    json.dump(result, output, indent=2, sort_keys=True)
    output.write("\\n")
PY
fi
