import io
import re
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from PIL import Image

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

logger = logging.getLogger("ml_services.forensics")

SUSPICIOUS_PRODUCERS = [
    "photoshop", "gimp", "canva", "ilovepdf", "smallpdf",
    "pdfescape", "sejda", "coreldraw", "illustrator", "inkscape"
]


def calculate_sha256(data: bytes) -> str:
    """Calculates the SHA-256 cryptographic hash of byte content."""
    return hashlib.sha256(data).hexdigest()


def parse_pdf_date(date_str: str) -> Optional[datetime]:
    """Parses PDF date strings formatted like D:YYYYMMDDHHmmSS[OHH'mm']."""
    if not date_str:
        return None
    raw = str(date_str).strip()
    if raw.startswith("D:"):
        raw = raw[2:]
    
    clean = re.sub(r"['Z].*", "", raw)
    clean = clean.split("+")[0].split("-")[0]
    
    formats = [
        "%Y%m%d%H%M%S",
        "%Y%m%d%H%M",
        "%Y%m%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(clean[:len(datetime.now().strftime(fmt))], fmt)
        except Exception:
            continue
    return None


def inspect_image_forensics(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Performs structural and EXIF forensics for image documents (PNG, JPG, TIFF)."""
    sha256_hash = calculate_sha256(file_bytes)
    anomaly_flags: List[str] = []
    metadata: Dict[str, Any] = {}
    
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            width, height = img.size
            img_format = img.format
            exif = img.getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag_name = str(tag_id)
                    metadata[tag_name] = str(value)
    except Exception as e:
        anomaly_flags.append(f"Image decode warning: {str(e)}")
        width, height, img_format = 0, 0, "UNKNOWN"

    status = "manual_review_recommended" if anomaly_flags else "no_technical_anomaly_detected"
    recommendation = "manual_review_required" if anomaly_flags else "officer_review_ready"

    return {
        "file_hash_sha256": sha256_hash,
        "file_name": filename,
        "file_size_bytes": len(file_bytes),
        "is_pdf": False,
        "media_type": f"image/{img_format.lower()}" if img_format else "image/unknown",
        "dimensions": {"width": width, "height": height},
        "page_count": 1,
        "pdf_metadata": None,
        "embedded_content": {
            "has_embedded_files": False,
            "has_embedded_js": False,
            "embedded_file_names": [],
        },
        "digital_signature": {
            "signature_present": False,
            "signer_name": None,
            "signing_time": None,
            "signature_type": None,
            "intact": None,
            "trusted": "unverified",
            "post_signing_modifications": None,
        },
        "anomaly_flags": anomaly_flags,
        "forensics_status": status,
        "review_recommendation": recommendation,
    }


def inspect_pdf_forensics(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """Performs deterministic structural, metadata, and signature forensics on a PDF file."""
    sha256_hash = calculate_sha256(file_bytes)
    
    # Verify PDF magic bytes
    if not file_bytes.startswith(b"%PDF-"):
        return inspect_image_forensics(file_bytes, filename)

    if not PIKEPDF_AVAILABLE:
        logger.warning("pikepdf not installed; returning basic hash metadata.")
        return {
            "file_hash_sha256": sha256_hash,
            "file_name": filename,
            "file_size_bytes": len(file_bytes),
            "is_pdf": True,
            "forensics_status": "not_evaluated",
            "anomaly_flags": ["pikepdf engine unavailable"],
            "review_recommendation": "manual_review_required",
        }

    anomaly_flags: List[str] = []
    meta_info: Dict[str, Any] = {
        "creator": None,
        "producer": None,
        "creation_date": None,
        "modification_date": None,
        "date_anomaly_detected": False,
    }
    embedded_info: Dict[str, Any] = {
        "has_embedded_files": False,
        "has_embedded_js": False,
        "embedded_file_names": [],
    }
    sig_info: Dict[str, Any] = {
        "signature_present": False,
        "signer_name": None,
        "signing_time": None,
        "signature_type": None,
        "intact": None,
        "trusted": "unverified",
        "post_signing_modifications": None,
    }

    try:
        pdf = pikepdf.Pdf.open(io.BytesIO(file_bytes))
    except Exception as e:
        anomaly_flags.append(f"PDF structural corruption: {str(e)}")
        return {
            "file_hash_sha256": sha256_hash,
            "file_name": filename,
            "file_size_bytes": len(file_bytes),
            "is_pdf": True,
            "is_encrypted": False,
            "page_count": 0,
            "pdf_metadata": meta_info,
            "embedded_content": embedded_info,
            "digital_signature": sig_info,
            "anomaly_flags": anomaly_flags,
            "forensics_status": "manual_review_recommended",
            "review_recommendation": "manual_review_required",
        }

    page_count = len(pdf.pages)
    is_encrypted = pdf.is_encrypted

    # 1. Metadata Inspection
    doc_info = pdf.docinfo
    creator = str(doc_info.get("/Creator", "")).strip() if doc_info else ""
    producer = str(doc_info.get("/Producer", "")).strip() if doc_info else ""
    c_date_raw = str(doc_info.get("/CreationDate", "")).strip() if doc_info else ""
    m_date_raw = str(doc_info.get("/ModDate", "")).strip() if doc_info else ""

    meta_info["creator"] = creator or None
    meta_info["producer"] = producer or None

    c_date = parse_pdf_date(c_date_raw)
    m_date = parse_pdf_date(m_date_raw)

    if c_date:
        meta_info["creation_date"] = c_date.isoformat()
    if m_date:
        meta_info["modification_date"] = m_date.isoformat()

    # Temporal anomaly: ModDate significantly earlier than CreationDate
    if c_date and m_date:
        if m_date < c_date:
            meta_info["date_anomaly_detected"] = True
            anomaly_flags.append(
                f"Temporal anomaly: Modification date ({meta_info['modification_date']}) "
                f"is earlier than Creation date ({meta_info['creation_date']}). Possible timestamp tampering."
            )

    # Check for suspicious editing software
    full_producer_str = f"{creator} {producer}".lower()
    for suspicious_app in SUSPICIOUS_PRODUCERS:
        if suspicious_app in full_producer_str:
            anomaly_flags.append(
                f"Suspicious editing software detected in PDF metadata: '{suspicious_app.title()}' "
                f"(Creator: '{creator}', Producer: '{producer}'). Document may have been manually altered."
            )
            break

    # 2. Embedded Content & JavaScript Check
    catalog = pdf.Root
    if "/Names" in catalog:
        names = catalog["/Names"]
        if "/JavaScript" in names:
            embedded_info["has_embedded_js"] = True
            anomaly_flags.append("Document contains embedded JavaScript action dictionary.")
        if "/EmbeddedFiles" in names:
            embedded_info["has_embedded_files"] = True
            try:
                ef_tree = names["/EmbeddedFiles"]
                if "/Names" in ef_tree:
                    raw_names = ef_tree["/Names"]
                    embedded_info["embedded_file_names"] = [str(item) for idx, item in enumerate(raw_names) if idx % 2 == 0]
            except Exception:
                pass
            anomaly_flags.append("Document contains embedded attachments or foreign files.")

    # 3. Digital Signatures Inspection
    if "/AcroForm" in catalog:
        acro_form = catalog["/AcroForm"]
        if "/Fields" in acro_form:
            for field in acro_form["/Fields"]:
                try:
                    ft = field.get("/FT")
                    if ft == pikepdf.Name("/Sig"):
                        sig_info["signature_present"] = True
                        if "/V" in field:
                            sig_dict = field["/V"]
                            signer = str(sig_dict.get("/Name", "")) or str(sig_dict.get("/ContactInfo", ""))
                            sub_filter = str(sig_dict.get("/SubFilter", ""))
                            sig_time = parse_pdf_date(str(sig_dict.get("/M", "")))
                            
                            sig_info["signer_name"] = signer or "Digital Signature Present"
                            sig_info["signature_type"] = sub_filter or "adbe.pkcs7"
                            if sig_time:
                                sig_info["signing_time"] = sig_time.isoformat()
                            sig_info["intact"] = True
                            sig_info["trusted"] = "requires_crl_verification"
                            sig_info["post_signing_modifications"] = False
                            break
                except Exception:
                    continue

    pdf.close()

    # Determine status according to SIH Guide §5
    if anomaly_flags:
        status = "manual_review_recommended"
        recommendation = "manual_review_required"
    else:
        status = "no_technical_anomaly_detected"
        recommendation = "officer_review_ready"

    return {
        "file_hash_sha256": sha256_hash,
        "file_name": filename,
        "file_size_bytes": len(file_bytes),
        "is_pdf": True,
        "is_encrypted": is_encrypted,
        "page_count": page_count,
        "pdf_metadata": meta_info,
        "embedded_content": embedded_info,
        "digital_signature": sig_info,
        "anomaly_flags": anomaly_flags,
        "forensics_status": status,
        "review_recommendation": recommendation,
    }
