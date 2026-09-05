import re

OFFICIAL_UDYAM_PATTERN = re.compile(r"UDYAM-[A-Z]{2}-\d{2}-\d{7}")
SYNTHETIC_UDYAM_PATTERN = re.compile(r"\bSYN[-_]UDYAM[-_]\d+\b", re.IGNORECASE)


def extract_udyam_fields(ocr_text: str) -> list:
    fields = []

    # 1. Udyam Registration Number
    udyam_number = None
    confidence = 0.0
    method = "none"

    official_match = OFFICIAL_UDYAM_PATTERN.search(ocr_text)
    if official_match:
        udyam_number = official_match.group()
        confidence = 0.95
        method = "regex_official_udyam_format"
    else:
        synthetic_match = SYNTHETIC_UDYAM_PATTERN.search(ocr_text)
        if synthetic_match:
            udyam_number = synthetic_match.group().upper()
            confidence = 0.90
            method = "regex_synthetic_udyam_format"

    fields.append({
        "field_name": "udyam_registration_number",
        "field_value": udyam_number,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Enterprise Name
    enterprise_name_match = re.search(r"(?:name of enterprise|enterprise name)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "enterprise_name",
        "field_value": enterprise_name_match.group(1).strip() if enterprise_name_match else None,
        "confidence": 0.80 if enterprise_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Enterprise Type
    enterprise_type_match = re.search(r"(?:type of enterprise|enterprise type)[:\s]+(Micro|Small|Medium|[A-Za-z]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "enterprise_type",
        "field_value": enterprise_type_match.group(1).strip() if enterprise_type_match else None,
        "confidence": 0.80 if enterprise_type_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields