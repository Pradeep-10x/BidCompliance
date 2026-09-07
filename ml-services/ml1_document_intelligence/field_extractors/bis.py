"""BIS Certificate / Licence — Field Extractor.

Extracts: licence_number, manufacturing_unit_name, product_name, expiry_date.
"""
import re
from typing import List, Dict, Any

# Official BIS format: CM/L-XXXXXXX or IS XXXX
OFFICIAL_BIS_PATTERN = re.compile(r"\b(?:CM/L[-_\s]?\d{7,10}|IS[-_\s]?\d+)\b", re.IGNORECASE)


def extract_bis_fields(ocr_text: str) -> List[Dict[str, Any]]:
    """Extracts BIS certification fields from OCR text."""
    fields = []

    # 1. Reference / Licence Number
    ref_num = None
    confidence = 0.0
    method = "none"

    official_match = OFFICIAL_BIS_PATTERN.search(ocr_text)
    if official_match:
        ref_num = official_match.group()
        confidence = 0.95
        method = "regex_official_bis_format"
    else:
        # Fallback: labeled reference
        labeled = re.search(r"(?:reference no\.?|licence no\.?)[:\s]+([A-Za-z0-9\-/]+)", ocr_text, re.IGNORECASE)
        if labeled:
            ref_num = labeled.group(1).upper()
            confidence = 0.85
            method = "regex_labeled_bis_format"

    fields.append({
        "field": "licence_number",
        "value": ref_num,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Manufacturing Unit Name
    unit_match = re.search(r"(?:unit name|manufacturer|manufacturing unit)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "manufacturing_unit_name",
        "value": unit_match.group(1).strip() if unit_match else None,
        "confidence": 0.85 if unit_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Product / IS Standard
    product_match = re.search(r"(?:product|is number)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "product_name",
        "value": product_match.group(1).strip() if product_match else None,
        "confidence": 0.80 if product_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 4. Validity / Expiry Date
    valid_upto_match = re.search(r"(?:valid upto|valid to|expiry date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "expiry_date",
        "value": valid_upto_match.group(1).strip() if valid_upto_match else None,
        "confidence": 0.80 if valid_upto_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields
