from fastapi import FastAPI

app = FastAPI(title="LarkSync API")


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
