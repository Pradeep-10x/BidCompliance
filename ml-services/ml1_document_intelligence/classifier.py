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
    "bis_certificate_or_licence": [
        r"bureau\s+of\s+indian\s+standards",
        r"product\s+certification",
        r"standard\s+mark",
        r"isi\s+mark",
        r"\bbis\b",
        r"bis[-_\s]*inspired",
        r"bis[-_\s]*style",
        r"syn[-_]8?1?bis",
        r"manufacturing\s+unit",
        r"is\s+number",
        r"licence\s+no",
    ],
    "dpiit_startup_recognition_certificate": [
        r"department\s+for\s+promotion\s+of\s+industry",
        r"startup\s+india",
        r"startup\s+recognition",
        r"dpii?f?t?",
        r"dpii?f?t?[-_\s]*inspired",
        r"dpii?f?t?[-_\s]*style",
        r"syn[-_]dpii?f?t?",
        r"certificate\s+of\s+recognition",
        r"recognition\s+details",
    ],
    "ca_turnover_certificate": [
        r"chartered\s+accountant",
        r"to\s+whomsoever\s+it\s+may\s+concern",
        r"books\s+of\s+accounts",
        r"total\s+turnover",
        r"financial\s+year",
        r"bid\s+capacity",
        r"maximum\s+turnover",
        r"\bfrn\b",
        r"turnover\s+certificate",
        r"annual\s+turnover",
    ],
    "oem_authorization_certificate": [
        r"oem\s+certificate",
        r"original\s+equipment\s+manufacturer",
        r"authorized\s+original\s+equipment\s+manufacturer",
        r"gem\s+bid\s+number",
        r"solution\s+to\s+be\s+supplied",
        r"signature\s+of\s+authorized\s+signatory\s+from\s+oem",
        r"certificate\s+of\s+authorization",
        r"undertaking\s+from\s+oem",
    ],
    "make_in_india_declaration": [
        r"make[-_\s]*in[-_\s]*india",
        r"preference\s+to\s+make[-_\s]*in[-_\s]*india",
        r"local\s+content",
        r"class\s*1\s+local\s+supplier",
        r"class\s*2\s+local\s+supplier",
        r"rule\s+175\(1\)\(i\)\(h\)",
        r"rule\s+151\s*\(iii\)",
        r"local\s+value\s+addition",
        r"country\s+of\s+origin",
        r"percentage\s+of\s+local\s+content",
    ],
    "bidder_legal_financial_standing": [
        r"bidder\s+legal\s+&\s+financial\s+standing",
        r"not\s+under\s+liquidation",
        r"court\s+receivership",
        r"bankrupt",
        r"involvement\s+in\s+illegal\s+activities",
        r"financial\s+frauds",
        r"prosecuted\s+or\s+suffered\s+any\s+penalty",
        r"suspended\s*/\s*delisted\s*/\s*blacklisted",
        r"rescinded/abandoned\s+any\s+contract",
    ],
    "debarment_declaration": [
        r"debarment,\s+suspension,\s+ineligibility",
        r"voluntary\s+exclusion",
        r"executive\s+order\s+12549",
        r"sba\s+form\s+1624",
        r"declaration\s+of\s+blacklisting",
        r"holiday\s+listing",
        r"non[-_\s]*blacklisting",
    ],
}


def classify_document(ocr_text: str) -> dict:
    """Classifies a document based on signature pattern presence in its OCR text."""
    if not ocr_text or not isinstance(ocr_text, str):
        return {
            "document_type": "unknown_or_other",
            "confidence": 0.0,
            "classification_method": "keyword_rule_baseline",
            "alternatives": [],
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

    # Normalize scores: 3+ distinct keyword matches = 1.0 confidence
    scores = {
        k: round(min(1.0, count / 3.0), 2) for k, count in matches_count.items()
    }

    # Build ranked alternatives (excluding best type, only with score > 0)
    alternatives = [
        {"document_type": k, "confidence": v}
        for k, v in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if k != best_type and v > 0.0
    ]

    if best_matches == 0:
        return {
            "document_type": "unknown_or_other",
            "confidence": 0.0,
            "classification_method": "keyword_rule_baseline",
            "alternatives": [],
            "scores": scores,
        }

    return {
        "document_type": best_type,
        "confidence": scores[best_type],
        "classification_method": "keyword_rule_baseline",
        "alternatives": alternatives,
        "scores": scores,
    }
