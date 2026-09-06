import re
from typing import List, Dict, Any

GEM_BID_REGEX = re.compile(r"\b(?:GEM/\d{4}/[A-Z]/\d+|GEM\s+Bid\s+(?:Number|No)[:\s]+[A-Za-z0-9/]+)\b", re.IGNORECASE)


def extract_oem_fields(ocr_text: str) -> List[Dict[str, Any]]:
    fields = []

    # 1. GeM Bid Number Reference
    gem_match = GEM_BID_REGEX.search(ocr_text)
    fields.append({
        "field": "gem_bid_number",
        "value": gem_match.group(0) if gem_match else None,
        "confidence": 0.90 if gem_match else 0.0,
        "extraction_method": "regex_gem_bid_pattern",
    })

    # 2. OEM Name
    oem_match = re.search(r"M/s\s+([A-Za-z0-9 &.,\-_]+?)\s+is the authorized Original Equipment Manufacturer", ocr_text, re.IGNORECASE)
    if not oem_match:
        oem_match = re.search(r"(?:oem name|manufacturer name)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "oem_name",
        "value": oem_match.group(1).strip() if oem_match else None,
        "confidence": 0.85 if oem_match else 0.0,
        "extraction_method": "regex_anchor",
    })

    # 3. Location / Manufacturing Address
    loc_match = re.search(r"(?:location are as follows|location|address)[:\s]+M/s\s*([A-Za-z0-9 &.,\-_/\n]+?)(?:Date|Signature|$)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "manufacturing_location",
        "value": loc_match.group(1).strip() if loc_match else None,
        "confidence": 0.80 if loc_match else 0.0,
        "extraction_method": "regex_anchor",
    })

    # 4. Signatory Email
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", ocr_text)
    fields.append({
        "field": "signatory_email",
        "value": email_match.group(0) if email_match else None,
        "confidence": 0.90 if email_match else 0.0,
        "extraction_method": "regex_email_pattern",
    })

    return fields
