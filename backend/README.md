# PRAMAAN backend

This backend now contains a runnable SIH demonstration slice:

```text
tender PDF upload/version
  -> deterministic candidate requirement extraction
  -> officer confirmation
  -> bidder document upload/hash/storage
  -> ML-1 OCR/classification/field extraction
  -> normalized mock source verification
  -> deterministic assessment
  -> officer decision
  -> hash-linked audit events
```

## Start the stack

For the selected managed deployment, follow
[`RENDER_VERCEL_S3_DEPLOYMENT.md`](../RENDER_VERCEL_S3_DEPLOYMENT.md). It uses
Render for FastAPI, PostgreSQL, and Tesseract, Vercel for the frontend, and a
private AWS S3 bucket for documents. The EC2 and Docker Compose paths remain
fallbacks in [`DEPLOYMENT.md`](../DEPLOYMENT.md).

Services:

- Frontend: `http://localhost`
- Backend API and Swagger: `http://localhost:8000/docs`
- Backend readiness: `http://localhost:8000/ready`
- ML service: `http://localhost:8001/health`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Local development stores documents on disk. The managed deployment stores both
tender and bidder documents in S3 and sends bidder-document bytes to ML-1 over
HTTPS. Set `PROCESSING_QUEUE_ENABLED=false` to use the explicit `/upload` then
`/{document_id}/process` route without Redis or a Celery worker.

See the managed deployment guide for the complete S3, Render, and Vercel setup,
service inventory, environment variables, and end-to-end check.

## Run locally without Docker

Create `backend/.env` from `.env.example`, start PostgreSQL, then run:

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload
```

Run ML-1 separately:

```bash
cd ml-services
../backend/.venv/bin/pip install -r requirements.txt
PYTHONPATH=. ../backend/.venv/bin/uvicorn main:app --port 8001
```

Tesseract must be installed for real OCR.

## Demonstrate the golden path

Use a text-based tender PDF containing a Udyam/MSME clause and an Udyam
certificate image:

```bash
./backend/scripts/demo_smoke.sh /path/to/tender.pdf /path/to/udyam.png
```

The script creates its own demo officer, tender, bidder, and bid. It confirms only
the extracted Udyam requirement, processes the certificate with ML-1, runs a
clearly labelled `MOCK` Udyam adapter, calculates the assessment, accepts it as an
officer, and prints a compact result.

## Supported deterministic demo rules

Requirements use version-ready JSON in `rule_config`.

Verification result:

```json
{
  "kind": "verification_status",
  "source": "UDYAM",
  "allowed_statuses": ["VERIFIED"],
  "on_unavailable": "REVIEW"
}
```

Extracted value:

```json
{
  "kind": "field_equals",
  "field": "enterprise_type",
  "allowed_values": ["Micro", "Small"],
  "on_missing": "REVIEW"
}
```

Evidence presence:

```json
{
  "kind": "evidence_present",
  "document_type": "oem_authorization_certificate",
  "on_missing": "FAIL"
}
```

Unconfirmed `CANDIDATE` requirements are deliberately excluded from assessments.
Only `CONFIRMED` and `ADDED_MANUALLY` requirements are evaluated.

## Current prototype boundaries

- Source runs are deterministic synthetic/mock scenarios and always disclose
  `mode=MOCK`.
- The standard document upload is asynchronous through Redis/Celery; the smoke
  script intentionally uses the synchronous compatibility path.
- Tender extraction uses page-aware deterministic keyword patterns; a dedicated
  tender LLM worker can replace it behind the same candidate contract.
- ML-1 extracts text directly from digital PDFs and OCRs raster images and
  image-only/scanned PDFs with Tesseract.
- S3-backed storage is implemented for private tender and bidder documents.
  Direct-browser signed uploads, official registry adapters, and production queue
  retry/dead-letter operations remain hardening milestones.

## Tests

Tests require a PostgreSQL database named `sih_project_test`:

```bash
cd backend
POSTGRES_PASSWORD=... .venv/bin/pytest -q
```

Migration/model drift check:

```bash
cd backend
POSTGRES_PASSWORD=... .venv/bin/alembic check
```
