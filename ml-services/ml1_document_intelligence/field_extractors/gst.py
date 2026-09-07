"""GST Registration Certificate — Field Extractor.

Extracts: GSTIN, legal_name, trade_name, registration_date.
Includes GSTIN Mod-36 check-digit validation per government format.
"""
import re
from typing import List, Dict, Any

# Official GSTIN: 2-digit state + 10-char PAN + 1 entity + Z + 1 check
OFFICIAL_GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")


def validate_gstin_checksum(gstin: str) -> bool:
    """Validates the 15th character of GSTIN using Mod-36 algorithm.

    The GSTIN check digit is computed over the first 14 characters.
    Returns True if the check digit matches, False otherwise.
    """
    if not gstin or len(gstin) != 15:
        return False

    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    total = 0
    for i, c in enumerate(gstin[:14]):
        idx = chars.find(c.upper())
        if idx == -1:
            return False
        factor = (2 if i % 2 else 1) * idx
        total += factor // 36 + factor % 36

    check = (36 - (total % 36)) % 36
    return chars[check] == gstin[14].upper()


def extract_gst_fields(ocr_text: str) -> List[Dict[str, Any]]:
    """Extracts GST-related fields from OCR text. Returns a list of field dicts."""
    fields = []

    # 1. GSTIN Identification
    gstin = None
    confidence = 0.0
    method = "none"

    official_match = OFFICIAL_GSTIN_PATTERN.search(ocr_text)
    if official_match:
        gstin = official_match.group()
        # Validate checksum for higher confidence
        if validate_gstin_checksum(gstin):
            confidence = 0.98
            method = "regex_official_gstin_checksum_verified"
        else:
            confidence = 0.80
            method = "regex_official_gstin_checksum_failed"

    fields.append({
        "field": "gstin",
        "value": gstin,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Legal Name
    legal_name_match = re.search(r"legal name[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "legal_name",
        "value": legal_name_match.group(1).strip() if legal_name_match else None,
        "confidence": 0.85 if legal_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Trade Name
    trade_name_match = re.search(r"trade name[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "trade_name",
        "value": trade_name_match.group(1).strip() if trade_name_match else None,
        "confidence": 0.85 if trade_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 4. Validity / Registration Date
    date_match = re.search(r"(?:valid from|registration date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "registration_date",
        "value": date_match.group(1).strip() if date_match else None,
        "confidence": 0.80 if date_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields