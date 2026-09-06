from fastapi import APIRouter

from app.api.v1.endpoints import auth, bidders, bids, requirements, tenders

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(bidders.router, prefix="/bidders", tags=["bidders"])
api_router.include_router(tenders.router, prefix="/tenders", tags=["tenders"])
api_router.include_router(
	bids.router,
	prefix="/tenders/{tender_id}/bids",
	tags=["bids"],
)
api_router.include_router(
	requirements.router,
	prefix="/tenders/{tender_id}/requirements",
	tags=["requirements"],
)
