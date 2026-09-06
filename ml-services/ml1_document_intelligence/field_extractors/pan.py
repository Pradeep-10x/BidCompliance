import re

OFFICIAL_PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]{1}\b")
SYNTHETIC_PAN_PATTERN = re.compile(r"\bS*YN[-_]PAN[-_]\d+\b", re.IGNORECASE)


def extract_pan_fields(ocr_text: str) -> list:
    fields = []

    # 1. PAN Number
    pan_number = None
    confidence = 0.0
    method = "none"

    official_match = OFFICIAL_PAN_PATTERN.search(ocr_text)
    if official_match:
        pan_number = official_match.group()
        confidence = 0.95
        method = "regex_official_pan_format"
    else:
        synthetic_match = SYNTHETIC_PAN_PATTERN.search(ocr_text)
        if synthetic_match:
            raw = synthetic_match.group().upper()
            if raw.startswith("SSYN"):
                raw = raw[1:]
            pan_number = raw
            confidence = 0.90
            method = "regex_synthetic_pan_format"

    fields.append({
        "field_name": "pan_number",
        "field_value": pan_number,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Cardholder / Holder Name
    name_match = re.search(r"(?:holder name|cardholder(?:'s)? name|name)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "name",
        "field_value": name_match.group(1).strip() if name_match else None,
        "confidence": 0.85 if name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Date of Birth
    dob_match = re.search(r"(?:date of birth|dob)[:\s]*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})", ocr_text, re.IGNORECASE)
    if not dob_match:
        dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b", ocr_text)

    fields.append({
        "field_name": "date_of_birth",
        "field_value": dob_match.group(1) if dob_match else None,
        "confidence": 0.80 if dob_match else 0.0,
        "extraction_method": "regex_date_format"
    })

    return fields