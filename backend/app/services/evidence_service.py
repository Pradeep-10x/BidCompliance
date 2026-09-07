import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.document import Document
from app.models.evidence import Evidence
from app.models.ml_processing_result import MLProcessingResult


def _generate_authoritative_evidence_id(document_id: UUID, field_name: str) -> str:
    """Generate a guaranteed non-colliding, authoritative backend evidence identifier."""
    clean_field = "".join(c for c in field_name if c.isalnum() or c == "_")[:24]
    random_suffix = uuid.uuid4().hex[:12]
    return f"ev_{document_id.hex[:8]}_{clean_field}_{random_suffix}"


def _validate_raw_field(raw: Any) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Validate raw extracted field payload.
    
    Returns (cleaned_data, error_dict). Exactly one will be non-None.
    """
    if not isinstance(raw, dict):
        return None, {
            "code": "MALFORMED_FIELD",
            "detail": "Field entry must be a dictionary/object",
            "raw": str(raw),
        }

    field_name = raw.get("field") or raw.get("field_name")
    if not field_name or not isinstance(field_name, str) or not field_name.strip():
        return None, {
            "code": "MALFORMED_FIELD",
            "field": None,
            "detail": "Field entry must contain a non-empty string 'field' or 'field_name'",
            "raw": raw,
        }
    clean_field_name = field_name.strip()

    # Validate confidence if provided
    confidence = raw.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
            if confidence < 0.0 or confidence > 1.0:
                return None, {
                    "code": "MALFORMED_FIELD",
                    "field": clean_field_name,
                    "detail": f"Confidence must be between 0.0 and 1.0, got {confidence}",
                    "raw": raw,
                }
        except (ValueError, TypeError):
            return None, {
                "code": "MALFORMED_FIELD",
                "field": clean_field_name,
                "detail": f"Confidence must be a valid float, got {type(confidence).__name__}",
                "raw": raw,
            }

    # Validate page number if provided
    page_num = raw.get("page_number") if "page_number" in raw else raw.get("page")
    if page_num is not None:
        try:
            page_num = int(page_num)
            if page_num < 1:
                return None, {
                    "code": "MALFORMED_FIELD",
                    "field": clean_field_name,
                    "detail": f"Page number must be >= 1, got {page_num}",
                    "raw": raw,
                }
        except (ValueError, TypeError):
            return None, {
                "code": "MALFORMED_FIELD",
                "field": clean_field_name,
                "detail": f"Page number must be an integer, got {type(page_num).__name__}",
                "raw": raw,
            }

    # Validate bounding box if provided
    bounding_box = raw.get("bounding_box")
    if bounding_box is not None and not isinstance(bounding_box, (list, dict)):
        return None, {
            "code": "MALFORMED_FIELD",
            "field": clean_field_name,
            "detail": "Bounding box must be a list, dict, or null",
            "raw": raw,
        }

    val = raw.get("value") if "value" in raw else raw.get("field_value")
    val_str = str(val) if val is not None else None

    norm_val = raw.get("value_normalized")
    norm_val_str = str(norm_val) if norm_val is not None else None

    source_text = raw.get("source_text")
    source_text_str = str(source_text) if source_text is not None else None

    extraction_method = raw.get("extraction_method")
    ext_method_str = str(extraction_method) if extraction_method is not None else "ocr"

    ml_ev_id = raw.get("evidence_id")
    ml_ev_id_str = str(ml_ev_id).strip() if ml_ev_id is not None else None

    return {
        "field_name": clean_field_name,
        "value": val_str,
        "value_normalized": norm_val_str,
        "confidence": confidence,
        "page_number": page_num,
        "bounding_box": bounding_box,
        "source_text": source_text_str,
        "extraction_method": ext_method_str,
        "source_evidence_id": ml_ev_id_str,
    }, None


async def ingest_evidence_from_ml_result(
    db: AsyncSession,
    ml_result: MLProcessingResult,
    document: Document,
) -> list[Evidence]:
    """Ingest extracted facts as durable, authoritative Evidence records from MLProcessingResult.
    
    This operation is transactional and idempotent:
    - If evidence records already exist for ml_result.id, existing records are returned.
    - Authoritative non-colliding evidence IDs are generated for each record.
    - Source ML evidence references are preserved for provenance.
    - Malformed field items are rejected and preserved in ml_result.errors without inventing new ML statuses.
    - Valid field items are persisted.
    """
    # 1. Idempotency check: Return existing evidence if already ingested
    existing_stmt = (
        select(Evidence)
        .where(Evidence.ml_result_id == ml_result.id)
        .order_by(Evidence.created_at, Evidence.field_name)
    )
    existing_result = await db.execute(existing_stmt)
    existing_records = list(existing_result.scalars().all())
    if existing_records:
        return existing_records

    # 2. Extract raw field list/dict from result payload
    result_data = ml_result.result or {}
    fields_payload = result_data.get("fields")

    raw_items: list[Any] = []
    if isinstance(fields_payload, list):
        raw_items = fields_payload
    elif isinstance(fields_payload, dict):
        # Convert dictionary to item objects
        for k, v in fields_payload.items():
            if isinstance(v, dict):
                item = dict(v)
                item.setdefault("field", k)
                raw_items.append(item)
            else:
                raw_items.append({"field": k, "value": v})
    elif fields_payload is None and isinstance(result_data, dict):
        # Fallback if result has other top-level keys
        for k, v in result_data.items():
            if k not in {"document_classification", "ocr_metadata", "errors"} and not isinstance(v, dict):
                raw_items.append({"field": k, "value": v})

    # 3. Validate each field
    new_evidence_list: list[Evidence] = []
    new_errors: list[dict[str, Any]] = []

    for item in raw_items:
        clean_data, err = _validate_raw_field(item)
        if err:
            new_errors.append(err)
            continue

        auth_evidence_id = _generate_authoritative_evidence_id(
            document.id, clean_data["field_name"]
        )

        evidence = Evidence(
            id=uuid.uuid4(),
            evidence_id=auth_evidence_id,
            source_evidence_id=clean_data["source_evidence_id"],
            document_id=document.id,
            ml_result_id=ml_result.id,
            field_name=clean_data["field_name"],
            value=clean_data["value"],
            value_normalized=clean_data["value_normalized"],
            confidence=clean_data["confidence"],
            page_number=clean_data["page_number"],
            bounding_box=clean_data["bounding_box"],
            source_text=clean_data["source_text"],
            extraction_method=clean_data["extraction_method"],
            evidence_type="ML_EXTRACTION",
        )
        new_evidence_list.append(evidence)

    # 4. If any partial-ingestion errors were identified, record them in ml_result.errors
    if new_errors:
        current_errors = list(ml_result.errors or [])
        current_errors.extend(new_errors)
        ml_result.errors = current_errors
        flag_modified(ml_result, "errors")

    # 5. Persist evidence rows within the active transaction
    if new_evidence_list:
        db.add_all(new_evidence_list)
        await db.flush()

    return new_evidence_list


async def list_document_evidence(
    db: AsyncSession, document_id: UUID
) -> list[Evidence]:
    """Retrieve all evidence records for a specific document."""
    stmt = (
        select(Evidence)
        .where(Evidence.document_id == document_id)
        .order_by(Evidence.created_at.asc(), Evidence.field_name.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_document_evidence(
    db: AsyncSession, document_id: UUID, identifier: str
) -> Optional[Evidence]:
    """Retrieve a single evidence record for a document by UUID, authoritative ID, or source ID."""
    id_clean = identifier.strip()
    try:
        parsed_uuid = UUID(id_clean)
        matcher = (
            (Evidence.id == parsed_uuid)
            | (Evidence.evidence_id == id_clean)
            | (Evidence.source_evidence_id == id_clean)
        )
    except (ValueError, AttributeError):
        matcher = (
            (Evidence.evidence_id == id_clean)
            | (Evidence.source_evidence_id == id_clean)
        )

    stmt = select(Evidence).where(
        and_(Evidence.document_id == document_id, matcher)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
