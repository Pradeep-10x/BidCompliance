import uuid
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import Bid, BidStatus
from app.models.bidder import Bidder
from app.models.document import Document, DocumentProcessingStatus
from app.models.requirement import Requirement
from app.models.tender import Tender, TenderStatus


@pytest.mark.asyncio
async def test_create_tender(db_session: AsyncSession):
    ref_num = f"REF-CREATE-{uuid.uuid4().hex[:8]}"
    tender = Tender(
        title="Supply of IT Equipment",
        description="Laptops and Servers for Government Offices",
        reference_number=ref_num,
        status=TenderStatus.DRAFT,
        budget=Decimal("500000.00"),
    )
    db_session.add(tender)
    await db_session.commit()
    await db_session.refresh(tender)

    assert tender.id is not None
    assert tender.reference_number == ref_num
    assert tender.status == TenderStatus.DRAFT
    assert tender.budget == Decimal("500000.00")
    assert tender.created_at is not None
    assert tender.updated_at is not None


@pytest.mark.asyncio
async def test_tender_unique_reference_number(db_session: AsyncSession):
    ref_num = f"REF-UNIQUE-{uuid.uuid4().hex[:8]}"
    tender1 = Tender(
        title="Tender One",
        reference_number=ref_num,
        status=TenderStatus.PUBLISHED,
    )
    db_session.add(tender1)
    await db_session.commit()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            tender2 = Tender(
                title="Tender Two",
                reference_number=ref_num,
                status=TenderStatus.PUBLISHED,
            )
            db_session.add(tender2)
            await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_requirements_tender_specific(db_session: AsyncSession):
    ref_a = f"REF-REQ-A-{uuid.uuid4().hex[:8]}"
    ref_b = f"REF-REQ-B-{uuid.uuid4().hex[:8]}"

    tender_a = Tender(title="Tender A", reference_number=ref_a)
    tender_b = Tender(title="Tender B", reference_number=ref_b)
    db_session.add_all([tender_a, tender_b])
    await db_session.commit()

    req_a1 = Requirement(
        tender_id=tender_a.id,
        title="GST Registration",
        is_mandatory=True,
        weight=Decimal("1.50"),
    )
    req_a2 = Requirement(
        tender_id=tender_a.id,
        title="PAN Card",
        is_mandatory=True,
        weight=Decimal("1.00"),
    )
    req_b1 = Requirement(
        tender_id=tender_b.id,
        title="BIS Certification",
        is_mandatory=True,
        weight=Decimal("2.00"),
        rule_config={"required_code": "IS-1234"},
    )
    db_session.add_all([req_a1, req_a2, req_b1])
    await db_session.commit()

    res_a = await db_session.execute(
        select(Requirement).where(Requirement.tender_id == tender_a.id)
    )
    reqs_a = res_a.scalars().all()
    assert len(reqs_a) == 2
    assert {r.title for r in reqs_a} == {"GST Registration", "PAN Card"}

    res_b = await db_session.execute(
        select(Requirement).where(Requirement.tender_id == tender_b.id)
    )
    reqs_b = res_b.scalars().all()
    assert len(reqs_b) == 1
    assert reqs_b[0].title == "BIS Certification"
    assert reqs_b[0].rule_config == {"required_code": "IS-1234"}
    assert reqs_b[0].weight == Decimal("2.00")


@pytest.mark.asyncio
async def test_bidder_creation_jsonb_identifiers(db_session: AsyncSession):
    email = f"contact_{uuid.uuid4().hex[:8]}@example.com"
    bidder = Bidder(
        legal_name="Acme Solutions Pvt Ltd",
        contact_email=email,
        contact_phone="+919876543210",
        identifiers={
            "pan": "ABCDE1234F",
            "gstin": "27ABCDE1234F1Z5",
            "cin": "U12345MH2026PTC123456",
            "udyam": "UDYAM-MH-00-0012345",
        },
    )
    db_session.add(bidder)
    await db_session.commit()
    await db_session.refresh(bidder)

    assert bidder.id is not None
    assert bidder.contact_email == email
    assert bidder.identifiers["pan"] == "ABCDE1234F"
    assert bidder.identifiers["gstin"] == "27ABCDE1234F1Z5"


@pytest.mark.asyncio
async def test_bidder_nullable_contact_email(db_session: AsyncSession):
    bidder = Bidder(
        legal_name="No Email Bidder LLC",
        contact_email=None,
    )
    db_session.add(bidder)
    await db_session.commit()
    await db_session.refresh(bidder)

    assert bidder.id is not None
    assert bidder.contact_email is None


@pytest.mark.asyncio
async def test_bid_creation_and_unique_constraint(db_session: AsyncSession):
    ref_num = f"REF-BID-{uuid.uuid4().hex[:8]}"
    tender = Tender(title="Laptops Procurement", reference_number=ref_num)
    bidder = Bidder(legal_name="Tech Corp", contact_email=f"sales_{uuid.uuid4().hex[:6]}@techcorp.com")
    db_session.add_all([tender, bidder])
    await db_session.commit()

    bid = Bid(
        tender_id=tender.id,
        bidder_id=bidder.id,
        bid_amount=None,
        status=BidStatus.SUBMITTED,
    )
    db_session.add(bid)
    await db_session.commit()
    await db_session.refresh(bid)

    assert bid.id is not None
    assert bid.bid_amount is None
    assert bid.status == BidStatus.SUBMITTED

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            duplicate_bid = Bid(
                tender_id=tender.id,
                bidder_id=bidder.id,
                bid_amount=Decimal("450000.00"),
                status=BidStatus.SUBMITTED,
            )
            db_session.add(duplicate_bid)
            await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_document_creation_and_defaults(db_session: AsyncSession):
    ref_num = f"REF-DOC-{uuid.uuid4().hex[:8]}"
    tender = Tender(title="Software Services", reference_number=ref_num)
    bidder = Bidder(legal_name="SoftDev LLC", contact_email=f"contact_{uuid.uuid4().hex[:6]}@softdev.com")
    db_session.add_all([tender, bidder])
    await db_session.commit()

    bid = Bid(
        tender_id=tender.id,
        bidder_id=bidder.id,
        bid_amount=Decimal("300000.00"),
    )
    db_session.add(bid)
    await db_session.commit()

    doc = Document(
        bid_id=bid.id,
        original_filename="gst_certificate.pdf",
        document_type="GST_CERTIFICATE",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_path="/uploads/docs/gst_cert.pdf",
        processing_status=DocumentProcessingStatus.PENDING,
        file_size_bytes=None,
        mime_type=None,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    assert doc.id is not None
    assert doc.processing_status == DocumentProcessingStatus.PENDING
    assert doc.file_size_bytes is None
    assert doc.mime_type is None
    assert len(doc.content_hash) == 64


@pytest.mark.asyncio
async def test_enum_values():
    assert TenderStatus.DRAFT.value == "DRAFT"
    assert TenderStatus.PUBLISHED.value == "PUBLISHED"
    assert TenderStatus.CLOSED.value == "CLOSED"
    assert TenderStatus.EVALUATING.value == "EVALUATING"
    assert TenderStatus.AWARDED.value == "AWARDED"
    assert TenderStatus.CANCELLED.value == "CANCELLED"

    assert BidStatus.SUBMITTED.value == "SUBMITTED"
    assert BidStatus.UNDER_REVIEW.value == "UNDER_REVIEW"
    assert BidStatus.QUALIFIED.value == "QUALIFIED"
    assert BidStatus.DISQUALIFIED.value == "DISQUALIFIED"
    assert BidStatus.WITHDRAWN.value == "WITHDRAWN"

    assert DocumentProcessingStatus.PENDING.value == "PENDING"
    assert DocumentProcessingStatus.PROCESSING.value == "PROCESSING"
    assert DocumentProcessingStatus.COMPLETED.value == "COMPLETED"
    assert DocumentProcessingStatus.FAILED.value == "FAILED"


@pytest.mark.asyncio
async def test_cascade_delete_tender(db_session: AsyncSession):
    ref_num = f"REF-CAS-{uuid.uuid4().hex[:8]}"
    tender = Tender(title="Cascade Test Tender", reference_number=ref_num)
    bidder = Bidder(legal_name="Cascade Bidder")
    db_session.add_all([tender, bidder])
    await db_session.commit()

    req = Requirement(tender_id=tender.id, title="Req 1")
    bid = Bid(tender_id=tender.id, bidder_id=bidder.id)
    db_session.add_all([req, bid])
    await db_session.commit()

    doc = Document(
        bid_id=bid.id,
        original_filename="test.pdf",
        document_type="TEST",
        content_hash="a" * 64,
        storage_path="/path/test.pdf",
    )
    db_session.add(doc)
    await db_session.commit()

    await db_session.delete(tender)
    await db_session.commit()

    res_req = await db_session.execute(select(Requirement).where(Requirement.id == req.id))
    assert res_req.scalars().first() is None

    res_bid = await db_session.execute(select(Bid).where(Bid.id == bid.id))
    assert res_bid.scalars().first() is None

    res_doc = await db_session.execute(select(Document).where(Document.id == doc.id))
    assert res_doc.scalars().first() is None
