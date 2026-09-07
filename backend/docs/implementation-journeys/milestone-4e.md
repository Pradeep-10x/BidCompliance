# Milestone 4E: Deterministic Requirement Evaluation & Persistence

## 1. Goal of Milestone 4E

Milestone 4E builds the deterministic evaluation engine and persistence foundation for evaluating tender requirements against persisted ML-1 evidence without hard-coding tender rules into ML or making premature bid qualification decisions.

The backend now:
1. Loads persisted `Evidence` records across documents submitted for a `Bid`.
2. Evaluates each `Requirement.rule_config` using a pure, deterministic evaluator.
3. Implements strict candidate selection and confidence semantics across multiple evidence extractions.
4. Records structured evaluations (`RequirementEvaluation`) in PostgreSQL with full explainability and provenance.
5. Preserves idempotency on repeated evaluations.
6. Enforces tenant, tender, bid, and requirement ownership scoping on all evaluation endpoints.
7. Leaves `Bid.status` unmodified (no premature qualification/disqualification).

## 2. Architectural Boundary

- **Backend Owns**:
  - Deterministic requirement rule execution.
  - Evaluation persistence and retrieval.
  - Provenance linking evaluation results to exact evidence records and documents.
  - Ownership protection and RBAC.
  - Auditability and explainability.

- **ML Owns**:
  - OCR, classification, and field extraction.
  - Bounding boxes, source text, confidence scores, and extraction methods.

- **ML Must NOT**:
  - Decide bid qualification/disqualification.
  - Implement tender eligibility rules.
  - Calculate compliance scores.
  - Fabricate official validity claims.

## 3. Rule Config Specification

Requirements specify evaluation rules via `Requirement.rule_config` (JSONB):

```json
{
  "target_field": "gstin",
  "operator": "EQUALS",
  "expected_value": "09ABCDE1234F1Z5",
  "expected_values": ["09ABCDE1234F1Z5", "07XYZAB9876C1Z2"],
  "min_confidence": 0.85,
  "use_normalized": false,
  "case_sensitive": false,
  "document_type": "GST_CERTIFICATE"
}
```

### Supported Deterministic Operators

- `EXISTS`: Verifies target field evidence exists (and meets `min_confidence` if specified).
- `EQUALS` / `EQ`: Checks equality against `expected_value` (default case-insensitive).
- `NOT_EQUALS` / `NEQ`: Checks inequality against `expected_value`.
- `IN`: Checks if extracted value matches any element in `expected_values`.
- `CONTAINS`: Checks substring containment.
- `STARTS_WITH`: Checks prefix match.
- `REGEX` / `MATCHES`: Compiles regex pattern safely and searches extracted value. Invalid regex returns `ERROR`.
- `GT`, `GTE`, `LT`, `LTE`: Numeric comparisons parsing numeric values from extracted text. Non-numeric values return `ERROR`.

## 4. Multiple Evidence Candidate Selection Policy

When evaluating a requirement against bid documents:
1. Filter evidence by `target_field`.
2. If `document_type` is specified in `rule_config`, filter by `document.document_type`.
3. If no matching-field candidates exist: return `MISSING_EVIDENCE`.
4. If matching-field candidates exist, check `min_confidence`:
   - If ALL matching candidates fall below `min_confidence`: return `LOW_CONFIDENCE`.
   - Do not mark as `NON_COMPLIANT` simply due to low confidence.
5. Evaluate all eligible candidates against the operator:
   - If **ANY** eligible candidate satisfies the operator: return `COMPLIANT` and link `evidence_id` to that satisfying record.
   - If eligible candidates exist but **NONE** satisfy the operator: return `NON_COMPLIANT`.
6. Candidate IDs considered are recorded in `details.candidate_evidence_ids` for complete explainability.

## 5. Confidence Semantics

- **No target-field evidence**: `MISSING_EVIDENCE`
- **Evidence exists but all candidates fail `min_confidence`**: `LOW_CONFIDENCE`
- **Confidence is sufficient but value fails operator**: `NON_COMPLIANT`
- **At least one sufficient-confidence candidate satisfies operator**: `COMPLIANT`
- **Invalid rule configuration / bad operator / unparseable numeric / bad regex**: `ERROR`

## 6. Persistence & Data Model

Table `requirement_evaluations`:
- `id`: UUID primary key.
- `tender_id`: UUID FK (`tenders.id`, ondelete `CASCADE`).
- `bid_id`: UUID FK (`bids.id`, ondelete `CASCADE`).
- `requirement_id`: UUID FK (`requirements.id`, ondelete `CASCADE`).
- `evidence_id`: UUID FK (`evidence.id`, ondelete `SET NULL`), nullable.
- `status`: String(50), indexed (`COMPLIANT`, `NON_COMPLIANT`, `MISSING_EVIDENCE`, `LOW_CONFIDENCE`, `ERROR`).
- `is_mandatory`: Boolean.
- `target_field`: String(150), nullable.
- `extracted_value`: Text, nullable.
- `confidence`: Float, nullable.
- `reason`: Text.
- `details`: JSONB (operator, expected value, candidate list, comparison value, etc.).
- `created_at`, `updated_at`: Timestamps with time zone.
- `UniqueConstraint("bid_id", "requirement_id")`: Idempotent upserts on repeated evaluation.

Alembic migration: `alembic/versions/006_requirement_evaluations.py`.

## 7. Provenance & Immutability

- `RequirementEvaluation.evidence_id` links directly to the specific `Evidence` record that satisfied the requirement.
- Immutability guarantees:
  - `Requirement` and `Requirement.rule_config` are never mutated.
  - `Evidence` rows are never mutated.
  - `Bid.status` remains unchanged (`SUBMITTED`).

## 8. API Layer

Added to `app/api/v1/endpoints/bids.py`:
- `POST /api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations`: Triggers deterministic evaluation and returns results.
- `GET /api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations`: Lists stored evaluations.
- `GET /api/v1/tenders/{tender_id}/bids/{bid_id}/evaluations/{requirement_id}`: Retrieves single evaluation.

Scoping:
- Tender exists → Bid belongs to Tender → Requirement belongs to Tender.
- Any mismatch returns `404 Not Found`.
- Unauthenticated requests return `401 Unauthorized`.

## 9. Testing & Results

- **Focused Test Suite** (`tests/test_evaluations.py` + `tests/test_evidence.py`):
  - **45 passed** in 20.98s.
- **Full Backend Suite**:
  - **151 passed** in 88.52s.
  - 0 failures, 0 errors.
  - 2 pre-existing Starlette deprecation warnings.

## 10. Limitations & Future Work

- Milestone 4E handles requirement-level evaluation only.
- Milestone 5 / future milestones will compute tender-level compliance aggregates, handle Procurement Officer adjudication, and execute final bid qualification decisions.
