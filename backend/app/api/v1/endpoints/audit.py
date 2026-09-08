from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.compliance import AuditEvent
from app.models.user import User
from app.schemas.compliance import AuditEventResponse
from app.services.audit_service import list_audit_events

router = APIRouter()


@router.get("", response_model=list[AuditEventResponse])
async def list_all(
    tender_id: UUID,
    bid_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list[AuditEvent]:
    return await list_audit_events(db, tender_id=tender_id, bid_id=bid_id)
