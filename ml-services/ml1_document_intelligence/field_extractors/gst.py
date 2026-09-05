import re

OFFICIAL_GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")
SYNTHETIC_GSTIN_PATTERN = re.compile(r"\b(?:SYN[-_]GST[-_]\d+|syN-@st\d+)\b", re.IGNORECASE)


def extract_gst_fields(ocr_text: str) -> list:
    """Extracts GST-related fields from OCR text. Returns a list of field dicts."""
    fields = []

    # 1. GSTIN Identification
    gstin = None
    confidence = 0.0
    method = "none"

    official_match = OFFICIAL_GSTIN_PATTERN.search(ocr_text)
    if official_match:
        gstin = official_match.group()
        confidence = 0.95
        method = "regex_official_gstin_format"
    else:
        synthetic_match = SYNTHETIC_GSTIN_PATTERN.search(ocr_text)
        if synthetic_match:
            gstin = synthetic_match.group().upper().replace("@", "G")
            confidence = 0.90
            method = "regex_synthetic_gstin_format"

    fields.append({
        "field_name": "gstin",
        "field_value": gstin,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Legal Name
    legal_name_match = re.search(r"legal name[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "legal_name",
        "field_value": legal_name_match.group(1).strip() if legal_name_match else None,
        "confidence": 0.85 if legal_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Trade Name
    trade_name_match = re.search(r"trade name[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "trade_name",
        "field_value": trade_name_match.group(1).strip() if trade_name_match else None,
        "confidence": 0.85 if trade_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 4. Validity / Registration Date
    date_match = re.search(r"(?:valid from|registration date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "registration_date",
        "field_value": date_match.group(1).strip() if date_match else None,
        "confidence": 0.80 if date_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields