import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import AuditEvent


async def append_audit_event(
    db: AsyncSession,
    *,
    event_type: str,
    payload: dict[str, Any],
    tender_id: UUID | None = None,
    bid_id: UUID | None = None,
    actor_id: UUID | None = None,
) -> AuditEvent:
    previous = await db.execute(
        select(AuditEvent)
        .where(
            AuditEvent.bid_id == bid_id if bid_id else AuditEvent.tender_id == tender_id
        )
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(1)
    )
    previous_event = previous.scalar_one_or_none()
    previous_hash = previous_event.payload_hash if previous_event else None
    canonical = json.dumps(
        {
            "previous_event_hash": previous_hash,
            "event_type": event_type,
            "tender_id": str(tender_id) if tender_id else None,
            "bid_id": str(bid_id) if bid_id else None,
            "actor_id": str(actor_id) if actor_id else None,
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    event = AuditEvent(
        tender_id=tender_id,
        bid_id=bid_id,
        actor_id=actor_id,
        event_type=event_type,
        payload=payload,
        previous_event_hash=previous_hash,
        payload_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )
    db.add(event)
    return event


async def list_audit_events(
    db: AsyncSession, *, tender_id: UUID, bid_id: UUID | None = None
) -> list[AuditEvent]:
    query = select(AuditEvent).where(AuditEvent.tender_id == tender_id)
    if bid_id is not None:
        query = query.where(AuditEvent.bid_id == bid_id)
    result = await db.execute(
        query.order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
    )
    return list(result.scalars().all())
