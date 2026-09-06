import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.exceptions import MLServiceException
from ml1_document_intelligence.routes import router as ml1_router
from ml1_document_intelligence.ocr_service import is_tesseract_available
from ml2_forensics.routes import router as ml2_router
from ml2_forensics.forensics_service import PIKEPDF_AVAILABLE

# Configure logging to server console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ml_services")

app = FastAPI(
    title="PS26100 ML Services",
    description="Document Intelligence and Verification ML Microservice",
    version="1.0.0",
)

# Enable CORS for frontend and cross-service calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MLServiceException)
async def handle_ml_service_exception(request: Request, exc: MLServiceException):
    """Translates domain exceptions into structured HTTP 4xx/5xx responses."""
    logger.warning(
        "Domain error on %s %s -> HTTP %d [%s]: %s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.error_code,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def handle_unhandled_exception(request: Request, exc: Exception):
    """Catches unexpected system crashes, writes stack trace to console, and returns safe HTTP 500."""
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred while processing the request.",
            "details": None,
        },
    )


app.include_router(ml1_router)
app.include_router(ml2_router)


@app.get("/health")
def root_health():
    tesseract_ready = is_tesseract_available()
    return {
        "status": "ok" if (tesseract_ready and PIKEPDF_AVAILABLE) else "degraded",
        "service": "ml-services",
        "ocr_engine_available": tesseract_ready,
        "forensics_engine_available": PIKEPDF_AVAILABLE,
    }


@app.get("/")
def read_root():
    return {"message": "PS26100 ML Services is running"}