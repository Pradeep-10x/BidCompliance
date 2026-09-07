# Milestone 4A: Document File Upload and Storage

## Milestone Goal

Milestone 4A turns the existing bid-scoped Document API from metadata-only creation into a real multipart file-ingestion flow:

```text
Frontend
  -> multipart upload
  -> backend validation
  -> SHA-256 hashing
  -> object storage
  -> Document metadata record
  -> PENDING processing status
```

The existing Document model is reused. PostgreSQL stores document metadata, while the uploaded bytes are stored by the storage adapter.

## Multipart Upload Contract

Document creation is a single multipart endpoint:

```text
POST /api/v1/tenders/{tender_id}/bids/{bid_id}/documents
```

Multipart fields:

- `file`: required uploaded file
- `document_type`: optional form field, default `GENERAL`

The former JSON metadata-only POST contract was replaced rather than maintained as a second creation path. Client-provided `content_hash` and `storage_path` are not accepted as upload metadata.

Existing read and metadata-update operations remain available:

```text
GET   /api/v1/tenders/{tender_id}/bids/{bid_id}/documents
GET   /api/v1/tenders/{tender_id}/bids/{bid_id}/documents/{document_id}
PATCH /api/v1/tenders/{tender_id}/bids/{bid_id}/documents/{document_id}
```

All routes require an authenticated active user and preserve tender-to-bid-to-document ownership checks.

## Supported File Types

The MVP accepts:

- `application/pdf`
- `image/png`
- `image/jpeg`
- `image/jpg`

Both the declared MIME type and the file signature are checked. Unsupported MIME types return `415`, while a signature mismatch returns `400`.

## MIME and Magic-Byte Validation

The upload route maps supported MIME types to expected signatures:

- PDF: `%PDF-`
- PNG: PNG signature bytes
- JPEG/JPG: JPEG signature bytes

The file stream is rewound after the header check so the storage service hashes and writes the complete upload.

Empty uploads are rejected with `400`.

## Maximum Upload Size

`MAX_UPLOAD_SIZE_BYTES` is configurable through the existing Pydantic settings mechanism. The default is 10 MiB:

```text
MAX_UPLOAD_SIZE_BYTES=10485760
```

The local adapter streams the file in chunks and rejects an upload as soon as it exceeds the configured limit with `413`.

## SHA-256 from Actual Bytes

The storage service calculates SHA-256 while writing the uploaded bytes. The resulting hexadecimal digest is assigned to `Document.content_hash`.

The client cannot provide or override the hash. The persisted hash is exactly 64 hexadecimal characters and is derived from the actual upload rather than from the filename or request metadata.

`file_size_bytes` is also calculated from the bytes received by the storage service.

## Safe Generated Storage Keys

The backend generates an object key using a UUID and a permitted extension under the `documents/` prefix. The client cannot select the storage path.

The original filename is normalized only for metadata:

- path separators are removed
- control characters are removed
- path traversal components are not retained
- the normalized name is length-limited

Uploaded filenames are never used directly as filesystem paths. The storage adapter also resolves and validates paths beneath its configured root before writing or deleting objects.

## Local Filesystem Storage Abstraction

No MinIO or S3 integration was configured in the existing project, so Milestone 4A introduces a small storage abstraction and a local development adapter:

- `StorageService` defines `store` and cleanup `delete` operations.
- `LocalFileStorage` writes objects beneath a configured local root.
- `StoredObject` returns the generated key, calculated hash, and byte count.
- The route depends on the abstraction rather than embedding filesystem behavior in the route handler.

Storage settings are environment-configurable:

- `STORAGE_BACKEND`
- `STORAGE_LOCAL_ROOT`
- `STORAGE_ENDPOINT`
- `STORAGE_ACCESS_KEY`
- `STORAGE_SECRET_KEY`
- `STORAGE_BUCKET`
- `STORAGE_SECURE`
- `MAX_UPLOAD_SIZE_BYTES`

The current implementation uses the local backend. The endpoint/access-key/secret/bucket/secure settings provide configuration placeholders for a future S3-compatible adapter without hard-coding credentials or infrastructure into routes.

## PostgreSQL Stores Metadata Only

The Document database record stores:

- bid association
- normalized original filename
- document type
- calculated content hash
- generated storage key
- calculated file size
- MIME type
- processing status
- timestamps

The actual document bytes are not inserted into PostgreSQL. They are written to the configured storage adapter.

## Processing Status

Every new upload begins with the existing model default:

```text
PENDING
```

The upload flow does not transition documents to `PROCESSING`, `COMPLETED`, or `FAILED`. No processing job is created in this milestone.

## Immutable Fields

PATCH continues to allow only safe metadata fields already established by Milestone 3D:

- `original_filename`
- `document_type`
- `file_size_bytes`
- `mime_type`

The following cannot be changed through PATCH:

- `bid_id`
- `content_hash`
- `storage_path`
- `processing_status`

The nested tender and bid URL determine ownership; the client cannot move a document to another bid.

## Upload Failure Cleanup

The local storage adapter removes a partially written file if streaming fails, the upload is empty, or the maximum size is exceeded.

If object storage succeeds but the database commit fails, the document service rolls back the database session and asks the storage adapter to delete the just-uploaded object. This avoids leaving an orphaned metadata record or stored object for the normal failure path.

## Test Strategy

Tests reuse the existing client, authentication, database, cleanup, and async test fixtures. Document tests override the storage dependency with `LocalFileStorage(tmp_path)`, so each test receives an isolated temporary storage directory and no repository upload files or live cloud service are required.

The final Document test module contains **17 tests** covering:

- authenticated upload
- unauthenticated rejection
- nonexistent tender and bid handling
- cross-tender and cross-bid isolation
- MIME and magic-byte validation
- empty uploads
- maximum size enforcement
- SHA-256 calculation from actual bytes
- exact 64-character hashes
- calculated file size
- normalized filename metadata
- generated storage paths
- client hash/path rejection
- `PENDING` status
- partial metadata PATCH
- immutable status/hash/path/ownership fields
- storage failure cleanup
- actual object existence in temporary storage
- list, pagination, get, and missing-document behavior

The focused result was:

```text
17 passed
```

The full backend suite result was:

```text
83 passed
```

## Existing Deprecation Warnings

The test suite continues to report two Starlette deprecation warnings for status constants:

- `HTTP_413_REQUEST_ENTITY_TOO_LARGE`
- `HTTP_422_UNPROCESSABLE_ENTITY`

They do not cause test failures and are outside the upload/storage behavior introduced here.

## Downstream Impact

Milestone 4A establishes the file and metadata foundation for the later workflow:

```text
Document upload
  -> future job orchestration
  -> ML-1 classification/OCR/extraction
  -> ML-2 forensics/entity work
  -> ML-3 reasoning
  -> evidence-backed results
```

The current API creates a durable document record with a stable storage key, hash, MIME type, size, bid association, and `PENDING` status. Future workers can consume this record without changing the upload contract.

No downstream processing is started automatically.

## Intentionally Deferred

The following are intentionally outside Milestone 4A:

- MinIO/S3 production deployment wiring and SDK integration
- PDF splitting, rendering, page extraction, or page records
- Redis, Celery, ARQ, or other job orchestration
- ML-1, ML-2, or ML-3 integration
- OCR, classification, extraction, forensics, and reasoning
- Compliance scoring
- Bidder qualification/disqualification
- Fraud decisions
- External government verification
- Document deletion API

## Changed Files

Milestone 4A changed or added:

- `app/core/config.py`
- `.env.example`
- `requirements.txt`
- `app/services/storage_service.py`
- `app/services/document_service.py`
- `app/schemas/document.py`
- `app/api/v1/endpoints/documents.py`
- `tests/test_documents.py`

The existing Document SQLAlchemy model was reused without storing file bytes in the database or adding a content-hash uniqueness constraint.
