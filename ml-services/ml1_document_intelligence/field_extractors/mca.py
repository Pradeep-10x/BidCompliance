import re

OFFICIAL_CIN_PATTERN = re.compile(r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")
SYNTHETIC_CIN_PATTERN = re.compile(r"\bS*Y*N*[-_]?CIN[-_]\d+\b", re.IGNORECASE)


def extract_mca_fields(ocr_text: str) -> list:
    fields = []

    # 1. CIN
    cin = None
    confidence = 0.0
    method = "none"

    official_match = OFFICIAL_CIN_PATTERN.search(ocr_text)
    if official_match:
        cin = official_match.group()
        confidence = 0.95
        method = "regex_official_cin_format"
    else:
        # Check for explicit cin label first, then synthetic pattern
        labeled_cin = re.search(r"\bcin[:\s]+([A-Za-z0-9\-]+)", ocr_text, re.IGNORECASE)
        if labeled_cin:
            raw = labeled_cin.group(1).upper()
            if raw.startswith("SSYN"):
                raw = raw[1:]
            cin = raw
            confidence = 0.90
            method = "regex_labeled_cin_format"
        else:
            synthetic_match = SYNTHETIC_CIN_PATTERN.search(ocr_text)
            if synthetic_match:
                raw = synthetic_match.group().upper()
                if raw.startswith("SSYN"):
                    raw = raw[1:]
                cin = raw
                confidence = 0.85
                method = "regex_synthetic_cin_format"

    fields.append({
        "field_name": "cin",
        "field_value": cin,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Company Name
    company_name_match = re.search(r"(?:certify that|company name[:\s]+)([A-Za-z0-9 &.,\-_]+?)(?:\s+is incorporated|\n|$)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "company_name",
        "field_value": company_name_match.group(1).strip() if company_name_match else None,
        "confidence": 0.85 if company_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Incorporation Date
    date_match = re.search(r"(?:incorporation date|date of incorporation|dated)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "date_of_incorporation",
        "field_value": date_match.group(1).strip() if date_match else None,
        "confidence": 0.80 if date_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields