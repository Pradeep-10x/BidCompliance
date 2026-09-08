import asyncio

from celery import shared_task

from app.core.database import AsyncSessionLocal
from app.services.ml1_client import ML1Client
from app.services.ml1_worker_service import execute_classification_job


@shared_task(name="app.workers.processing.process_document")
def process_document(job_id: str, payload: dict | None = None) -> str:
    async def run() -> None:
        async with AsyncSessionLocal() as db:
            await execute_classification_job(db, job_id, ML1Client())

    asyncio.run(run())
    return job_id
