from .auth import router as auth_router
from .config import router as config_router
from .conflicts import router as conflicts_router
from .drive import router as drive_router
from .sync_tasks import router as sync_router
from .watcher import events_router, watcher_router

__all__ = [
    "auth_router",
    "config_router",
    "conflicts_router",
    "drive_router",
    "sync_router",
    "watcher_router",
    "events_router",
]
