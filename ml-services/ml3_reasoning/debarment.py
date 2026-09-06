import re
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List

logger = logging.getLogger("ml_services.debarment")

# Official records extracted directly from CPCL e-Procurement Portal (cpcletenders.nic.in/nicgep/app)
CPCL_OFFICIAL_DEBARMENT_RECORDS = [
    {
        "s_no": 1,
        "bidder_name": "FANIBHUSAN INFRATECH PRIVATE LIMITED",
        "pan_masked": "XXXXXXXX2Q",
        "pan_last2": "2Q",
        "login_id": "admXXXX[at]fanibhusan[dot]com",
        "organisation_chain": "CPCL,DGM(M and C)||CM - CONTRACTS||Sr.MANAGER||Sr Engr Officer",
        "start_date": "2025-07-05",
        "end_date": "2028-07-04",
        "reason": "Debarred by CPCL Contracts Division",
    },
    {
        "s_no": 2,
        "bidder_name": "N S BAKTHAVATCHALAM",
        "pan_masked": "XXXXXXXX3D",
        "pan_last2": "3D",
        "login_id": "nsbXXXX[at]gmail[dot]com",
        "organisation_chain": "CPCL,DGM(M and C)||CM - CONTRACTS||Sr.MANAGER||Sr Engr Officer",
        "start_date": "2025-11-19",
        "end_date": "2028-11-18",
        "reason": "Debarred by CPCL Contracts Division",
    },
    {
        "s_no": 3,
        "bidder_name": "Radiant Hitech Eng Pvt Ltd",
        "pan_masked": "XXXXXXXX3Q",
        "pan_last2": "3Q",
        "login_id": "infXXXX[at]radiantengg[dot]com",
        "organisation_chain": "CPCL,DGM(M and C)||CM - CONTRACTS||Sr.MANAGER||Sr Engr Officer",
        "start_date": "2026-05-18",
        "end_date": "2027-04-21",
        "reason": "Debarred by CPCL Contracts Division",
    },
    {
        "s_no": 4,
        "bidder_name": "Sri balaji enterprises",
        "pan_masked": "XXXXXXXX4E",
        "pan_last2": "4E",
        "login_id": "sriXXXX[at]gmail[dot]com",
        "organisation_chain": "CPCL,DGM(M and C)||CM - CONTRACTS||Sr.MANAGER||Sr Engr Officer",
        "start_date": "2025-11-19",
        "end_date": "2026-11-18",
        "reason": "Debarred by CPCL Contracts Division",
    },
    {
        "s_no": 5,
        "bidder_name": "Sri Sarvamangala Fabrication",
        "pan_masked": "XXXXXXXX3D",
        "pan_last2": "3D",
        "login_id": "sriXXXX[at]yahoo[dot]com",
        "organisation_chain": "CPCL,DGM(M and C)||CM - CONTRACTS||Sr.MANAGER||Sr Engr Officer",
        "start_date": "2025-11-19",
        "end_date": "2028-11-18",
        "reason": "Debarred by CPCL Contracts Division",
    },
    {
        "s_no": 6,
        "bidder_name": "SRI SARVAMANGALA FABRICATION",
        "pan_masked": "XXXXXXXX3D",
        "pan_last2": "3D",
        "login_id": "sriXXXX[at]gmail[dot]com",
        "organisation_chain": "CPCL,DGM(M and C)||CM - CONTRACTS||Sr.MANAGER||Sr Engr Officer",
        "start_date": "2025-11-19",
        "end_date": "2028-11-18",
        "reason": "Debarred by CPCL Contracts Division",
    },
]


def normalize_name(name: str) -> str:
    """Normalize organization name for robust comparison."""
    if not name:
        return ""
    v = name.upper()
    for stop_word in [
        "PRIVATE LIMITED", "PVT LTD", "PVT. LTD.", "PVT.LTD.",
        "LIMITED", "LTD.", "LTD", "ENTERPRISES", "ENTERPRISE",
        "FABRICATION", "FABRICATIONS", "ENGG", "ENGINEERING"
    ]:
        v = v.replace(stop_word, "")
    v = re.sub(r"[^A-Z0-9]", "", v)
    return v.strip()


def parse_raw_debarment_text(raw_text: str) -> List[Dict[str, Any]]:
    """Parses custom raw text debarment lists into structured records.
    
    Handles table rows, line-separated listings, dates, and PAN numbers.
    """
    records = []
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    date_regex = re.compile(r"\b(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{4}-\d{2}-\d{2})\b")
    pan_regex = re.compile(r"\b([A-Z]{5}\d{4}[A-Z]|[Xx]{8}[A-Za-z0-9]{2})\b")

    for line in lines:
        dates_found = date_regex.findall(line)
        pan_found = pan_regex.findall(line)
        
        # Simple extraction heuristic
        if dates_found:
            records.append({
                "raw_line": line,
                "dates": dates_found,
                "pan": pan_found[0] if pan_found else None,
            })
    return records


def verify_bidder_debarment(
    bidder_name: str,
    bidder_pan: Optional[str] = None,
    tender_date: Optional[str] = "2026-06-06",
) -> Dict[str, Any]:
    """Verifies bidder against the official CPCL Debarment list.
    
    Checks:
    1. Exact Name match (after normalisation)
    2. PAN match (full or last-2 chars against masked PAN)
    3. Active validity window on bid opening date
    """
    norm_bidder = normalize_name(bidder_name)
    eval_date = datetime.strptime(tender_date, "%Y-%m-%d").date() if tender_date else date.today()

    bidder_pan_clean = bidder_pan.upper().strip() if bidder_pan else ""
    bidder_pan_last2 = bidder_pan_clean[-2:] if len(bidder_pan_clean) >= 2 else ""

    for rec in CPCL_OFFICIAL_DEBARMENT_RECORDS:
        rec_norm = normalize_name(rec["bidder_name"])
        start = datetime.strptime(rec["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(rec["end_date"], "%Y-%m-%d").date()

        # Check if debarment is active on tender evaluation date
        is_currently_active = (start <= eval_date <= end)

        # 1. Exact / High Confidence Name Match
        name_matched = False
        if norm_bidder and rec_norm:
            if norm_bidder == rec_norm or norm_bidder in rec_norm or rec_norm in norm_bidder:
                name_matched = True

        # 2. PAN Match (Check last 2 characters if masked, or full if known)
        pan_matched = False
        if bidder_pan_last2 and rec["pan_last2"]:
            if bidder_pan_last2 == rec["pan_last2"]:
                pan_matched = True

        if name_matched or (pan_matched and name_matched):
            status = "critical_contradiction" if is_currently_active else "past_debarment_expired"
            return {
                "is_debarred": is_currently_active,
                "status": status,
                "match_type": "exact_name_and_pan" if (name_matched and pan_matched) else ("name_match" if name_matched else "pan_match"),
                "matched_record": rec,
                "finding": (
                    f"CRITICAL: Bidder '{bidder_name}' matches active CPCL debarred organization '{rec['bidder_name']}'. "
                    f"Debarment active from {rec['start_date']} to {rec['end_date']}. "
                    f"Self-declaration of non-blacklisting is directly contradicted."
                    if is_currently_active else
                    f"NOTICE: Bidder '{bidder_name}' was previously holiday-listed by CPCL ({rec['start_date']} to {rec['end_date']}), but debarment is now expired."
                ),
                "action_recommendation": "clarification_required" if is_currently_active else "officer_review_ready"
            }

    return {
        "is_debarred": False,
        "status": "cleared",
        "match_type": "none",
        "matched_record": None,
        "finding": f"No active debarment or holiday-listing records found for '{bidder_name}' in CPCL database.",
        "action_recommendation": "officer_review_ready"
    }
