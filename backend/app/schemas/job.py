from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.processing_job import PipelineStage, ProcessingJobStatus


class ProcessingJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    job_type: str
    pipeline_stage: PipelineStage
    status: ProcessingJobStatus
    attempt_count: int
    max_attempts: int
    payload: dict[str, Any]
    error_message: str | None
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
