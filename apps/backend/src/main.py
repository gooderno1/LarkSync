import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import auth_router, drive_router, events_router, watcher_router
from src.api.watcher import watcher_manager

app = FastAPI(title="LarkSync API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(drive_router)
app.include_router(watcher_router)
app.include_router(events_router)


@app.on_event("startup")
async def startup_event() -> None:
    watcher_manager.set_loop(asyncio.get_running_loop())


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
