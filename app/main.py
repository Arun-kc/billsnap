import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import bills, dashboard, jobs, waitlist

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BillSnap API",
    description="Bill & receipt digitization for Indian small businesses",
    version="0.1.0",
)

_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bills.router)
app.include_router(jobs.router)
app.include_router(dashboard.router)
app.include_router(waitlist.router)

_worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup() -> None:
    global _worker_task
    from .workers.ocr_worker import run_worker
    _worker_task = asyncio.create_task(run_worker())
    logger.info("BillSnap API started (env=%s)", settings.app_env)


@app.on_event("shutdown")
async def shutdown() -> None:
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    logger.info("BillSnap API stopped")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "env": settings.app_env}
