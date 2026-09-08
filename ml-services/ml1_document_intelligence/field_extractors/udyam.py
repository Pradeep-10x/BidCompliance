"""Udyam/MSME Registration Certificate — Field Extractor.

Extracts: udyam_registration_number, enterprise_name, enterprise_type.
"""
import re
from typing import List, Dict, Any

# Official Udyam format: UDYAM-XX-99-9999999
OFFICIAL_UDYAM_PATTERN = re.compile(r"UDYAM-[A-Z]{2}-\d{2}-\d{7}")
# OCR commonly duplicates the leading S in the synthetic watermark/typeface.
SYNTHETIC_UDYAM_PATTERN = re.compile(r"\bS+YN[-_]UDYAM[-_]\d+\b", re.IGNORECASE)


def extract_udyam_fields(ocr_text: str) -> List[Dict[str, Any]]:
    """Extracts Udyam/MSME registration fields from OCR text."""
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
            udyam_number = re.sub(r"^S+YN", "SYN", synthetic_match.group().upper())
            confidence = 0.90
            method = "regex_synthetic_udyam_format"

    fields.append({
        "field": "udyam_registration_number",
        "value": udyam_number,
        "confidence": confidence,
        "extraction_method": method
    })

    # 2. Enterprise Name
    enterprise_name_match = re.search(r"(?:name of enterprise|enterprise name)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "enterprise_name",
        "value": enterprise_name_match.group(1).strip() if enterprise_name_match else None,
        "confidence": 0.80 if enterprise_name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Enterprise Type (Micro/Small/Medium)
    enterprise_type_match = re.search(r"(?:type of enterprise|enterprise type)[:\s]+(Micro|Small|Medium|[A-Za-z]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "enterprise_type",
        "value": enterprise_type_match.group(1).strip().title() if enterprise_type_match else None,
        "confidence": 0.80 if enterprise_type_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    return fields
