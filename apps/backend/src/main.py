from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import auth_router

app = FastAPI(title="LarkSync API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
