#!/usr/bin/env bash
# NormClaim backend smoke flow:
# health -> config -> auth/session -> upload -> extract -> get extraction
# Usage: from repo root: ./scripts/smoke_api.sh [path/to/file.pdf]
# Env:
#   BACKEND_URL (default http://localhost:8000)
#   ACCESS_TOKEN (required; Supabase user access token)

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${BACKEND_URL:-http://localhost:8000}"
PDF="${1:-$ROOT/test-data/discharge_simple.pdf}"
TOKEN="${ACCESS_TOKEN:-}"

if [[ ! -f "$PDF" ]]; then
  echo "PDF not found: $PDF"
  echo "Usage: $0 [path/to/file.pdf]"
  exit 1
fi

if [[ -z "$TOKEN" ]]; then
  echo "ACCESS_TOKEN is required for protected endpoints."
  exit 1
fi

AUTH_HEADER="Authorization: Bearer ${TOKEN}"

echo "GET $BASE/health"
curl -sS "$BASE/health" -o "$ROOT/test-data/.smoke_health.json"
echo " (saved to test-data/.smoke_health.json)"

echo "GET $BASE/api/config/public"
curl -sS "$BASE/api/config/public" -o "$ROOT/test-data/.smoke_config.json"
echo " (saved to test-data/.smoke_config.json)"

echo "GET $BASE/api/auth/session"
curl -sS -H "$AUTH_HEADER" "$BASE/api/auth/session" -o "$ROOT/test-data/.smoke_session.json"
echo " (saved to test-data/.smoke_session.json)"

echo "POST $BASE/api/documents (upload)"
RESP="$(curl -sS -H "$AUTH_HEADER" -F "consent_obtained=true" -F "file=@${PDF}" "$BASE/api/documents")"
DOC_ID="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['document_id'])" "$RESP")"
echo "document_id=$DOC_ID"

echo "POST $BASE/api/extract/$DOC_ID"
curl -sS -H "$AUTH_HEADER" -X POST "$BASE/api/extract/$DOC_ID" -o "$ROOT/test-data/.smoke_extract.json"
echo " (saved last response to test-data/.smoke_extract.json)"

echo "GET $BASE/api/extract/$DOC_ID"
curl -sS -H "$AUTH_HEADER" "$BASE/api/extract/$DOC_ID" -o "$ROOT/test-data/.smoke_extract_get.json"
echo " (saved to test-data/.smoke_extract_get.json)"

python3 - <<'PY' "$ROOT/test-data/.smoke_extract_get.json"
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
diag = len(data.get("diagnoses", []))
proc = len(data.get("procedures", []))
med = len(data.get("medications", []))
if diag == 0 and proc == 0 and med == 0:
    raise SystemExit("Extraction appears empty: diagnoses/procedures/medications are all zero")
print(f"Extraction counts -> diagnoses={diag}, procedures={proc}, medications={med}")
PY

echo "Smoke flow completed OK."
