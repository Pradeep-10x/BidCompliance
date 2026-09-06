from fastapi import APIRouter

from app.api.v1.endpoints import auth, requirements, tenders

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenders.router, prefix="/tenders", tags=["tenders"])
api_router.include_router(
	requirements.router,
	prefix="/tenders/{tender_id}/requirements",
	tags=["requirements"],
)
