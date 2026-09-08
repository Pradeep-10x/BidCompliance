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

For deployment, follow [`DEPLOYMENT.md`](../DEPLOYMENT.md). Its primary EC2
path uses native systemd services, Nginx, PostgreSQL, Redis, and Tesseract, so
Docker is not required. Docker Compose remains an optional local fallback.

Services:

- Frontend: `http://localhost`
- Backend API and Swagger: `http://localhost:8000/docs`
- Backend readiness: `http://localhost:8000/ready`
- ML service: `http://localhost:8001/health`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

In the native deployment, documents are stored under
`/var/lib/pramaan/documents` and shared with ML-1. The normal upload endpoint
submits processing work to Redis and a Celery worker. The explicit `/upload`
then `/{document_id}/process` route remains available for a predictable,
synchronous SIH stage demonstration.

See [`DEPLOYMENT.md`](../DEPLOYMENT.md) for the complete EC2 and Vercel setup,
service inventory, environment variables, HTTPS guidance, and update procedure.

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
- S3/MinIO-backed storage, official registry adapters, signed URLs, and production
  queue retry/dead-letter operations remain hardening milestones.

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
