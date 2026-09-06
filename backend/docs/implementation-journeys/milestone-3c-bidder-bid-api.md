# Milestone 3C: Bidder + Bid REST API

## 1. Milestone Goal

Milestone 3C exposes the existing Bidder and Bid SQLAlchemy models through authenticated REST APIs. The implementation supports bidder management and tender-scoped bid management while preserving the existing database model, authentication behavior, relationships, defaults, and constraints.

The API manages domain data only. It does not evaluate bids, determine compliance, or make qualification decisions.

## 2. Starting Architecture

The implementation builds on the existing FastAPI backend:

```text
Tender
  |-- Requirements
  `-- Bids
        `-- Bidder
```

The existing components were reused:

- FastAPI routing and dependency injection
- Async SQLAlchemy sessions
- PostgreSQL UUID, JSONB, enum, and Numeric columns
- Existing JWT authentication
- Existing active-user/RBAC dependency pattern
- Existing test database, HTTP client, authentication helper, and cleanup fixtures

Bidder endpoints are top-level because bidders are reusable company/entity records. Bid endpoints are nested under a tender because each bid represents one bidder's submission to one specific tender.

## 3. Bidder API Endpoints

All endpoints require an authenticated active user.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/bidders` | Create a bidder |
| GET | `/api/v1/bidders` | List bidders with `skip` and `limit` pagination |
| GET | `/api/v1/bidders/{bidder_id}` | Retrieve one bidder |
| PATCH | `/api/v1/bidders/{bidder_id}` | Partially update a bidder |

Unexpected request fields are rejected. Omitted PATCH fields remain unchanged.

## 4. Bid API Endpoints

All endpoints require an authenticated active user.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/tenders/{tender_id}/bids` | Create a bid under a tender |
| GET | `/api/v1/tenders/{tender_id}/bids` | List bids for a tender with `skip` and `limit` pagination |
| GET | `/api/v1/tenders/{tender_id}/bids/{bid_id}` | Retrieve one tender-scoped bid |
| PATCH | `/api/v1/tenders/{tender_id}/bids/{bid_id}` | Partially update a tender-scoped bid |

Bid creation validates both the parent tender and the referenced bidder. Bid retrieval and updates always constrain the query by both `tender_id` and `bid_id`.

## 5. Why Bidder Deletion Is Intentionally Excluded

No bidder deletion endpoint was added. The existing `Bidder.bids` relationship uses `cascade="all, delete-orphan"`, so deleting a bidder would remove its associated bids. That destructive behavior is not required by the milestone and would be a broader domain operation than bidder profile management.

Bid deletion was also not added because the requested Bid API is limited to create, list, get, and PATCH operations.

## 6. Database Constraints Preserved

The implementation reuses the existing models without redesigning them:

- Bidder `legal_name` remains required.
- Bidder contact email and phone remain nullable.
- Bidder `identifiers` remains non-null JSONB with the database server default `{}`.
- Bid `tender_id` and `bidder_id` remain required UUID foreign keys.
- Bid `bid_amount` remains nullable `Numeric(15, 2)`.
- Bid status remains the existing database enum.
- The unique `(tender_id, bidder_id)` constraint is preserved.
- Existing foreign-key cascade behavior is unchanged.

Duplicate submission attempts for the same tender and bidder are translated into HTTP `409 Conflict` responses.

## 7. Authentication/RBAC Behavior

Every Bidder and Bid route uses the existing `get_current_active_user` dependency. Unauthenticated requests are rejected by the existing JWT/OAuth2 mechanism, and inactive users continue to be rejected according to the existing authentication behavior.

No second authorization system or role-specific policy was introduced. The APIs intentionally require an authenticated active user rather than inventing new role semantics.

## 8. Cross-Tender Isolation Behavior

Bid routes are tender-scoped. A bid can only be retrieved or updated when its `tender_id` matches the tender ID in the URL.

The following cases return `404`:

- The parent tender does not exist.
- The bid does not exist.
- The bid exists but belongs to another tender.
- The referenced bidder does not exist during bid creation or bidder reassignment.

This prevents cross-tender bid exposure through a different nested URL.

## 9. Decimal, JSON, and Null Handling

- Bid amounts use Pydantic `Decimal` fields and preserve the model's two-decimal precision. JSON responses expose Decimal values using the existing API serialization behavior, such as `"125000.50"`.
- Bidder identifiers are accepted and returned as structured JSON objects. No external identifier verification is performed.
- Omitted bidder identifiers preserve the database server default `{}`.
- Contact email, contact phone, and bid amount may be explicitly null.
- PATCH operations distinguish omitted fields from explicitly supplied values, preserving omitted data.

## 10. Test Coverage

New tests were added in:

- `tests/test_bidders.py`: **7 tests**
- `tests/test_bids.py`: **12 tests**

The Bidder tests cover authentication, unauthenticated rejection, creation, listing, pagination, retrieval, PATCH behavior, nullable contacts, identifier JSON round-trips/defaults, and request validation.

The Bid tests cover unauthenticated rejection, valid creation, nonexistent tender and bidder handling, listing, pagination, retrieval, cross-tender isolation, PATCH behavior, partial updates, duplicate tender/bidder conflicts, nullable bid amounts, Decimal serialization, and validation.

The full backend suite result was:

```text
66 passed
```

The suite also reports one existing Starlette deprecation warning related to `HTTP_422_UNPROCESSABLE_ENTITY`. This warning is not introduced by the Bidder or Bid API implementation.

## 11. Existing Starlette Deprecation Warning

The full suite continues to emit the existing warning recommending `HTTP_422_UNPROCESSABLE_CONTENT` instead of the deprecated `HTTP_422_UNPROCESSABLE_ENTITY` constant. It does not cause test failures and was outside the scope of this milestone.

## 12. Downstream Impact on Document APIs and ML Pipeline

Milestone 3C establishes the data path needed by later workflows:

```text
Tender
  -> Bid
  -> Bidder
  -> Documents
  -> ML-1 / ML-2 / ML-3
  -> Evidence
  -> Backend deterministic rules
```

The Bid API provides stable tender and bidder references for future Document APIs. Documents can later attach to a specific bid without requiring changes to the Bidder or Bid API contract.

The implementation does not invoke document processing, ML services, evidence extraction, or rule evaluation. It only stores and exposes the domain records that downstream components may consume later.

## 13. Explicit Non-Goals

No following behavior was added:

- ML service calls
- ML job creation
- Compliance scoring
- Bidder qualification or disqualification
- Fraud decisions or accusations
- External government verification
- Official validation of PAN, GSTIN, CIN, or other identifiers based on formatting
- Automatic bid status transitions
- Final decision logic

Bid status remains explicitly controlled by API/application input and the existing model defaults.

## 14. Changed Files

Milestone 3C added or updated:

- `app/schemas/bidder.py`
- `app/schemas/bid.py`
- `app/services/bidder_service.py`
- `app/services/bid_service.py`
- `app/api/v1/endpoints/bidders.py`
- `app/api/v1/endpoints/bids.py`
- `app/api/v1/api.py`
- `tests/test_bidders.py`
- `tests/test_bids.py`

Existing Bidder and Bid models were reused unchanged.

## 15. What Is Intentionally Deferred

The following work remains outside Milestone 3C:

- Bidder and Bid deletion APIs
- Document upload, storage, processing, and retrieval APIs
- Evidence APIs
- ML extraction, classification, comparison, and reasoning workflows
- Deterministic compliance rule evaluation
- Qualification/disqualification and final tender decisions
- External identifier verification
- Advanced search and filtering
- More extensive negative-path coverage for every HTTP method
- Pagination boundary and maximum-limit tests
- PATCH-specific duplicate tender/bidder conflict tests

These can be introduced in later milestones without changing the core separation between domain data APIs, document/ML processing, and backend deterministic decision logic.
