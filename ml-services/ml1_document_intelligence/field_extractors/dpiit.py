"""DPIIT Startup Recognition Certificate — Field Extractor.

Extracts: certificate_number, company_name, date_of_issue, valid_upto.
"""
import re
from typing import List, Dict, Any

# Official DPIIT format: DIPPXXXX or DPIIT-XXXX
OFFICIAL_DPIIT_PATTERN = re.compile(r"\b(?:DIPP\d+|DPIIT[-_\s]?\d+)\b", re.IGNORECASE)


def extract_dpiit_fields(ocr_text: str) -> List[Dict[str, Any]]:
    """Extracts DPIIT startup recognition fields from OCR text."""
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
            cert_num = labeled.group(1).upper()
            confidence = 0.85
            method = "regex_labeled_dpiit_format"

    fields.append({
        "field": "certificate_number",
        "value": cert_num,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Company / Entity Name
    name_match = re.search(r"(?:company name|entity name)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "company_name",
        "value": name_match.group(1).strip() if name_match else None,
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
        "field": "date_of_issue",
        "value": raw_date,
        "confidence": 0.80 if raw_date else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 4. Validity Date
    valid_match = re.search(r"(?:valid upto|valid to|validity)[:\s]*(\d{4}[/-]\d{2}[/-]\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "valid_upto",
        "value": valid_match.group(1).strip() if valid_match else None,
        "confidence": 0.80 if valid_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields
