from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from .config import CANVAS_SIZE, FONT_CANDIDATES, BOLD_FONT_CANDIDATES, WATERMARK

MARGIN = 70
INK = (32, 32, 32)
MUTED = (90, 90, 90)
LINE = (170, 170, 170)
LIGHT = (245, 245, 245)
ACCENT = (120, 30, 30)


@lru_cache(maxsize=32)
def _font(size: int, bold: bool = False):
    candidates = BOLD_FONT_CANDIDATES if bold else FONT_CANDIDATES
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _text(draw, xy, text, size=20, bold=False, fill=INK, anchor=None):
    draw.text(xy, str(text), font=_font(size, bold), fill=fill, anchor=anchor)


def _wrapped_lines(draw, text, font, max_width):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        test = word if not current else current + " " + word
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_wrapped(draw, x, y, text, max_width, size=18, bold=False, line_gap=8, fill=INK):
    font = _font(size, bold)
    lines = _wrapped_lines(draw, text, font, max_width)
    line_h = size + line_gap
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h
    return y


def _draw_header(draw, title, subtitle, doc_label):
    draw.rounded_rectangle((45, 35, 1195, 145), radius=12, outline=LINE, width=3, fill=(252, 252, 252))
    draw.ellipse((65, 58, 120, 113), outline=INK, width=3)
    _text(draw, (145, 48), "DEMO DOCUMENT AUTHORITY", size=28, bold=True)
    _text(draw, (145, 88), "Fictional research format — no official branding", size=17, fill=MUTED)
    _text(draw, (620, 185), title, size=28, bold=True, anchor="ma")
    _text(draw, (620, 220), subtitle, size=16, fill=MUTED, anchor="ma")
    _text(draw, (MARGIN, 250), doc_label, size=16, bold=True, fill=ACCENT)


def _section(draw, x, y, w, title):
    draw.rounded_rectangle((x, y, x + w, y + 44), radius=7, fill=LIGHT, outline=LINE, width=2)
    _text(draw, (x + 16, y + 10), title, size=18, bold=True)
    return y + 58


def _row(draw, x, y, label, value, label_w=235, total_w=1100, value_size=18, min_h=42):
    value = "—" if value is None else str(value)
    value_font = _font(value_size)
    lines = _wrapped_lines(draw, value, value_font, total_w - label_w - 28)
    h = max(min_h, len(lines) * (value_size + 7) + 12)
    draw.rectangle((x, y, x + total_w, y + h), outline=LINE, width=1)
    draw.line((x + label_w, y, x + label_w, y + h), fill=LINE, width=1)
    _text(draw, (x + 12, y + 10), label, size=16, bold=True)
    yy = y + 10
    for line in lines:
        _text(draw, (x + label_w + 12, yy), line, size=value_size)
        yy += value_size + 7
    return y + h


def _two_col_row(draw, x, y, left_label, left_value, right_label, right_value, total_w=1100, label_w=180):
    half = total_w // 2
    h = 54
    draw.rectangle((x, y, x + total_w, y + h), outline=LINE, width=1)
    draw.line((x + half, y, x + half, y + h), fill=LINE, width=1)
    draw.line((x + label_w, y, x + label_w, y + h), fill=LINE, width=1)
    draw.line((x + half + label_w, y, x + half + label_w, y + h), fill=LINE, width=1)
    _text(draw, (x + 10, y + 16), left_label, size=15, bold=True)
    _text(draw, (x + label_w + 10, y + 16), left_value, size=16)
    _text(draw, (x + half + 10, y + 16), right_label, size=15, bold=True)
    _text(draw, (x + half + label_w + 10, y + 16), right_value, size=16)
    return y + h


def _watermark(base):
    layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(layer)
    f = _font(58, True)
    bbox = d.textbbox((0, 0), WATERMARK, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((base.width - tw) // 2, (base.height - th) // 2), WATERMARK, font=f, fill=(170, 0, 0, 55))
    layer = layer.rotate(30, expand=False, resample=Image.Resampling.BICUBIC)
    return Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")


def _footer(draw):
    y0 = 1545
    draw.rounded_rectangle((70, y0, 1170, 1690), radius=10, outline=(120, 120, 120), width=2, fill=(252, 252, 252))
    _text(draw, (90, y0 + 18), "NON-AUTHENTIC DEMO MARKER", size=18, bold=True)
    _text(draw, (90, y0 + 50), "No official seal, signature, QR code, or government branding is present.", size=15, fill=MUTED)
    _text(draw, (90, y0 + 88), WATERMARK, size=24, bold=True, fill=ACCENT)


def _render_bis(d, r):
    _draw_header(d, "SYNTHETIC PRODUCT CERTIFICATION LETTER", "BIS-inspired field structure for OCR research only", "Document type: BIS-style synthetic sample")
    y = 275
    y = _section(d, MARGIN, y, 1100, "Reference & Issue Details")
    y = _two_col_row(d, MARGIN, y, "Reference No.", r.reference_number, "Issue Date", r.issue_date)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Manufacturing Unit")
    y = _row(d, MARGIN, y, "Unit Name", r.manufacturing_unit_name)
    y = _row(d, MARGIN, y, "Unit Address", r.manufacturing_unit_address)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Product Details")
    y = _two_col_row(d, MARGIN, y, "Category", r.product_category, "Product", r.product_name)
    y = _two_col_row(d, MARGIN, y, "IS Number", r.is_number, "Brand", r.brand_name or "—")
    y = _two_col_row(d, MARGIN, y, "Model", r.model_name or "—", "Licence No.", r.licence_number)
    y = _row(d, MARGIN, y, "Factory Address", r.factory_address)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Validity & Representative")
    y = _two_col_row(d, MARGIN, y, "Valid From", r.valid_from, "Valid Upto", r.valid_upto)
    y = _row(d, MARGIN, y, "Representative", r.authorized_representative_name or "—")
    y = _row(d, MARGIN, y, "Representative Address", r.authorized_representative_address or "—")
    y += 14
    y = _section(d, MARGIN, y, 1100, "Terms & Signatory")
    terms = r.terms_conditions or []
    for idx, term in enumerate(terms, 1):
        y = _draw_wrapped(d, MARGIN + 18, y, f"{idx}. {term}", 1060, size=15, line_gap=5)
    y += 10
    y = _two_col_row(d, MARGIN, y, "Signatory", r.signatory_name or "—", "Designation", r.signatory_designation or "—")
    _text(d, (MARGIN + 720, y + 14), "SIGNATURE PLACEHOLDER — NOT AUTHENTIC", size=13, bold=True, fill=MUTED)
    return y + 42


def _render_pan(d, r):
    _draw_header(d, "SYNTHETIC IDENTITY CARD FORMAT", "PAN-inspired field structure for OCR research only", "Document type: PAN-style synthetic sample")
    y = 275
    # visual placeholder areas
    d.rounded_rectangle((75, y, 320, y + 300), radius=8, outline=LINE, width=2, fill=(250,250,250))
    _text(d, (197, y + 130), "PHOTO\nPLACEHOLDER", size=20, bold=True, anchor="mm", fill=MUTED)
    _text(d, (915, y + 18), "Synthetic Identifier", size=17, bold=True, fill=ACCENT)
    _text(d, (915, y + 58), r.pan_number, size=25, bold=True)
    y += 335
    y = _section(d, MARGIN, y, 1100, "Holder Details")
    y = _row(d, MARGIN, y, "Holder Name", r.holder_name)
    y = _row(d, MARGIN, y, "Father Name", r.father_name)
    y = _row(d, MARGIN, y, "Date of Birth", r.date_of_birth)
    y += 28
    d.rounded_rectangle((760, y, 1170, y + 90), radius=8, outline=LINE, width=2)
    _text(d, (780, y + 18), "SIGNATURE PLACEHOLDER", size=16, bold=True)
    _text(d, (780, y + 50), "Not an authentic signature", size=14, fill=MUTED)


def _render_mca(d, r):
    _draw_header(d, "SYNTHETIC CERTIFICATE OF INCORPORATION FORMAT", "MCA-inspired field structure for OCR research only", "Document type: MCA-style synthetic sample")
    y = 275
    y = _section(d, MARGIN, y, 1100, "Company Information")
    y = _row(d, MARGIN, y, "Company Name", r.company_name)
    y = _row(d, MARGIN, y, "Incorporation Date", r.incorporation_date)
    y = _row(d, MARGIN, y, "Date (Words)", r.incorporation_date_words)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Synthetic Identifiers")
    y = _two_col_row(d, MARGIN, y, "CIN", r.cin_number, "PAN", r.pan_number)
    y = _two_col_row(d, MARGIN, y, "TAN", r.tan_number, "Place", r.place_of_issue)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Registrar / Digital Signature")
    y = _row(d, MARGIN, y, "Registrar", f"{r.registrar_name} — {r.registrar_designation}")
    y = _row(d, MARGIN, y, "Digital Signature", r.digital_signature_text or "—")


def _render_gst(d, r):
    _draw_header(d, "SYNTHETIC TAX REGISTRATION FORMAT", "GST-inspired field structure for OCR research only", "Document type: GST-style synthetic sample")
    y = 275
    y = _section(d, MARGIN, y, 1100, "Registration")
    y = _two_col_row(d, MARGIN, y, "Synthetic GSTIN", r.gstin_number, "Issue Date", r.certificate_issue_date)
    y = _row(d, MARGIN, y, "Legal Name", r.legal_name)
    y = _row(d, MARGIN, y, "Trade Name", r.trade_name)
    y = _two_col_row(d, MARGIN, y, "Constitution", r.constitution_of_business, "Registration Type", r.registration_type)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Validity & Address")
    y = _two_col_row(d, MARGIN, y, "Valid From", r.validity_from, "Valid To", r.validity_to)
    y = _row(d, MARGIN, y, "Principal Address", r.principal_address)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Approval Details")
    y = _two_col_row(d, MARGIN, y, "Officer", r.officer_name, "Designation", r.officer_designation)
    y = _row(d, MARGIN, y, "Approving Authority", r.approving_authority)
    y = _row(d, MARGIN, y, "Jurisdiction", r.jurisdictional_office)
    y = _row(d, MARGIN, y, "Date of Liability", r.date_of_liability or "Not specified")


def _render_dpiit(d, r):
    _draw_header(d, "SYNTHETIC STARTUP RECOGNITION FORMAT", "DPIIT-inspired field structure for OCR research only", "Document type: DPIIT-style synthetic sample")
    y = 275
    y = _section(d, MARGIN, y, 1100, "Recognition Details")
    y = _two_col_row(d, MARGIN, y, "Certificate No.", r.certificate_number, "Date of Issue", r.date_of_issue)
    y = _row(d, MARGIN, y, "Company Name", r.company_name)
    y = _two_col_row(d, MARGIN, y, "Constitution", r.constitution_type, "Incorporation", r.incorporation_date)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Industry & Validity")
    y = _two_col_row(d, MARGIN, y, "Industry", r.industry, "Sector", r.sector)
    y = _row(d, MARGIN, y, "Valid Upto", r.valid_upto)
    y = _row(d, MARGIN, y, "Condition", r.turnover_condition_text)
    d.rounded_rectangle((MARGIN, y + 22, MARGIN + 1100, y + 90), radius=8, outline=LINE, width=2, fill=(250,250,250))
    _text(d, (MARGIN + 20, y + 42), "Synthetic recognition notice — not an official government recognition.", size=16, fill=MUTED)


def _render_udyam(d, r):
    _draw_header(d, "SYNTHETIC ENTERPRISE REGISTRATION FORMAT", "Udyam-inspired field structure for OCR research only", "Document type: Udyam-style synthetic sample")
    y = 275
    y = _section(d, MARGIN, y, 1100, "Enterprise")
    y = _two_col_row(d, MARGIN, y, "Registration No.", r.udyam_registration_number, "Enterprise Type", r.enterprise_type)
    y = _row(d, MARGIN, y, "Enterprise Name", r.enterprise_name)
    y = _two_col_row(d, MARGIN, y, "Major Activity", r.major_activity, "Social Category", r.social_category)
    y = _row(d, MARGIN, y, "Unit Name", r.unit_name)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Address & Contact")
    y = _row(d, MARGIN, y, "Address Line", r.line1)
    y = _two_col_row(d, MARGIN, y, "City", r.city, "State", r.state)
    y = _two_col_row(d, MARGIN, y, "PIN", r.pin, "Mobile", r.mobile)
    y = _row(d, MARGIN, y, "Email", r.email)
    y += 14
    y = _section(d, MARGIN, y, 1100, "Dates")
    y = _two_col_row(d, MARGIN, y, "Incorporation", r.date_of_incorporation, "Commencement", r.date_of_commencement)


def render_document(record, path: Path):
    im = Image.new("RGB", CANVAS_SIZE, "white")
    d = ImageDraw.Draw(im)
    doc_type = record.__class__.__name__.replace("Record", "").lower()
    if doc_type == "bis":
        _render_bis(d, record)
    elif doc_type == "pan":
        _render_pan(d, record)
    elif doc_type == "mca":
        _render_mca(d, record)
    elif doc_type == "gst":
        _render_gst(d, record)
    elif doc_type == "dpiit":
        _render_dpiit(d, record)
    elif doc_type == "udyam":
        _render_udyam(d, record)
    else:
        raise ValueError(f"Unsupported document type: {doc_type}")
    _footer(d)
    im = _watermark(im)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG")
    return im
