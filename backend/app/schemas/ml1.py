from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ML1Request(BaseModel):
    job_id: UUID
    bid_id: UUID
    document_id: UUID
    page_id: UUID | None
    page_number: int = Field(ge=1)
    file_type: str
    image_path: str
    document_hash: str
    callback_url: str | None
    pipeline_stage: str

    model_config = ConfigDict(extra="forbid")


class ML1Response(BaseModel):
    job_id: UUID
    bid_id: UUID
    document_id: UUID
    page_id: UUID | None
    page_number: int = Field(ge=1)
    module: str
    model_name: str
    model_version: str
    status: str
    processing_time_ms: int | None = Field(default=None, ge=0)
    result: dict[str, Any]
    errors: list[Any]
    created_at: datetime

    model_config = ConfigDict(extra="ignore")
