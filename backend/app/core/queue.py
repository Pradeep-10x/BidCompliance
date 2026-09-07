from typing import Protocol
from uuid import UUID

from app.core.config import settings


class QueueSubmissionError(Exception):
    pass


class JobPublisher(Protocol):
    async def publish(self, job_id: UUID, payload: dict) -> None: ...


class CeleryJobPublisher:
    def __init__(self) -> None:
        from celery import Celery

        self.app = Celery(
            "bid_compliance_processing",
            broker=settings.CELERY_BROKER_URL,
            backend=settings.CELERY_RESULT_BACKEND,
        )

    async def publish(self, job_id: UUID, payload: dict) -> None:
        try:
            self.app.send_task(
                "app.workers.processing.process_document",
                args=[str(job_id)],
                kwargs={"payload": payload},
            )
        except Exception as exc:
            raise QueueSubmissionError from exc


def get_job_publisher() -> JobPublisher:
    return CeleryJobPublisher()
