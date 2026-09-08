#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 TENDER_PDF UDYAM_IMAGE [API_BASE_URL]" >&2
  exit 2
fi

tender_pdf=$1
udyam_image=$2
base_url=${3:-http://localhost:8000/api/v1}
run_id=$(date +%s)
email="demo-${run_id}@example.com"
password="Password123!"

token=$(curl -fsS -X POST "$base_url/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$email\",\"password\":\"$password\",\"full_name\":\"SIH Demo Officer\"}" >/dev/null \
  && curl -fsS -X POST "$base_url/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"$password\"}" | jq -r .access_token)

tender_id=$(curl -fsS -X POST "$base_url/tenders" \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  -d "{\"title\":\"CPCL SIH Demo Tender\",\"reference_number\":\"CPCL-DEMO-$run_id\"}" | jq -r .id)

curl -fsS -X POST "$base_url/tenders/$tender_id/documents" \
  -H "Authorization: Bearer $token" \
  -F "file=@$tender_pdf;type=application/pdf" >/dev/null

analysis=$(curl -fsS -X POST "$base_url/tenders/$tender_id/analyze" \
  -H "Authorization: Bearer $token")
requirement_id=$(jq -r '.candidates[] | select(.category == "MSME_REGISTRATION") | .id' <<<"$analysis" | head -n 1)
if [ -z "$requirement_id" ]; then
  echo "The tender analyzer did not find an Udyam/MSME requirement." >&2
  exit 1
fi

curl -fsS -X POST "$base_url/tenders/$tender_id/requirements/confirm" \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  -d "{\"requirement_ids\":[\"$requirement_id\"]}" >/dev/null

bidder_id=$(curl -fsS -X POST "$base_url/bidders" \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  -d '{"legal_name":"ABC Industrial Systems Pvt Ltd"}' | jq -r .id)
bid_id=$(curl -fsS -X POST "$base_url/tenders/$tender_id/bids" \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  -d "{\"bidder_id\":\"$bidder_id\"}" | jq -r .id)
document_id=$(curl -fsS -X POST "$base_url/tenders/$tender_id/bids/$bid_id/documents/upload" \
  -H "Authorization: Bearer $token" \
  -F "file=@$udyam_image" | jq -r .id)

processing=$(curl -fsS -X POST "$base_url/tenders/$tender_id/bids/$bid_id/documents/$document_id/process" \
  -H "Authorization: Bearer $token")
verification=$(curl -fsS -X POST "$base_url/tenders/$tender_id/bids/$bid_id/verifications/run" \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  -d '{"source":"UDYAM","scenario":"MATCH"}')
assessment=$(curl -fsS -X POST "$base_url/tenders/$tender_id/bids/$bid_id/assessments/run" \
  -H "Authorization: Bearer $token")
assessment_id=$(jq -r .id <<<"$assessment")
decision=$(curl -fsS -X POST "$base_url/tenders/$tender_id/bids/$bid_id/assessments/$assessment_id/decisions" \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  -d '{"action":"ACCEPT"}')
audit_count=$(curl -fsS "$base_url/tenders/$tender_id/audit" \
  -H "Authorization: Bearer $token" | jq length)

jq -n \
  --arg tender_id "$tender_id" \
  --arg bid_id "$bid_id" \
  --arg document_status "$(jq -r .processing_status <<<"$processing")" \
  --arg source_mode "$(jq -r .mode <<<"$verification")" \
  --arg verification_status "$(jq -r .status <<<"$verification")" \
  --arg mandatory_gate "$(jq -r .mandatory_gate_status <<<"$assessment")" \
  --arg score "$(jq -r .compliance_score <<<"$assessment")" \
  --arg risk "$(jq -r .risk_level <<<"$assessment")" \
  --arg decision "$(jq -r .action <<<"$decision")" \
  --argjson audit_events "$audit_count" \
  '{tender_id:$tender_id,bid_id:$bid_id,document_status:$document_status,source_mode:$source_mode,verification_status:$verification_status,mandatory_gate:$mandatory_gate,compliance_score:$score,risk:$risk,decision:$decision,audit_events:$audit_events}'
