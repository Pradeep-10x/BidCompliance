import re

UDYAM_PATTERN = re.compile(r"UDYAM-[A-Z]{2}-\d{2}-\d{7}")


def extract_udyam_fields(ocr_text: str) -> list:
    fields = []

    udyam_match = UDYAM_PATTERN.search(ocr_text)
    fields.append({
        "field_name": "udyam_registration_number",
        "field_value": udyam_match.group() if udyam_match else None,
        "confidence": 0.95 if udyam_match else 0.0,
        "extraction_method": "regex_udyam_format"
    })

    enterprise_name_match = re.search(r"name of enterprise[:\s]+([A-Za-z0-9 &.,]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "enterprise_name",
        "field_value": enterprise_name_match.group(1).strip() if enterprise_name_match else None,
        "confidence": 0.8 if enterprise_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields