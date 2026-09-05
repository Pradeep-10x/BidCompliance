from fastapi import FastAPI
from ml1_document_intelligence.routes import router as ml1_router

app = FastAPI(title="PS26100 ML Services")

app.include_router(ml1_router)


@app.get("/health")
def root_health():
    return {"status": "ok"}