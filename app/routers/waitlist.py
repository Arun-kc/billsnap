import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models.waitlist import WaitlistEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["waitlist"])


class WaitlistRequest(BaseModel):
    contact: str


@router.post("/waitlist", status_code=status.HTTP_201_CREATED)
async def join_waitlist(
    payload: WaitlistRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    contact = payload.contact.strip()
    if len(contact) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid email or WhatsApp number.",
        )

    entry = WaitlistEntry(contact=contact)
    db.add(entry)
    try:
        await db.commit()
        logger.info("[waitlist] New signup received (contact length=%d)", len(contact))
    except IntegrityError:
        await db.rollback()
        # Already on the list — treat as success so we don't leak whether an
        # email/number is registered.

    return {"success": True}
