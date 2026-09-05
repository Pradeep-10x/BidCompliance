DOCUMENT_SIGNATURES = {
    "gst_registration_certificate": [
        "goods and services tax", "gstin", "registration certificate",
        "form gst reg", "principal place of business"
    ],
    "pan_document": [
        "income tax department", "permanent account number", "govt. of india"
    ],
    "udyam_registration_certificate": [
        "udyam registration", "ministry of micro, small and medium enterprises",
        "udyam-", "type of enterprise"
    ],
    "mca_incorporation_certificate": [
        "certificate of incorporation", "ministry of corporate affairs",
        "corporate identity number", "companies act"
    ],
}


def classify_document(ocr_text: str) -> dict:
    """Classifies a document based on keyword presence in its OCR'd text."""
    text_lower = ocr_text.lower()
    scores = {}

    for doc_type, keywords in DOCUMENT_SIGNATURES.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        scores[doc_type] = matches / len(keywords)

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score == 0:
        return {
            "document_type": "unknown_or_other",
            "confidence": 0.0,
            "scores": {k: round(v, 2) for k, v in scores.items()}
        }

    return {
        "document_type": best_type,
        "confidence": round(best_score, 2),
        "scores": {k: round(v, 2) for k, v in scores.items()}
    }