from fastapi import APIRouter

from app.api.v1.endpoints import (
	auth,
	assessments,
	audit,
	bidders,
	bids,
	documents,
	requirements,
	tenders,
	verifications,
)

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
	documents.router,
	prefix="/tenders/{tender_id}/bids/{bid_id}/documents",
	tags=["documents"],
)
api_router.include_router(
	requirements.router,
	prefix="/tenders/{tender_id}/requirements",
	tags=["requirements"],
)
api_router.include_router(
	verifications.router,
	prefix="/tenders/{tender_id}/bids/{bid_id}/verifications",
	tags=["verifications"],
)
api_router.include_router(
	assessments.router,
	prefix="/tenders/{tender_id}/bids/{bid_id}/assessments",
	tags=["assessments"],
)
api_router.include_router(
	audit.router,
	prefix="/tenders/{tender_id}/audit",
	tags=["audit"],
)
