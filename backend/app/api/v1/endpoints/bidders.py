from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models.bidder import Bidder
from app.models.user import User
from app.schemas.bidder import BidderCreate, BidderResponse, BidderUpdate
from app.services.bidder_service import (
    create_bidder,
    get_bidder,
    list_bidders,
    update_bidder,
)

router = APIRouter()


def bidder_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Bidder not found"
    )


@router.post("", response_model=BidderResponse, status_code=status.HTTP_201_CREATED)
async def create(
    bidder_in: BidderCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Bidder:
    return await create_bidder(db, bidder_in)


@router.get("", response_model=list[BidderResponse])
async def list_all(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list[Bidder]:
    return await list_bidders(db, skip, limit)


@router.get("/{bidder_id}", response_model=BidderResponse)
async def get_one(
    bidder_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Bidder:
    bidder = await get_bidder(db, bidder_id)
    if bidder is None:
        raise bidder_not_found()
    return bidder


@router.patch("/{bidder_id}", response_model=BidderResponse)
async def update(
    bidder_id: UUID,
    bidder_in: BidderUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> Bidder:
    bidder = await get_bidder(db, bidder_id)
    if bidder is None:
        raise bidder_not_found()
    return await update_bidder(db, bidder, bidder_in)
