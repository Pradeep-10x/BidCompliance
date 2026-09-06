from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.requirement import Requirement
from app.models.user import User
from app.schemas.requirement import (
    RequirementCreate,
    RequirementResponse,
    RequirementUpdate,
)
from app.services.requirement_service import (
    create_requirement,
    delete_requirement,
    get_requirement,
    get_tender,
    list_requirements,
    update_requirement,
)

router = APIRouter()


def not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Tender or requirement not found",
    )


async def require_tender(
    db: AsyncSession, tender_id: UUID
) -> None:
    if await get_tender(db, tender_id) is None:
        raise not_found()


@router.post("", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create(
    tender_id: UUID,
    requirement_in: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Requirement:
    await require_tender(db, tender_id)
    return await create_requirement(db, tender_id, requirement_in)


@router.get("", response_model=list[RequirementResponse])
async def list_all(
    tender_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list[Requirement]:
    await require_tender(db, tender_id)
    return await list_requirements(db, tender_id, skip, limit)


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_one(
    tender_id: UUID,
    requirement_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Requirement:
    await require_tender(db, tender_id)
    requirement = await get_requirement(db, tender_id, requirement_id)
    if requirement is None:
        raise not_found()
    return requirement


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update(
    tender_id: UUID,
    requirement_id: UUID,
    requirement_in: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Requirement:
    await require_tender(db, tender_id)
    requirement = await get_requirement(db, tender_id, requirement_id)
    if requirement is None:
        raise not_found()
    return await update_requirement(db, requirement, requirement_in)


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    tender_id: UUID,
    requirement_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> None:
    await require_tender(db, tender_id)
    requirement = await get_requirement(db, tender_id, requirement_id)
    if requirement is None:
        raise not_found()
    await delete_requirement(db, requirement)
