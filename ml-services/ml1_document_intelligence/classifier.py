"""
Document Classification — Keyword/Pattern-Based Baseline Classifier.

Classifies bidder documents into the taxonomy required by the PRD using
deterministic pattern matching on OCR text. Each document type has a curated
set of Indian government procurement-specific patterns.

Classification method: keyword_rule_baseline
Confidence model:      count / total_patterns  (no more count/3 ceiling)
Minimum threshold:     >= 2 pattern matches required to assign a type
"""

import re

# ─────────────────────────────────────────────────────────────────────
# Document Signature Patterns — Indian Government Procurement Documents
# ─────────────────────────────────────────────────────────────────────
# Each pattern list contains ONLY real-world patterns that appear in
# genuine Indian government documents. No synthetic/test patterns.

DOCUMENT_SIGNATURES = {
    "gst_registration_certificate": [
        r"goods\s+and\s+services\s+tax",
        r"\bgst(?:in)?\b",
        r"form\s+gst\s+reg",
        r"principal\s+place\s+of\s+business",
        r"tax\s+registration",
        r"central\s+goods\s+and\s+services\s+tax",
        r"state\s+goods\s+and\s+services\s+tax",
        r"certificate\s+of\s+registration",
        r"trade\s+name",
        r"legal\s+name",
    ],
    "pan_document": [
        r"income\s+tax\s+department",
        r"permanent\s+account\s+number",
        r"govt\.?\s+of\s+india",
        r"\bpan\b",
        r"identity\s+card",
        r"cardholder",
        r"date\s+of\s+birth",
        r"father['']?s?\s+name",
        r"signature",
    ],
    "udyam_registration_certificate": [
        r"udyam\s+registration",
        r"ministry\s+of\s+micro",
        r"small\s+and\s+medium\s+enterprises",
        r"\budyam\b",
        r"type\s+of\s+enterprise",
        r"enterprise\s+registration",
        r"\bmsme\b",
        r"major\s+activity",
        r"nic\s+code",
        r"date\s+of\s+(?:incorporation|commencement)",
    ],
    "mca_incorporation_certificate": [
        r"certificate\s+of\s+incorporation",
        r"ministry\s+of\s+corporate\s+affairs",
        r"corporate\s+identity\s+number",
        r"companies\s+act",
        r"\bcin\b",
        r"registrar\s+of\s+companies",
        r"is\s+(?:hereby\s+)?incorporated",
        r"authorized\s+capital",
        r"paid[\s-]?up\s+capital",
        r"registered\s+office",
    ],
    "bis_certificate_or_licence": [
        r"bureau\s+of\s+indian\s+standards",
        r"product\s+certification",
        r"standard\s+mark",
        r"isi\s+mark",
        r"\bbis\b",
        r"manufacturing\s+unit",
        r"is\s+number",
        r"licence\s+no",
        r"bis\s+care",
        r"conformity\s+assessment",
    ],
    "dpiit_startup_recognition_certificate": [
        r"department\s+for\s+promotion\s+of\s+industry",
        r"startup\s+india",
        r"startup\s+recognition",
        r"\bdpiit\b",
        r"certificate\s+of\s+recognition",
        r"recognition\s+details",
        r"recognition\s+number",
        r"inter[\s-]?ministerial\s+board",
        r"eligible\s+(?:entity|startup)",
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
        r"bidder\s+legal\s+\&\s+financial\s+standing",
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
        # Indian-specific debarment and holiday-listing patterns
        r"declaration\s+of\s+(?:non[\s-]?)?blacklisting",
        r"holiday\s+listing",
        r"non[-_\s]*blacklisting",
        r"debarment",
        r"(?:cppp|gem|government\s+e[\s-]?marketplace)",
        r"e[\s-]?procurement\s+portal",
        r"banned\s+(?:bidder|firm|vendor)",
        r"self[\s-]?declaration",
        r"not\s+(?:been\s+)?(?:debarred|blacklisted|holiday[\s-]?listed)",
    ],
}

# Minimum number of pattern matches required to classify a document.
# Prevents false classifications from accidental keyword hits.
MIN_MATCH_THRESHOLD = 2


def classify_document(ocr_text: str) -> dict:
    """Classifies a document based on signature pattern presence in its OCR text.

    Returns:
        dict with document_type, confidence, classification_method,
        alternatives and per-type scores.
    """
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

    # Confidence = matches / total patterns for that document type
    # This gives a meaningful ratio instead of the old count/3 ceiling
    scores = {}
    for doc_type, count in matches_count.items():
        total_patterns = len(DOCUMENT_SIGNATURES[doc_type])
        scores[doc_type] = round(min(1.0, count / max(total_patterns, 1)), 2)

    # Build ranked alternatives (excluding best type, only with score > 0)
    alternatives = [
        {"document_type": k, "confidence": v}
        for k, v in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if k != best_type and v > 0.0
    ]

    # Require minimum match threshold to prevent false classifications
    if best_matches < MIN_MATCH_THRESHOLD:
        return {
            "document_type": "unknown_or_other",
            "confidence": 0.0,
            "classification_method": "keyword_rule_baseline",
            "alternatives": alternatives if best_matches > 0 else [],
            "scores": scores,
        }

    return {
        "document_type": best_type,
        "confidence": scores[best_type],
        "classification_method": "keyword_rule_baseline",
        "alternatives": alternatives,
        "scores": scores,
    }
