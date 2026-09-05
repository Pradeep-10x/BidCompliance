import re

GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")


def extract_gst_fields(ocr_text: str) -> list:
    """Extracts GST-related fields from OCR text. Returns a list of field dicts."""
    fields = []

    gstin_match = GSTIN_PATTERN.search(ocr_text)
    fields.append({
        "field_name": "gstin",
        "field_value": gstin_match.group() if gstin_match else None,
        "confidence": 0.95 if gstin_match else 0.0,
        "extraction_method": "regex_gstin_format"
    })

    legal_name_match = re.search(r"legal name[:\s]+([A-Za-z0-9 &.,]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "legal_name",
        "field_value": legal_name_match.group(1).strip() if legal_name_match else None,
        "confidence": 0.8 if legal_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields