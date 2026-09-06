from .config import ROOT, WATERMARK
from .id_generator import generate_document_id, generate_synthetic_ref
from .field_generators import *
from .schemas import BISRecord, PANRecord, MCARecord, GSTRecord, DPIITRecord, UdyamRecord
from datetime import date, timedelta
import random


def build_bis_record() -> BISRecord:
    doc_id = generate_document_id("bis", ROOT)
    issue = fake_date(2024, 2026)
    valid_from = issue
    valid_upto = (date.fromisoformat(valid_from) + timedelta(days=730)).isoformat()
    return BISRecord(
        document_id=doc_id,
        reference_number=doc_id,
        issue_date=issue,
        manufacturing_unit_name=fake_company_name(),
        manufacturing_unit_address=fake_address(),
        product_category=random.choice(PRODUCT_CATEGORIES),
        product_name=random.choice(PRODUCTS),
        is_number=generate_synthetic_ref("IS", int(doc_id[-6:])),
        brand_name=random.choice([None, "DemoBrand"]),
        model_name=random.choice([None, "Model-DX"]),
        factory_address=fake_address(),
        licence_number=generate_synthetic_ref("LIC", int(doc_id[-6:])),
        valid_from=valid_from,
        valid_upto=valid_upto,
        authorized_representative_name=random.choice([None, fake_person_name()]),
        authorized_representative_address=random.choice([None, fake_address()]),
        signatory_name=random.choice([None, "Officer Demo"]),
        signatory_designation=random.choice([None, "Synthetic Officer"]),
        terms_conditions=[
            "This is a synthetic demo document.",
            "Not valid for legal or regulatory use.",
            "Generated for OCR research only.",
        ],
        watermark_tag=WATERMARK,
    )


def build_pan_record() -> PANRecord:
    doc_id = generate_document_id("pan", ROOT)
    return PANRecord(doc_id, generate_synthetic_ref("PAN", int(doc_id[-6:])), fake_person_name(), fake_person_name(), fake_date(1975, 2005), True, True, WATERMARK)


def build_mca_record() -> MCARecord:
    doc_id = generate_document_id("mca", ROOT); d = fake_date(2022, 2026)
    return MCARecord(doc_id, fake_company_name(), d, d, generate_synthetic_ref("CIN", int(doc_id[-6:])), generate_synthetic_ref("PAN", int(doc_id[-6:])), generate_synthetic_ref("TAN", int(doc_id[-6:])), fake_city(), "Registrar Demo", "Registrar", "Digital signature placeholder - synthetic", WATERMARK)


def build_gst_record() -> GSTRecord:
    doc_id = generate_document_id("gst", ROOT); d = fake_date(2023, 2026)
    return GSTRecord(doc_id, generate_synthetic_ref("GST", int(doc_id[-6:])), fake_company_name(), "Demo Trade Name", random.choice(CONSTITUTIONS), fake_address(), None, d, (date.fromisoformat(d)+timedelta(days=1095)).isoformat(), "Regular", "Approving Authority (Fictional)", "Officer Demo", "Synthetic Officer", "Demo Jurisdiction", d, WATERMARK)


def build_dpiit_record() -> DPIITRecord:
    doc_id = generate_document_id("dpiit", ROOT); d = fake_date(2022, 2026)
    return DPIITRecord(doc_id, generate_synthetic_ref("DPIIT", int(doc_id[-6:])), fake_company_name(), random.choice(CONSTITUTIONS), d, "Technology", "Software Services", d, (date.fromisoformat(d)+timedelta(days=1825)).isoformat(), "Synthetic turnover condition for demonstration only.", WATERMARK)


def build_udyam_record() -> UdyamRecord:
    doc_id = generate_document_id("udyam", ROOT); d = fake_date(2021, 2025)
    return UdyamRecord(doc_id, generate_synthetic_ref("UDYAM", int(doc_id[-6:])), fake_company_name(), "Micro", "Manufacturing", "General", "Demo Unit", "12 Synthetic Industrial Road", fake_city(), fake_state(), fake_pin(), fake_mobile(), fake_email(), d, d, WATERMARK)

BUILDERS = {"bis": build_bis_record, "pan": build_pan_record, "mca": build_mca_record, "gst": build_gst_record, "dpiit": build_dpiit_record, "udyam": build_udyam_record}


def build_record(doc_type: str):
    return BUILDERS[doc_type]()
