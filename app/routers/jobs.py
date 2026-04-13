import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user, get_db
from ..models.ocr_job import OcrJob
from ..models.user import User
from ..schemas.ocr_job import JobStatusOut

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobStatusOut)
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(OcrJob).where(OcrJob.id == job_id, OcrJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    bill_id = job.bill.id if job.bill else None

    return JobStatusOut(
        job_id=job.id,
        status=job.status,
        bill_id=bill_id,
        extraction_confidence=float(job.extraction_confidence) if job.extraction_confidence else None,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
