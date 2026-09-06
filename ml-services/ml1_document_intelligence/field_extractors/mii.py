import re
from typing import List, Dict, Any

LOCAL_CONTENT_REGEX = re.compile(r"(\d{1,3}(?:\.\d{1,2})?)\s*%")


def extract_mii_fields(ocr_text: str) -> List[Dict[str, Any]]:
    fields = []

    # 1. Supplier Classification (Class 1 vs Class 2)
    supplier_class = None
    if re.search(r"class\s*[-_]?\s*1", ocr_text, re.IGNORECASE):
        supplier_class = "Class-I Local Supplier"
    elif re.search(r"class\s*[-_]?\s*2", ocr_text, re.IGNORECASE):
        supplier_class = "Class-II Local Supplier"
    
    fields.append({
        "field": "supplier_class",
        "value": supplier_class,
        "confidence": 0.85 if supplier_class else 0.0,
        "extraction_method": "regex_rule",
    })

    # 2. Local Content Percentage
    content_match = None
    lc_matches = re.finditer(r"(?:local content|total value \(in %\))[:\s]*(\d{1,3}(?:\.\d{1,2})?)\s*%", ocr_text, re.IGNORECASE)
    for m in lc_matches:
        content_match = m.group(1)
    if not content_match:
        # Check any percentage in text
        pct_match = LOCAL_CONTENT_REGEX.search(ocr_text)
        if pct_match:
            content_match = pct_match.group(1)

    fields.append({
        "field": "local_content_percentage",
        "value": f"{content_match}%" if content_match else None,
        "confidence": 0.85 if content_match else 0.0,
        "extraction_method": "regex_percentage_pattern",
    })

    # 3. Country of Origin
    origin_match = re.search(r"(?:country of origin)[:\s]+([A-Za-z]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "country_of_origin",
        "value": origin_match.group(1).strip() if origin_match else "India",
        "confidence": 0.80,
        "extraction_method": "regex_anchor_with_default",
    })

    # 4. GFR Rule 175 / 151 compliance flag
    has_gfr = bool(re.search(r"rule\s+(?:175|151)", ocr_text, re.IGNORECASE))
    fields.append({
        "field": "gfr_code_of_integrity_pledge",
        "value": "Yes" if has_gfr else "No",
        "confidence": 0.90 if has_gfr else 0.50,
        "extraction_method": "regex_statutory_rule",
    })

    return fields
