#!/usr/bin/env bash
# NormClaim — upload → extract → FHIR → reconcile (requires running backend on BACKEND_URL).
# Usage: from repo root:  ./scripts/smoke_api.sh [path/to/file.pdf]
# Env: BACKEND_URL (default http://localhost:8000)

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${BACKEND_URL:-http://localhost:8000}"
PDF="${1:-$ROOT/test-data/discharge_simple.pdf}"

if [[ ! -f "$PDF" ]]; then
  echo "PDF not found: $PDF"
  echo "Usage: $0 [path/to/file.pdf]"
  exit 1
fi

echo "POST $BASE/api/documents (upload)"
RESP="$(curl -sS -F "file=@${PDF}" "$BASE/api/documents")"
DOC_ID="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['id'])" "$RESP")"
echo "document_id=$DOC_ID"

echo "POST $BASE/api/extract/$DOC_ID"
curl -sS -X POST "$BASE/api/extract/$DOC_ID" -o "$ROOT/test-data/.smoke_extract.json"
echo " (saved last response to test-data/.smoke_extract.json)"

echo "POST $BASE/api/fhir/$DOC_ID"
curl -sS -X POST "$BASE/api/fhir/$DOC_ID" -o "$ROOT/test-data/.smoke_fhir.json"
echo " (saved to test-data/.smoke_fhir.json)"

echo "POST $BASE/api/reconcile/$DOC_ID"
curl -sS -X POST "$BASE/api/reconcile/$DOC_ID" -o "$ROOT/test-data/.smoke_reconcile.json"
echo " (saved to test-data/.smoke_reconcile.json)"
echo "Smoke flow completed OK."
