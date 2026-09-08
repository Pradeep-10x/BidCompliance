# Milestone 4F: Bid-Level Compliance Aggregation & Orchestration

## 1. Goal of Milestone 4F

Milestone 4F builds the backend bid-level compliance aggregation layer on top of persisted `RequirementEvaluation` records. It summarizes requirement-level compliance deterministically, providing a structured, explainable, and audit-traceable foundation for the future Procurement Officer decision-making workflow.

### Architectural Boundary

- **4D**: ML-1 $\rightarrow$ persisted `Evidence`.
- **4E**: `Evidence` + `Requirement.rule_config` $\rightarrow$ deterministic `RequirementEvaluation`.
- **4F**: Persisted `RequirementEvaluation` $\rightarrow$ bid-level compliance summary (`BidComplianceSummaryResponse`).

### Critical Guarantees (4F Must NOT)

- **Must NOT allow ML to decide qualification**: All aggregation is deterministic, consuming persisted backend records.
- **Must NOT change Requirement rules or Evidence**: Pure aggregation over persisted data; zero mutation of domain entities.
- **Must NOT bypass deterministic requirement evaluation**: Summary directly incorporates requirement-level outcomes.
- **Must NOT directly qualify or disqualify a bid**: `Bid.status` remains completely unchanged (`SUBMITTED`).
- **Must NOT replace Procurement Officer decision-making**: Summary statuses are neutral evaluation states (`READY_FOR_REVIEW`, `REVIEW_REQUIRED`, `INCOMPLETE`, `ERROR`).

---

## 2. Aggregation Architecture & Data Model Decisions

### No Redundant Persistence Table

In accordance with architectural principles ("Prefer reusing RequirementEvaluation records and computing the summary deterministically... Do not create unnecessary duplication"):
- No separate persistence table was added.
- The summary is computed dynamically, deterministically, and idempotently from the authoritative `requirements` and `requirement_evaluations` tables.
- This prevents data staleness, schema duplication, and cache-invalidation bugs while ensuring 100% real-time auditability.

---

## 3. Aggregation Algorithm & Formulas

For any tender $T$ and bid $B$:
1. Fetch all requirements $R = \{r_1, r_2, \dots, r_n\}$ belonging to $T$, sorted deterministically by `(created_at, id)`.
2. Fetch all persisted requirement evaluations $E$ belonging to $B$ under $T$.
3. For each requirement $r \in R$:
   - If no evaluation exists in $E$, track as `UNEVALUATED`.
   - If an evaluation exists, increment corresponding status counters (`compliant`, `non_compliant`, `missing_evidence`, `low_confidence`, `error`).
   - If $r.\text{is\_mandatory}$ is True:
     - Increment `mandatory_total`.
     - If evaluated: increment `mandatory_evaluated`.
     - If evaluation status is `COMPLIANT`: increment `mandatory_compliant`.
     - Otherwise (if status is `NON_COMPLIANT`, `MISSING_EVIDENCE`, `LOW_CONFIDENCE`, or `ERROR`): increment `mandatory_non_compliant`.

### Compliance Ratio (Unweighted)

$$\text{compliance\_ratio} = \begin{cases} 1.0 & \text{if } \text{total\_requirements} = 0 \\ \operatorname{round}\left(\frac{\text{compliant}}{\text{total\_requirements}}, 4\right) & \text{otherwise} \end{cases}$$

### Weighted Compliance Metric

Requirements define `weight` (numeric decimal, default `1.00`).
- Non-positive weights are clamped safely: $w(r) = \max(0.0, r.\text{weight})$.
- Total weight: $W_{\text{total}} = \sum_{r \in R} w(r)$.
- Compliant weight: $W_{\text{compliant}} = \sum_{r \in R \land \text{status}(r) = \text{COMPLIANT}} w(r)$.

$$\text{weighted\_compliance\_ratio} = \begin{cases} \text{compliance\_ratio} & \text{if } W_{\text{total}} \le 0.0 \\ \operatorname{round}\left(\frac{W_{\text{compliant}}}{W_{\text{total}}}, 4\right) & \text{otherwise} \end{cases}$$

---

## 4. Summary Status Semantics

The `summary_status` is strictly neutral and conveys the readiness of the bid for human review:

1. `ERROR`:
   - Trigger: At least one requirement evaluation resulted in `ERROR` (`error > 0`).
   - Meaning: A rule config error, unparseable numeric, or regex error requires administrative attention.
2. `INCOMPLETE`:
   - Trigger: Not all tender requirements have been evaluated yet (`unevaluated_requirements > 0`).
   - Meaning: Evaluation pipeline has not finished or was only partially executed. Missing evaluations are never silently coerced to `NON_COMPLIANT`.
3. `REVIEW_REQUIRED`:
   - Trigger: All requirements evaluated, but one or more mandatory requirements failed (`mandatory_compliant < mandatory_total`) OR any requirement is `NON_COMPLIANT`, `MISSING_EVIDENCE`, or `LOW_CONFIDENCE`.
   - Meaning: Discrepancies or missing documents need Procurement Officer manual review.
4. `READY_FOR_REVIEW`:
   - Trigger: All requirements evaluated, 100% compliant, all mandatory requirements satisfied, 0 errors.
   - Meaning: Bid satisfies all deterministic rules and is ready for officer review and final decision.

---

## 5. Provenance & Explainability

The summary response preserves item-by-item provenance in the `requirements` array:
- `requirement_id`: UUID of the tender requirement.
- `title`: Requirement title.
- `is_mandatory`: Whether requirement is mandatory.
- `weight`: Requirement weight.
- `evaluation_id`: UUID of the persisted `RequirementEvaluation` (or `null` if unevaluated).
- `status`: Requirement status (`COMPLIANT`, `NON_COMPLIANT`, `MISSING_EVIDENCE`, `LOW_CONFIDENCE`, `ERROR`, `UNEVALUATED`).
- `target_field`: Extracted field checked.
- `extracted_value`: Raw or normalized value extracted from document.
- `confidence`: ML extraction confidence score.
- `evidence_id`: UUID of the underlying authoritative `Evidence` record.
- `reason`: Human-readable explanation of deterministic result.
- `details`: Rich evaluation diagnostics (operator, matched evidence ID, candidates considered).

---

## 6. API Specification

### Endpoint:
`GET /api/v1/tenders/{tender_id}/bids/{bid_id}/compliance-summary`

- **Authentication**: Required (`Bearer <JWT>`). Returns `401 Unauthorized` if unauthenticated.
- **Scoping**:
  - Validates `tender_id` exists (returns `404 Not Found` if missing).
  - Validates `bid_id` exists and belongs to `tender_id` (returns `404 Not Found` for mismatched/cross-tender bids).
- **Idempotency & Read-Only Guarantee**:
  - Querying the summary does not alter database state.
  - `Bid.status` remains unchanged.
  - `Requirement` and `Evidence` rows are untouched.

---

## 7. Verification & Test Results

### Focused Test Suite (`tests/test_compliance_summary.py`)
17 focused unit and integration tests covering:
1. `test_compliance_summary_all_compliant`: 100% compliance, status `READY_FOR_REVIEW`, ratio 1.0.
2. `test_compliance_summary_mixed_statuses`: Mixed compliant and non-compliant, status `REVIEW_REQUIRED`.
3. `test_compliance_summary_mandatory_failure`: Mandatory requirement failure flagged, status `REVIEW_REQUIRED`.
4. `test_compliance_summary_missing_evidence`: Missing evidence counter and status `REVIEW_REQUIRED`.
5. `test_compliance_summary_low_confidence`: Low confidence counter and status `REVIEW_REQUIRED`.
6. `test_compliance_summary_evaluation_error`: Evaluation error propagates to summary status `ERROR`.
7. `test_compliance_summary_zero_requirements`: Zero-requirement tender edge case handled gracefully.
8. `test_compliance_summary_incomplete_evaluations`: Partial evaluation returns `INCOMPLETE` without coercing unevaluated to non-compliant.
9. `test_compliance_summary_repeated_call_determinism`: Deterministic idempotency on repeated calls.
10. `test_compliance_summary_immutability`: Verifies `Bid.status`, `Requirement`, and `Evidence` remain unmodified.
11. `test_compliance_summary_provenance`: Verifies linking from requirement to `RequirementEvaluation` and `Evidence`.
12. `test_compliance_summary_weighted_calculation`: Verifies exact weighted mathematical formula.
13. `test_compliance_summary_zero_and_negative_weights`: Safe handling of zero and negative weights.
14. `test_compliance_summary_scoping_and_not_found`: Scoping enforcement and 404 handling.
15. `test_compliance_summary_unauthenticated`: RBAC enforcement and 401 handling.
16. `test_compliance_summary_no_autonomous_qualification`: Confirms zero premature qualification/disqualification.
17. `test_compliance_summary_direct_service_layer`: Direct service-layer verification.

**Focused Suite Result**: `17 passed in 19.91s`.

### Full Test Suite Result
Full suite across all backend modules (Milestones 1 through 4F):
- **168 passed**, 2 pre-existing Starlette deprecation warnings in 151.96s (2m 31s).
- Zero regressions.

---

## 8. Limitations & Next Steps for Procurement Officer Workflow

- **Procurement Officer Final Decision**: 4F provides the compliance summary, but only an authorized Procurement Officer can review discrepancies, inspect evidence bounding boxes and documents, and issue the authoritative `QUALIFIED` or `DISQUALIFIED` decision.
- **Manual Overrides & Remarks**: The upcoming Procurement Officer workflow will allow authorized officers to record formal justification when accepting edge-case documentation or overriding low-confidence flags.
