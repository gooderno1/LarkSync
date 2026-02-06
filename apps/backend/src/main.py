import asyncio
import time

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api import (
    auth_router,
    config_router,
    conflicts_router,
    drive_router,
    events_router,
    system_router,
    sync_router,
    watcher_router,
)
from src.core.logging import init_logging
from src.db.session import init_db
from src.api.watcher import watcher_manager
from src.api.sync_tasks import runner as sync_runner, service as sync_task_service
from src.services.sync_scheduler import SyncScheduler

app = FastAPI(title="LarkSync API")
sync_scheduler = SyncScheduler(runner=sync_runner, task_service=sync_task_service)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3666"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(config_router)
app.include_router(conflicts_router)
app.include_router(drive_router)
app.include_router(watcher_router)
app.include_router(events_router)
app.include_router(sync_router)
app.include_router(system_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("请求处理失败: {} {}", request.method, request.url.path)
        raise
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "{} {} -> {} ({:.1f} ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.on_event("startup")
async def startup_event() -> None:
    init_logging()
    watcher_manager.set_loop(asyncio.get_running_loop())
    await init_db()
    await sync_scheduler.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await sync_scheduler.stop()


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
