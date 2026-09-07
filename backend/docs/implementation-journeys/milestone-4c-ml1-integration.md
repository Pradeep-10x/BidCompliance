# Milestone 4C: Backend Worker to ML-1 Integration

## 1. Goal of Milestone 4C

Milestone 4C connects the backend's queued document-processing jobs to the ML-1 document-intelligence contract.

The backend worker now:

1. Loads a queued `ProcessingJob`.
2. Loads its associated `Document` and `Bid`.
3. Constructs the established ML-1 request payload.
4. Calls the configured ML-1 HTTP endpoint.
5. Validates the response envelope and identity fields.
6. Persists successful ML output separately from the job record.
7. Updates job state truthfully.
8. Leaves the Document in a truthful state because ML-1 completion is not full pipeline completion.

The API layer continues to enqueue work only. It does not call ML-1 directly.

## 2. Starting State from Milestones 4A and 4B

Milestone 4A established real document ingestion:

- Multipart file uploads
- MIME and magic-byte validation
- SHA-256 hashing from actual bytes
- Generated storage keys
- Local storage abstraction
- Document metadata persistence
- Initial `PENDING` document status

Milestone 4B established backend job orchestration:

- Celery + Redis as the intended queue stack
- `ProcessingJob` persistence
- Generic pipeline stages
- Bounded attempts and retry metadata
- Queue publisher abstraction
- Initial classification job creation after upload
- Ownership-scoped job status endpoints

Milestone 4C adds the worker-side ML-1 execution path without implementing ML-1 internals.

## 3. Backend Worker Entry Point

The Celery task is defined in:

```text
app/workers/processing.py
```

Task name:

```text
app.workers.processing.process_document
```

The task receives a job ID, opens an async SQLAlchemy session, constructs `ML1Client`, and delegates execution to `execute_classification_job` in `app/services/ml1_worker_service.py`.

The worker loads job, Document, and Bid records through database relationships. User-facing API routes never invoke the ML client.

## 4. ML-1 Endpoint Used

The worker calls the combined ML-1 document-intelligence endpoint:

```text
POST {ML1_BASE_URL}/ml/v1/document-intelligence
```

`ML1_BASE_URL` is read from the trusted backend settings configuration. It is not accepted from users, jobs, or API request bodies.

HTTP behavior is implemented in `app/services/ml1_client.py` using async HTTPX with configured connect, read, and total timeouts.

## 5. Exact Request Payload Contract

The worker forwards the established payload without renaming fields:

```json
{
  "job_id": "job_001",
  "bid_id": "bid_001",
  "document_id": "doc_001",
  "page_id": null,
  "page_number": 1,
  "file_type": "image/png",
  "image_path": "documents/object-key.png",
  "document_hash": "sha256-digest",
  "callback_url": null,
  "pipeline_stage": "classification"
}
```

The payload is built from the stored `ProcessingJob` payload and backend-owned Document/Bid data. The worker does not accept an arbitrary ML URL or callback URL from a user.

## 6. ML Response Validation and Identity Checks

The ML-1 response schema validates the expected envelope:

- `job_id`
- `bid_id`
- `document_id`
- `page_id`
- `page_number`
- `module`
- `model_name`
- `model_version`
- `status`
- `processing_time_ms`
- `result`
- `errors`
- `created_at`

The worker rejects responses when:

- `job_id` does not match the submitted job
- `bid_id` does not match the associated Bid
- `document_id` does not match the associated Document
- `page_id` does not match the submitted page ID
- `page_number` does not match the submitted page number
- `status` is not recognized
- The JSON envelope or field types are invalid

A response with `status="failed"` is not treated as a successful result.

## 7. MLProcessingResult Model and Migration

ML results are stored separately from `ProcessingJob` in:

```text
app/models/ml_processing_result.py
```

The result stores:

- `job_id`
- `document_id`
- `bid_id`
- ML module/model/version metadata
- ML status
- processing time
- structured `result` JSONB
- structured `errors` JSONB
- timestamps

Migration:

```text
alembic/versions/004_ml_processing_results.py
```

The table has a unique constraint on `job_id`, preventing duplicate final result rows for the same processing job.

No document bytes are stored in the ML result table or PostgreSQL.

## 8. ProcessingJob State Transitions

Successful execution:

```text
QUEUED
  -> PROCESSING
  -> COMPLETED
```

When processing begins, the worker records `started_at` and increments `attempt_count`.

Transport failures, timeouts, HTTP errors, invalid JSON, invalid schemas, ML error responses, and identity mismatches result in:

```text
QUEUED
  -> PROCESSING
  -> FAILED
```

The existing bounded retry model remains responsible for deciding whether a failed job may be submitted again. Completed jobs are idempotent: re-executing the same job returns without another ML call.

## 9. Failure, Timeout, and Invalid-Response Behavior

The ML-1 client converts HTTPX transport, connection, timeout, and HTTP status failures into backend integration errors.

The worker records the error on `ProcessingJob`, leaves `completed_at` unset, and does not persist an accepted ML result for failed or invalid responses.

Invalid response identity is treated as a failure even when the HTTP request itself succeeds. This prevents an ML response for another job, Document, or Bid from being trusted.

## 10. Idempotency Behavior

Idempotency is enforced at two levels:

1. Completed `ProcessingJob` records are not submitted to ML-1 again.
2. `MLProcessingResult.job_id` is unique and the persistence service checks for an existing result before inserting.

The integration tests verify that repeating a completed execution makes only one mocked ML call and leaves exactly one result row.

## 11. Why Document Remains PENDING After ML-1

ML-1 performs document intelligence for one pipeline stage. It does not represent completion of the entire backend processing workflow.

Therefore, the worker updates `ProcessingJob` to `COMPLETED` after a successful ML-1 response but intentionally does not mark `Document.processing_status` as `COMPLETED`. The Document remains `PENDING` until a later workflow defines the complete document-processing state transition.

This prevents the API from falsely claiming that all processing, evidence, and downstream stages have completed.

## 12. Mocked HTTP Testing Strategy

`tests/test_ml1_integration.py` uses HTTPX `MockTransport` and injected `AsyncClient` instances. Tests do not contact a live ML-1 service and do not require a running Redis service.

The existing client, database, cleanup, authentication, temporary storage, and job publisher fixtures are reused. The upload setup uses a recording publisher and temporary filesystem storage.

The tests cover:

- successful worker execution
- exact request payload
- response identity validation
- matching and mismatched job/document/bid IDs
- ML error responses
- connection failures
- timeouts
- invalid JSON
- invalid response schemas
- result persistence
- duplicate-result prevention
- truthful failed-job behavior

## 13. Test Results

Focused ML-1 integration tests:

```text
12 passed
```

Full backend suite:

```text
106 passed
```

The suite reports two existing Starlette deprecation warnings:

- `HTTP_413_REQUEST_ENTITY_TOO_LARGE`
- `HTTP_422_UNPROCESSABLE_ENTITY`

These warnings are unrelated to ML-1 behavior and do not fail the suite.

## 14. Downstream Impact

Milestone 4C creates the integration boundary needed for later stages:

```text
Document
  -> ML-1 document intelligence
  -> ML-2 processing
  -> ML-3 reasoning
  -> evidence persistence
  -> backend deterministic rule engine
  -> Procurement Officer audit and decision
```

ML-1 results now have a durable job/document/Bid association and a structured JSON persistence location. Future ML-2 and ML-3 workers can consume the stored result and produce their own stage-specific records without changing the initial upload or queue contract.

The result metadata and job transitions also provide an audit trail for execution attempts, failures, model metadata, and processing timing.

## 15. Explicit Non-Goals

Milestone 4C does **not** implement:

- ML-1 internals
- OCR or classification algorithms
- Compliance scoring
- Qualification or disqualification
- Fraud decisions
- External government verification
- Final procurement decisions
- ML-2 or ML-3 services
- Deterministic rule evaluation
- Evidence adjudication

The backend only orchestrates the request, validates the response envelope, persists the ML result, and maintains truthful job state.

## 16. Changed Files

Milestone 4C added or updated:

- `.env.example`
- `app/core/config.py`
- `app/models/__init__.py`
- `app/models/ml_processing_result.py`
- `app/schemas/ml1.py`
- `app/services/ml1_client.py`
- `app/services/ml1_worker_service.py`
- `app/workers/processing.py`
- `alembic/versions/004_ml_processing_results.py`
- `tests/test_ml1_integration.py`

The existing ProcessingJob, queue, Document, and upload implementation remain the foundation for this integration.

## 17. Intentionally Deferred Work

The following work remains outside Milestone 4C:

- ML-1 implementation and model hosting
- ML-2 integration
- ML-3 integration
- PDF/page splitting and rendering workflows
- Evidence-specific APIs and adjudication
- Deterministic compliance rule execution
- Compliance scoring
- Bidder qualification/disqualification
- Fraud analysis
- Final Procurement Officer decision workflows
- Callback endpoints and asynchronous ML result callbacks
- Production worker deployment and operational monitoring
- Advanced retry scheduling and dead-letter queue handling
