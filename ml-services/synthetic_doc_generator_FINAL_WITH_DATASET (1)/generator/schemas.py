from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

@dataclass
class BISRecord:
    document_id: str
    reference_number: str
    issue_date: str
    manufacturing_unit_name: str
    manufacturing_unit_address: str
    product_category: str
    product_name: str
    is_number: str
    brand_name: Optional[str]
    model_name: Optional[str]
    factory_address: str
    licence_number: str
    valid_from: str
    valid_upto: str
    authorized_representative_name: Optional[str]
    authorized_representative_address: Optional[str]
    signatory_name: Optional[str]
    signatory_designation: Optional[str]
    terms_conditions: Optional[List[str]]
    watermark_tag: str

@dataclass
class PANRecord:
    document_id: str
    pan_number: str
    holder_name: str
    father_name: str
    date_of_birth: str
    signature_present: bool
    photo_present: bool
    watermark_tag: str

@dataclass
class MCARecord:
    document_id: str
    company_name: str
    incorporation_date: str
    incorporation_date_words: str
    cin_number: str
    pan_number: str
    tan_number: str
    place_of_issue: str
    registrar_name: str
    registrar_designation: str
    digital_signature_text: Optional[str]
    watermark_tag: str

@dataclass
class GSTRecord:
    document_id: str
    gstin_number: str
    legal_name: str
    trade_name: str
    constitution_of_business: str
    principal_address: str
    date_of_liability: Optional[str]
    validity_from: str
    validity_to: str
    registration_type: str
    approving_authority: str
    officer_name: str
    officer_designation: str
    jurisdictional_office: str
    certificate_issue_date: str
    watermark_tag: str

@dataclass
class DPIITRecord:
    document_id: str
    certificate_number: str
    company_name: str
    constitution_type: str
    incorporation_date: str
    industry: str
    sector: str
    date_of_issue: str
    valid_upto: str
    turnover_condition_text: str
    watermark_tag: str

@dataclass
class UdyamRecord:
    document_id: str
    udyam_registration_number: str
    enterprise_name: str
    enterprise_type: str
    major_activity: str
    social_category: str
    unit_name: str
    line1: str
    city: str
    state: str
    pin: str
    mobile: str
    email: str
    date_of_incorporation: str
    date_of_commencement: str
    watermark_tag: str


def record_to_dict(record: Any) -> Dict[str, Any]:
    return asdict(record)
