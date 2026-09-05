import re

DOCUMENT_SIGNATURES = {
    "gst_registration_certificate": [
        r"goods\s+and\s+services\s+tax",
        r"\bgst(?:in)?\b",
        r"form\s+gst\s+reg",
        r"principal\s+place\s+of\s+business",
        r"tax\s+registration",
        r"gst[-_\s]*inspired",
        r"gst[-_\s]*style",
        r"@stin",
        r"syn[-_]gst",
    ],
    "pan_document": [
        r"income\s+tax\s+department",
        r"permanent\s+account\s+number",
        r"govt\.?\s+of\s+india",
        r"\bpan\b",
        r"identity\s+card",
        r"pan[-_\s]*inspired",
        r"pan[-_\s]*style",
        r"syn[-_]pan",
        r"cardholder",
    ],
    "udyam_registration_certificate": [
        r"udyam\s+registration",
        r"ministry\s+of\s+micro",
        r"small\s+and\s+medium\s+enterprises",
        r"\budyam\b",
        r"type\s+of\s+enterprise",
        r"enterprise\s+registration",
        r"udyam[-_\s]*inspired",
        r"udyam[-_\s]*style",
        r"syn[-_]udyam",
        r"\bmsme\b",
    ],
    "mca_incorporation_certificate": [
        r"certificate\s+of\s+incorporation",
        r"ministry\s+of\s+corporate\s+affairs",
        r"corporate\s+identity\s+number",
        r"companies\s+act",
        r"\bcin\b",
        r"mca[-_\s]*inspired",
        r"mca[-_\s]*style",
        r"syn[-_]mca",
        r"registrar\s+of\s+companies",
        r"is\s+incorporated",
    ],
}


def classify_document(ocr_text: str) -> dict:
    """Classifies a document based on signature pattern presence in its OCR text."""
    if not ocr_text or not isinstance(ocr_text, str):
        return {
            "document_type": "unknown_or_other",
            "confidence": 0.0,
            "scores": {k: 0.0 for k in DOCUMENT_SIGNATURES},
        }

    text_lower = ocr_text.lower()
    matches_count = {}

    for doc_type, patterns in DOCUMENT_SIGNATURES.items():
        count = 0
        for pattern in patterns:
            if re.search(pattern, text_lower):
                count += 1
        matches_count[doc_type] = count

    best_type = max(matches_count, key=matches_count.get)
    best_matches = matches_count[best_type]

    # Normalize scores: 3+ distinct keyword matches = 0.95+ confidence
    scores = {
        k: round(min(1.0, count / 3.0), 2) for k, count in matches_count.items()
    }

    if best_matches == 0:
        return {
            "document_type": "unknown_or_other",
            "confidence": 0.0,
            "scores": scores,
        }

    return {
        "document_type": best_type,
        "confidence": scores[best_type],
        "scores": scores,
    }