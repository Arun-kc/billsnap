import uuid
from datetime import datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str


class JobStatusOut(BaseModel):
    job_id: uuid.UUID
    status: str
    bill_id: uuid.UUID | None
    extraction_confidence: float | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}
