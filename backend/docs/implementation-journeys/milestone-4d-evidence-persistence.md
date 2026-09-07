# Milestone 4D: ML-1 Result → Evidence / Extracted Facts Persistence

## 1. Goal of Milestone 4D

Milestone 4D turns successful ML-1 extraction output into durable, authoritative, traceable `Evidence` records in PostgreSQL.

The backend worker now:
1. Receives and validates ML-1 document intelligence responses.
2. Persists `MLProcessingResult`.
3. Validates each extracted field from `result.fields`.
4. Generates authoritative, non-colliding backend evidence identifiers while preserving source ML references.
5. Persists valid fields as `Evidence` records linked to the Document and `MLProcessingResult`.
6. Preserves partial-ingestion errors in `ml_result.errors` as structured entries without mutating the ML status.
7. Commits the result, evidence records, and job completion transactionally.
8. Exposes read-only, ownership-scoped evidence endpoints for the frontend.

## 2. Evidence Data Model

The `evidence` table stores extracted facts and their provenance:

- `id`: UUID primary key.
- `evidence_id`: String(150), unique, authoritative backend identifier (`ev_<doc_hex>_<field>_<uuid_hex>`).
- `source_evidence_id`: String(150), nullable, ML-supplied reference identifier (e.g., `ev_udyam_name_001`).
- `document_id`: UUID foreign key (`documents.id`, ondelete `CASCADE`).
- `ml_result_id`: UUID foreign key (`ml_processing_results.id`, ondelete `CASCADE`).
- `field_name`: String(150), indexed.
- `value`: Text, nullable.
- `value_normalized`: Text, nullable.
- `confidence`: Float, nullable.
- `page_number`: Integer, nullable.
- `bounding_box`: JSONB, nullable.
- `source_text`: Text, nullable.
- `extraction_method`: String(100), nullable.
- `evidence_type`: String(50), default `ML_EXTRACTION`.
- `created_at`, `updated_at`: Timestamps with time zone.

Alembic migration: `005_evidence.py`.

No document bytes are stored in the evidence table or PostgreSQL.

## 3. Ingestion & Transactional Idempotency

- Ingestion occurs in `app/services/evidence_service.py` via `ingest_evidence_from_ml_result`.
- If evidence rows already exist for `ml_result_id`, the function returns them without duplicate inserts.
- Unique constraints on `evidence_id` and `(ml_result_id, evidence_id)` prevent race-condition duplicates.
- All operations (saving `MLProcessingResult`, writing `Evidence`, logging partial ingestion errors, updating `ProcessingJob`) execute in a single database transaction.

## 4. Error Handling Policy

- If an item in `fields` lacks a valid non-empty string name, has an invalid confidence out of `[0.0, 1.0]`, or an invalid page number `< 1`:
  - The corrupted item is rejected.
  - A structured error entry `{"code": "MALFORMED_FIELD", "detail": "...", "raw": ...}` is appended to `ml_result.errors`.
  - ML status remains unmodified (preserving the upstream contract).
  - All valid fields in the same payload are saved.

## 5. API Layer

Read-only endpoints nested under documents:

```text
GET /api/v1/tenders/{tender_id}/bids/{bid_id}/documents/{document_id}/evidence
GET /api/v1/tenders/{tender_id}/bids/{bid_id}/documents/{document_id}/evidence/{evidence_id}
```

- Path `{evidence_id}` resolves by UUID, authoritative `evidence_id`, or `source_evidence_id`.
- Mismatched parent/child entities return `404 Not Found`.
- POST and PATCH methods are not implemented (return `405 Method Not Allowed`).
