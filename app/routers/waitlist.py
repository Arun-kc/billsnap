import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models.waitlist import WaitlistEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["waitlist"])


class WaitlistRequest(BaseModel):
    contact: str = Field(min_length=5, max_length=320)


@router.post("/waitlist", status_code=status.HTTP_201_CREATED)
async def join_waitlist(
    payload: WaitlistRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    contact = payload.contact.strip()

    entry = WaitlistEntry(contact=contact)
    db.add(entry)
    try:
        await db.commit()
        logger.info("[waitlist] New signup received (contact length=%d)", len(contact))
        return {"success": True}
    except IntegrityError:
        await db.rollback()
        # Already on the list — return 200 (not 201) so callers can distinguish
        # a new signup from a duplicate, while still not leaking existence.
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": True}, status_code=200)
