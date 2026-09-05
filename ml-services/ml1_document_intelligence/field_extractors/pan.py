import re

PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]{1}\b")


def extract_pan_fields(ocr_text: str) -> list:
    fields = []

    pan_match = PAN_PATTERN.search(ocr_text)
    fields.append({
        "field_name": "pan_number",
        "field_value": pan_match.group() if pan_match else None,
        "confidence": 0.95 if pan_match else 0.0,
        "extraction_method": "regex_pan_format"
    })

    dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", ocr_text)
    fields.append({
        "field_name": "date_of_birth",
        "field_value": dob_match.group(1) if dob_match else None,
        "confidence": 0.75 if dob_match else 0.0,
        "extraction_method": "regex_date_format"
    })

    return fields