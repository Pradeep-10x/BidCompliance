from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requirement import Requirement
from app.models.tender import Tender
from app.schemas.requirement import RequirementCreate, RequirementUpdate
from app.services.audit_service import append_audit_event


async def get_tender(db: AsyncSession, tender_id: UUID) -> Tender | None:
    return await db.get(Tender, tender_id)


async def create_requirement(
    db: AsyncSession, tender_id: UUID, requirement_in: RequirementCreate
) -> Requirement:
    values = requirement_in.model_dump(exclude_unset=True)
    requirement = Requirement(tender_id=tender_id, **values)
    db.add(requirement)
    await db.commit()
    await db.refresh(requirement)
    return requirement


async def list_requirements(
    db: AsyncSession, tender_id: UUID, skip: int, limit: int
) -> list[Requirement]:
    result = await db.execute(
        select(Requirement)
        .where(Requirement.tender_id == tender_id)
        .order_by(Requirement.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_requirement(
    db: AsyncSession, tender_id: UUID, requirement_id: UUID
) -> Requirement | None:
    result = await db.execute(
        select(Requirement).where(
            Requirement.id == requirement_id,
            Requirement.tender_id == tender_id,
        )
    )
    return result.scalar_one_or_none()


async def update_requirement(
    db: AsyncSession,
    requirement: Requirement,
    requirement_in: RequirementUpdate,
) -> Requirement:
    for field, value in requirement_in.model_dump(exclude_unset=True).items():
        setattr(requirement, field, value)
    await db.commit()
    await db.refresh(requirement)
    return requirement


async def delete_requirement(db: AsyncSession, requirement: Requirement) -> None:
    await db.delete(requirement)
    await db.commit()


async def confirm_requirements(
    db: AsyncSession,
    *,
    tender_id: UUID,
    requirement_ids: list[UUID],
    actor_id: UUID,
) -> list[Requirement]:
    result = await db.execute(
        select(Requirement).where(
            Requirement.tender_id == tender_id,
            Requirement.id.in_(requirement_ids),
        )
    )
    requirements = list(result.scalars().all())
    if len(requirements) != len(set(requirement_ids)):
        raise ValueError("One or more requirements do not belong to this tender")
    for requirement in requirements:
        if requirement.status == "DISABLED":
            raise ValueError("Disabled requirements cannot be confirmed")
        requirement.status = "CONFIRMED"
    await append_audit_event(
        db,
        event_type="TENDER_REQUIREMENTS_CONFIRMED",
        tender_id=tender_id,
        actor_id=actor_id,
        payload={"requirement_ids": [str(value) for value in requirement_ids]},
    )
    await db.commit()
    for requirement in requirements:
        await db.refresh(requirement)
    return requirements
