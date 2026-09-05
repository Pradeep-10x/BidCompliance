import re

CIN_PATTERN = re.compile(r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")


def extract_mca_fields(ocr_text: str) -> list:
    fields = []

    cin_match = CIN_PATTERN.search(ocr_text)
    fields.append({
        "field_name": "cin",
        "field_value": cin_match.group() if cin_match else None,
        "confidence": 0.95 if cin_match else 0.0,
        "extraction_method": "regex_cin_format"
    })

    company_name_match = re.search(r"certify that ([A-Za-z0-9 &.,]+?) is incorporated", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "company_name",
        "field_value": company_name_match.group(1).strip() if company_name_match else None,
        "confidence": 0.8 if company_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields