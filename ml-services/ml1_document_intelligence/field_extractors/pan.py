"""PAN Document — Field Extractor.

Extracts: pan_number, name, date_of_birth.
Includes PAN 4th character entity-type validation.
"""
import re
from typing import List, Dict, Any

# Official PAN: 5 alpha + 4 digits + 1 alpha
# 4th character indicates entity type: P=Person, C=Company, H=HUF, etc.
OFFICIAL_PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]{1}\b")

VALID_PAN_ENTITY_TYPES = {
    "A": "Association of Persons (AOP)",
    "B": "Body of Individuals (BOI)",
    "C": "Company",
    "F": "Firm",
    "G": "Government",
    "H": "Hindu Undivided Family (HUF)",
    "L": "Local Authority",
    "J": "Artificial Juridical Person",
    "P": "Individual (Person)",
    "T": "Trust",
}


def validate_pan_entity_type(pan: str) -> str | None:
    """Returns the entity type name if the 4th character is valid, else None."""
    if pan and len(pan) == 10:
        return VALID_PAN_ENTITY_TYPES.get(pan[3].upper())
    return None


def extract_pan_fields(ocr_text: str) -> List[Dict[str, Any]]:
    """Extracts PAN-related fields from OCR text."""
    fields = []

    # 1. PAN Number
    pan_number = None
    confidence = 0.0
    method = "none"
    entity_type = None

    official_match = OFFICIAL_PAN_PATTERN.search(ocr_text)
    if official_match:
        pan_number = official_match.group()
        entity_type = validate_pan_entity_type(pan_number)
        if entity_type:
            confidence = 0.95
            method = "regex_official_pan_entity_validated"
        else:
            confidence = 0.75
            method = "regex_official_pan_entity_unknown"

    fields.append({
        "field": "pan_number",
        "value": pan_number,
        "confidence": confidence,
        "extraction_method": method,
    })

    # Add entity type as a separate field if detected
    if entity_type:
        fields.append({
            "field": "pan_entity_type",
            "value": entity_type,
            "confidence": 0.95,
            "extraction_method": "pan_4th_char_lookup",
        })

    # 2. Cardholder / Holder Name
    name_match = re.search(r"(?:holder name|cardholder(?:'s)? name|name)[:\s]+([A-Za-z0-9 &.,\-_]+)", ocr_text, re.IGNORECASE)
    fields.append({
        "field": "name",
        "value": name_match.group(1).strip() if name_match else None,
        "confidence": 0.85 if name_match else 0.0,
        "extraction_method": "regex_anchor"
    })

    # 3. Date of Birth
    dob_match = re.search(r"(?:date of birth|dob)[:\s]*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})", ocr_text, re.IGNORECASE)
    if not dob_match:
        dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b", ocr_text)

    fields.append({
        "field": "date_of_birth",
        "value": dob_match.group(1) if dob_match else None,
        "confidence": 0.80 if dob_match else 0.0,
        "extraction_method": "regex_date_format"
    })

    return fields