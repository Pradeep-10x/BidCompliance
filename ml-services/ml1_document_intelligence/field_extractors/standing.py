import re
from typing import List, Dict, Any


def extract_standing_fields(ocr_text: str) -> List[Dict[str, Any]]:
    fields = []

    # 1. Insolvency / Liquidation Status
    not_bankrupt = bool(re.search(r"not\s+be\s+(?:under\s+liquidation|bankrupt)", ocr_text, re.IGNORECASE))
    fields.append({
        "field": "liquidation_bankruptcy_declaration",
        "value": "Clean (Not under liquidation/bankruptcy)" if not_bankrupt else "Unverified",
        "confidence": 0.90 if not_bankrupt else 0.0,
        "extraction_method": "regex_statutory_declaration",
    })

    # 2. Criminal / Illegal Activity
    clean_track = bool(re.search(r"clean|should not have any involvement in illegal activities", ocr_text, re.IGNORECASE))
    fields.append({
        "field": "criminal_fraud_record_declaration",
        "value": "Clean (No illegal activities or court cases)" if clean_track else "Unverified",
        "confidence": 0.90 if clean_track else 0.0,
        "extraction_method": "regex_statutory_declaration",
    })

    # 3. Delisting / Blacklisting Self-Declaration
    not_blacklisted = bool(re.search(r"not\s+have\s+been\s+(?:suspended|delisted|blacklisted)", ocr_text, re.IGNORECASE))
    fields.append({
        "field": "blacklisting_holiday_listing_declaration",
        "value": "Clean (Not suspended/delisted/blacklisted)" if not_blacklisted else "Unverified",
        "confidence": 0.95 if not_blacklisted else 0.0,
        "extraction_method": "regex_statutory_declaration",
    })

    return fields
