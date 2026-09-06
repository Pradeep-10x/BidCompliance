import re
from typing import List, Dict, Any

PAN_REGEX = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
GSTIN_REGEX = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")
FRN_REGEX = re.compile(r"\b(?:FRN|FIRM REG(?:ISTRATION)?(?: NO)?)[.:\s]+([0-9A-Z]{5,8})\b", re.IGNORECASE)
TURNOVER_NUM_REGEX = re.compile(r"[₹Rs.\s]*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)")


def extract_ca_fields(ocr_text: str) -> List[Dict[str, Any]]:
    fields = []
    
    # 1. CA Firm Registration Number (FRN)
    frn_match = FRN_REGEX.search(ocr_text)
    if not frn_match:
        frn_match = re.search(r"\b([0-9]{6}[A-Z])\b", ocr_text) # e.g. 153736W
    fields.append({
        "field": "ca_frn_number",
        "value": frn_match.group(1).strip() if frn_match else None,
        "confidence": 0.90 if frn_match else 0.0,
        "extraction_method": "regex_frn_pattern",
    })

    # 2. Vendor PAN from CA certificate
    pan_match = PAN_REGEX.search(ocr_text)
    fields.append({
        "field": "pan_number",
        "value": pan_match.group(0) if pan_match else None,
        "confidence": 0.95 if pan_match else 0.0,
        "extraction_method": "regex_official_pan_format",
    })

    # 3. Vendor GSTIN from CA certificate
    gstin_match = GSTIN_REGEX.search(ocr_text)
    fields.append({
        "field": "gstin",
        "value": gstin_match.group(0) if gstin_match else None,
        "confidence": 0.95 if gstin_match else 0.0,
        "extraction_method": "regex_official_gstin_format",
    })

    # 4. Total Turnover / Max Turnover
    max_to_match = re.search(r"(?:maximum turnover|total turnover)[:\s]+([₹Rs.\s0-9,.]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "maximum_turnover",
        "value": max_to_match.group(1).strip() if max_to_match else None,
        "confidence": 0.85 if max_to_match else 0.0,
        "extraction_method": "regex_anchor",
    })

    # 5. Bid Capacity
    cap_match = re.search(r"(?:bid capacity)[=\s]+([A-Za-z0-9()\-×*+.\s]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "bid_capacity_formula",
        "value": cap_match.group(1).strip() if cap_match else None,
        "confidence": 0.85 if cap_match else 0.0,
        "extraction_method": "regex_anchor",
    })

    return fields
