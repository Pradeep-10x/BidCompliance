import re

OFFICIAL_DPIIT_PATTERN = re.compile(r"\b(?:DIPP\d+|DPIIT[-_\s]?\d+)\b", re.IGNORECASE)
SYNTHETIC_DPIIT_PATTERN = re.compile(r"\bS*Y*N*[-_]DPI[IFT]*[-_]\d+\b", re.IGNORECASE)


def extract_dpiit_fields(ocr_text: str) -> list:
    fields = []

    # 1. Certificate / Recognition Number
    cert_num = None
    confidence = 0.0
    method = "none"

    official_match = OFFICIAL_DPIIT_PATTERN.search(ocr_text)
    if official_match:
        cert_num = official_match.group().upper()
        confidence = 0.95
        method = "regex_official_dpiit_format"
    else:
        labeled = re.search(r"(?:certificate no\.?|recognition no\.?)[:\s]+([A-Za-z0-9\-.]+)", ocr_text, re.IGNORECASE)
        if labeled:
            raw = labeled.group(1).upper()
            if raw.startswith("SSYN"):
                raw = raw[1:]
            raw = re.sub(r"DPI[FT.]*", "DPIIT-", raw).replace("--", "-")
            cert_num = raw
            confidence = 0.90
            method = "regex_labeled_dpiit_format"
        else:
            synthetic_match = SYNTHETIC_DPIIT_PATTERN.search(ocr_text)
            if synthetic_match:
                raw = synthetic_match.group().upper()
                if raw.startswith("SSYN"):
                    raw = raw[1:]
                cert_num = raw
                confidence = 0.85
                method = "regex_synthetic_dpiit_format"

    fields.append({
        "field_name": "certificate_number",
        "field_value": cert_num,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Company / Entity Name
    name_match = re.search(r"(?:company name|entity name)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "company_name",
        "field_value": name_match.group(1).strip() if name_match else None,
        "confidence": 0.85 if name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Date of Issue / Incorporation (handles OCR variants like 'date of sue')
    raw_date = None
    date_match = re.search(r"(?:date of issue|date of sue|issue date|incorporation)[:\s]*(\d{4}[/-]\d{2}[/-]?\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", ocr_text, re.IGNORECASE)
    if date_match:
        raw_val = date_match.group(1).strip()
        # Clean potential unhyphenated date like 2022-0305 -> 2022-03-05
        if re.match(r"^\d{4}-\d{4}$", raw_val):
            raw_val = f"{raw_val[:7]}-{raw_val[7:]}"
        raw_date = raw_val

    fields.append({
        "field_name": "date_of_issue",
        "field_value": raw_date,
        "confidence": 0.80 if raw_date else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 4. Validity Date
    valid_match = re.search(r"(?:valid upto|valid to|validity)[:\s]*(\d{4}[/-]\d{2}[/-]\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", ocr_text, re.IGNORECASE)
    fields.append({
        "field_name": "valid_upto",
        "field_value": valid_match.group(1).strip() if valid_match else None,
        "confidence": 0.80 if valid_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields
