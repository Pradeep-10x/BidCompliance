"""MCA Certificate of Incorporation — Field Extractor.

Extracts: cin, company_name, date_of_incorporation.
"""
import re
from typing import List, Dict, Any

# Official CIN format: U/L + 5 digits + 2 alpha (state) + 4 digits (year) + 3 alpha + 6 digits
OFFICIAL_CIN_PATTERN = re.compile(r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")


def extract_mca_fields(ocr_text: str) -> List[Dict[str, Any]]:
    """Extracts MCA incorporation fields from OCR text."""
    fields = []

    # 1. CIN (Corporate Identity Number)
    cin = None
    confidence = 0.0
    method = "none"

    official_match = OFFICIAL_CIN_PATTERN.search(ocr_text)
    if official_match:
        cin = official_match.group()
        confidence = 0.95
        method = "regex_official_cin_format"
    else:
        # Fallback: labeled CIN field
        labeled_cin = re.search(r"\bcin[:\s]+([A-Za-z0-9\-]+)", ocr_text, re.IGNORECASE)
        if labeled_cin:
            cin = labeled_cin.group(1).upper()
            confidence = 0.85
            method = "regex_labeled_cin_format"

    fields.append({
        "field": "cin",
        "value": cin,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Company Name
    company_name_match = re.search(r"(?:certify that|company name[:\s]+)([A-Za-z0-9 &.,\-_]+?)(?:\s+is incorporated|\n|$)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "company_name",
        "value": company_name_match.group(1).strip() if company_name_match else None,
        "confidence": 0.85 if company_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Incorporation Date
    date_match = re.search(r"(?:incorporation date|date of incorporation|dated)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "date_of_incorporation",
        "value": date_match.group(1).strip() if date_match else None,
        "confidence": 0.80 if date_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields