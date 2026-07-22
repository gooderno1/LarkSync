import asyncio
import os
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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
from src.api.sync_tasks import (
    event_store,
    runner as sync_runner,
    run_event_service,
    service as sync_task_service,
)
from src.api.watcher import watcher_manager
from src.core.logging import init_logging
from src.core.config import AppConfig, ConfigManager, RuntimeProfile
from src.core.paths import bundle_root
from src.db.session import init_db
from src.services.conflict_service import ConflictService
from src.services.sync_log_maintenance_service import SyncLogMaintenanceService
from src.services.sync_run_service import SyncRunService
from src.services.sync_scheduler import SyncScheduler
from src.services.update_scheduler import UpdateScheduler
from src.api.system import build_desktop_status, desktop_status_to_tray_status

InitDbFn = Callable[[], Awaitable[Any]]
InitLoggingFn = Callable[[], None]
RecoverRunsFn = Callable[[], Awaitable[int]]


async def _recover_interrupted_runs() -> int:
    return await SyncRunService().interrupt_running_runs()


def _as_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _expose_error_detail() -> bool:
    # 默认关闭错误详情回显，避免将内部异常直接暴露给客户端。
    return _as_bool_env("LARKSYNC_DEBUG_ERRORS", default=False)


def _runtime_mutation_denied(config: AppConfig, method: str, path: str) -> bool:
    if config.runtime_profile is not RuntimeProfile.snapshot_test:
        return False
    if method.strip().upper() in {"GET", "HEAD", "OPTIONS"}:
        return False
    return path != "/system/shutdown"


sync_scheduler = SyncScheduler(runner=sync_runner, task_service=sync_task_service)
conflict_service = ConflictService()
log_maintenance_service = SyncLogMaintenanceService(
    run_event_service=run_event_service,
    event_store=event_store,
)
update_scheduler = UpdateScheduler()

# ---- 静态前端服务（生产模式） ----
# 检测前端构建产物 dist/ 目录：
#   - 项目根 / apps / frontend / dist
#   - 当前文件: apps / backend / src / main.py → parents[3] = 项目根
_BUNDLE_ROOT = bundle_root()
_PROJECT_ROOT = _BUNDLE_ROOT or Path(__file__).resolve().parents[3]
_FRONTEND_DIST = _PROJECT_ROOT / "apps" / "frontend" / "dist"
_INDEX_HTML = _FRONTEND_DIST / "index.html"
_MIME_MAP = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".ico": "image/x-icon",
    ".webp": "image/webp", ".css": "text/css", ".js": "application/javascript",
    ".json": "application/json", ".woff": "font/woff", ".woff2": "font/woff2",
    ".ttf": "font/ttf", ".html": "text/html", ".txt": "text/plain",
}


def _log_frontend_mount_status() -> None:
    if _FRONTEND_DIST.is_dir():
        logger.info("前端静态文件已挂载: {}", _FRONTEND_DIST)
    else:
        logger.info("未检测到前端构建产物（开发模式），跳过静态文件服务")


def _build_lifespan(
    *,
    sync_scheduler_instance: SyncScheduler,
    log_maintenance_service_instance: SyncLogMaintenanceService,
    update_scheduler_instance: UpdateScheduler,
    watcher_manager_instance,
    init_db_fn: InitDbFn,
    recover_runs_fn: RecoverRunsFn,
    init_logging_fn: InitLoggingFn,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_logging_fn()
        watcher_manager_instance.set_loop(asyncio.get_running_loop())
        await init_db_fn()
        recovered_runs = await recover_runs_fn()
        if recovered_runs:
            logger.warning("已恢复 {} 条上次退出时遗留的运行记录", recovered_runs)
        await log_maintenance_service_instance.start()
        await sync_scheduler_instance.start()
        await update_scheduler_instance.start()
        _log_frontend_mount_status()
        try:
            yield
        finally:
            await log_maintenance_service_instance.stop()
            await sync_scheduler_instance.stop()
            await update_scheduler_instance.stop()
            close_runner = getattr(app.state.sync_runner, "close", None)
            if callable(close_runner):
                await close_runner()

    return lifespan


def _configure_static_frontend_routes(app: FastAPI) -> None:
    if not (_FRONTEND_DIST.is_dir() and _INDEX_HTML.is_file()):
        return

    assets_dir = _FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/oauth-guide.html", include_in_schema=False)
    async def serve_oauth_guide():
        oauth_file = _FRONTEND_DIST / "oauth-guide.html"
        if oauth_file.is_file():
            return FileResponse(str(oauth_file), media_type="text/html")
        return HTMLResponse("Not found", status_code=404)

    @app.get("/favicon.ico", include_in_schema=False)
    async def serve_favicon():
        favicon = _FRONTEND_DIST / "favicon.ico"
        if favicon.is_file():
            return FileResponse(str(favicon))
        return HTMLResponse("", status_code=204)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith(("auth/", "config/", "conflicts/", "drive/",
                                  "sync/", "watcher/", "system/", "ws/",
                                  "health", "tray/", "docs", "openapi")):
            return HTMLResponse("Not found", status_code=404)

        static_file = _FRONTEND_DIST / full_path
        if static_file.is_file() and _FRONTEND_DIST in static_file.resolve().parents:
            suffix = static_file.suffix.lower()
            media_type = _MIME_MAP.get(suffix)
            return FileResponse(str(static_file), media_type=media_type)

        return FileResponse(str(_INDEX_HTML), media_type="text/html")


def create_app(
    *,
    sync_runner_service=sync_runner,
    sync_task_service_instance=sync_task_service,
    conflict_service_instance=conflict_service,
    sync_scheduler_instance=sync_scheduler,
    log_maintenance_service_instance=log_maintenance_service,
    update_scheduler_instance=update_scheduler,
    watcher_manager_instance=watcher_manager,
    init_db_fn: InitDbFn = init_db,
    recover_runs_fn: RecoverRunsFn = _recover_interrupted_runs,
    init_logging_fn: InitLoggingFn = init_logging,
) -> FastAPI:
    app = FastAPI(
        title="LarkSync API",
        lifespan=_build_lifespan(
            sync_scheduler_instance=sync_scheduler_instance,
            log_maintenance_service_instance=log_maintenance_service_instance,
            update_scheduler_instance=update_scheduler_instance,
            watcher_manager_instance=watcher_manager_instance,
            init_db_fn=init_db_fn,
            recover_runs_fn=recover_runs_fn,
            init_logging_fn=init_logging_fn,
        ),
    )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        """全局异常处理：默认返回通用错误，开发诊断可通过环境变量开启详情。"""
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        error_id = uuid.uuid4().hex[:12]
        logger.error(
            "未处理异常 id={} {} {}: {}",
            error_id,
            request.method,
            request.url.path,
            exc,
        )
        logger.debug("Traceback:\n{}", "".join(tb))
        detail = "Internal Server Error"
        if _expose_error_detail():
            detail = f"{type(exc).__name__}: {exc}"
        return JSONResponse(
            status_code=500,
            content={
                "detail": detail,
                "error_id": error_id,
                "path": str(request.url.path),
            },
        )

    @app.middleware("http")
    async def enforce_runtime_profile(request: Request, call_next):
        config = ConfigManager.get().config
        if _runtime_mutation_denied(config, request.method, request.url.path):
            return JSONResponse(
                status_code=403,
                content={"detail": "snapshot mode is read-only"},
            )
        return await call_next(request)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        # 静态资源请求不记录日志（减少噪音）
        path = request.url.path
        if path.startswith("/assets/") or path.endswith((".js", ".css", ".ico", ".png", ".svg", ".woff2")):
            return await call_next(request)
        start = time.time()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("请求处理失败: {} {}", request.method, path)
            raise
        duration_ms = (time.time() - start) * 1000
        logger.info(
            "{} {} -> {} ({:.1f} ms)",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
        return response

    app.state.sync_scheduler = sync_scheduler_instance
    app.state.sync_runner = sync_runner_service
    app.state.sync_task_service = sync_task_service_instance
    app.state.conflict_service = conflict_service_instance
    app.state.log_maintenance_service = log_maintenance_service_instance
    app.state.update_scheduler = update_scheduler_instance

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3666",
            "http://localhost:18765",
            "http://localhost:8000",
        ],
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

    @app.get("/tray/status", tags=["tray"])
    async def tray_status(request: Request) -> dict:
        """返回托盘应用需要的聚合状态信息。"""
        desktop_status = await build_desktop_status(request)
        return desktop_status_to_tray_status(desktop_status).model_dump()

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        return {"status": "ok"}

    _configure_static_frontend_routes(app)
    return app


app = create_app()
