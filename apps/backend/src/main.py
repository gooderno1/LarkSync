import asyncio
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
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
from src.core.logging import init_logging
from src.db.session import init_db
from src.api.watcher import watcher_manager
from src.api.sync_tasks import runner as sync_runner, service as sync_task_service
from src.services.sync_scheduler import SyncScheduler
from src.services.conflict_service import ConflictService

app = FastAPI(title="LarkSync API")
sync_scheduler = SyncScheduler(runner=sync_runner, task_service=sync_task_service)
conflict_service = ConflictService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3666", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- API Routers ----
app.include_router(auth_router)
app.include_router(config_router)
app.include_router(conflicts_router)
app.include_router(drive_router)
app.include_router(watcher_router)
app.include_router(events_router)
app.include_router(sync_router)
app.include_router(system_router)


# ---- 托盘聚合状态接口 ----
@app.get("/tray/status", tags=["tray"])
async def tray_status() -> dict:
    """返回托盘应用需要的聚合状态信息。"""
    statuses = sync_runner.list_statuses()
    tasks = await sync_task_service.list_tasks()
    conflicts = await conflict_service.list_conflicts(include_resolved=False)
    running = sum(1 for s in statuses.values() if s.state == "running")
    paused = sum(1 for t in tasks if not t.enabled)
    errors = [s.last_error for s in statuses.values() if s.last_error]
    last_sync = max(
        (s.finished_at for s in statuses.values() if s.finished_at),
        default=None,
    )
    return {
        "backend_running": True,
        "tasks_total": len(tasks),
        "tasks_running": running,
        "tasks_paused": paused,
        "unresolved_conflicts": len(conflicts),
        "last_error": errors[0] if errors else None,
        "last_sync_time": last_sync,
    }


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


@app.on_event("startup")
async def startup_event() -> None:
    init_logging()
    watcher_manager.set_loop(asyncio.get_running_loop())
    await init_db()
    await sync_scheduler.start()
    if _FRONTEND_DIST.is_dir():
        logger.info("前端静态文件已挂载: {}", _FRONTEND_DIST)
    else:
        logger.info("未检测到前端构建产物（开发模式），跳过静态文件服务")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await sync_scheduler.stop()


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}


# ---- 静态前端服务（生产模式） ----
# 检测前端构建产物 dist/ 目录：
#   - 项目根 / apps / frontend / dist
#   - 当前文件: apps / backend / src / main.py → parents[3] = 项目根
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_FRONTEND_DIST = _PROJECT_ROOT / "apps" / "frontend" / "dist"
_INDEX_HTML = _FRONTEND_DIST / "index.html"

if _FRONTEND_DIST.is_dir() and _INDEX_HTML.is_file():
    # 挂载 /assets 静态资源（Vite 构建输出的 JS/CSS/images）
    _ASSETS_DIR = _FRONTEND_DIST / "assets"
    if _ASSETS_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="frontend-assets")

    # 挂载其他静态文件（favicon、oauth-guide.html 等）
    # 注意：不能直接 mount "/"，否则会覆盖 API 路由
    # 使用 catch-all 路由实现 SPA fallback
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

    # MIME 类型映射（常见静态资源）
    _MIME_MAP = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".svg": "image/svg+xml", ".ico": "image/x-icon",
        ".webp": "image/webp", ".css": "text/css", ".js": "application/javascript",
        ".json": "application/json", ".woff": "font/woff", ".woff2": "font/woff2",
        ".ttf": "font/ttf", ".html": "text/html", ".txt": "text/plain",
    }

    # SPA Fallback：优先检查 dist 目录下的静态文件，否则返回 index.html
    # 注意：这必须放在所有路由之后
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # 排除 API 路径和 WebSocket
        if full_path.startswith(("auth/", "config/", "conflicts/", "drive/",
                                  "sync/", "watcher/", "system/", "ws/",
                                  "health", "tray/", "docs", "openapi")):
            return HTMLResponse("Not found", status_code=404)

        # 先检查 dist 目录下是否有对应的静态文件
        static_file = _FRONTEND_DIST / full_path
        if static_file.is_file() and _FRONTEND_DIST in static_file.resolve().parents:
            suffix = static_file.suffix.lower()
            media_type = _MIME_MAP.get(suffix)
            return FileResponse(str(static_file), media_type=media_type)

        # 不存在的路径 → SPA fallback（返回 index.html，由前端路由处理）
        return FileResponse(str(_INDEX_HTML), media_type="text/html")
