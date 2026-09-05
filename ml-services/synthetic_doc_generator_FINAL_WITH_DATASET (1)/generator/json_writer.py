import json
from dataclasses import asdict
from pathlib import Path


def to_common_json(record):
    d = asdict(record)
    doc_type = record.__class__.__name__.replace("Record", "").upper()
    if doc_type == "PAN":
        entity_name = d.get("holder_name")
        entity_type = "individual"
    else:
        entity_name = d.get("manufacturing_unit_name") or d.get("company_name") or d.get("enterprise_name")
        entity_type = "company"
    preferred = [
        "reference_number", "pan_number", "cin_number", "gstin_number",
        "certificate_number", "udyam_registration_number", "licence_number"
    ]
    primary = next(((k, d[k]) for k in preferred if k in d), ("document_id", d["document_id"]))
    address = d.get("manufacturing_unit_address") or d.get("factory_address") or d.get("principal_address")
    if not address and d.get("line1"):
        address = ", ".join(str(x) for x in [d.get("line1"), d.get("city"), d.get("state"), d.get("pin")] if x)
    date_keys = {k for k in d if k.endswith("date") or k.endswith("_date") or k in {"valid_from", "valid_upto", "validity_from", "validity_to"}}
    excluded = {
        "document_id", "watermark_tag", *preferred,
        "manufacturing_unit_name", "company_name", "enterprise_name", "holder_name",
        "manufacturing_unit_address", "factory_address", "principal_address", "line1", "city", "state", "pin"
    }
    extra = {k: v for k, v in d.items() if k not in excluded and k not in date_keys}
    other_dates = []
    for k in sorted(date_keys):
        if k in {"issue_date", "certificate_issue_date", "date_of_issue", "valid_from", "validity_from", "valid_upto", "validity_to"}:
            continue
        if d.get(k):
            other_dates.append({"label": k, "value": d[k]})
    issue_date = d.get("issue_date") or d.get("certificate_issue_date") or d.get("date_of_issue")
    valid_from = d.get("valid_from") or d.get("validity_from")
    valid_upto = d.get("valid_upto") or d.get("validity_to")
    return {
        "document_id": d["document_id"],
        "document_type": doc_type,
        "issuing_authority": "Fictional Demo Authority",
        "entity": {
            "name": entity_name,
            "type": entity_type,
            "constitution": d.get("constitution_of_business") or d.get("constitution_type")
        },
        "identifiers": {
            "primary_id_label": primary[0],
            "primary_id_value": primary[1],
            "secondary_ids": [
                {"label": k, "value": d[k]}
                for k in ["pan_number", "cin_number", "tan_number", "gstin_number", "certificate_number", "udyam_registration_number", "licence_number"]
                if k in d and k != primary[0]
            ]
        },
        "address": {
            "raw_text": address,
            "structured": {
                "line1": d.get("line1"),
                "city": d.get("city"),
                "state": d.get("state"),
                "pin": d.get("pin")
            }
        },
        "dates": {
            "issue_date": issue_date,
            "valid_from": valid_from,
            "valid_upto": valid_upto,
            "other_dates": other_dates
        },
        "signatory": {
            "name": d.get("signatory_name") or d.get("officer_name"),
            "designation": d.get("signatory_designation") or d.get("officer_designation")
        },
        "visual_elements": {
            "has_photo": bool(d.get("photo_present", False)),
            "has_qr_or_barcode": False,
            "has_signature_block": bool(d.get("signature_present") or d.get("digital_signature_text") or d.get("signatory_name")),
            "has_emblem_or_logo": False
        },
        "extra_fields": extra,
        "fields": d,
        "watermark_tag": d["watermark_tag"]
    }


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
