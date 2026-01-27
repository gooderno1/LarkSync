from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from src.services import AuthError, AuthService, AuthStateStore

router = APIRouter(prefix="/auth", tags=["auth"])

state_store = AuthStateStore()


@router.get("/login")
async def login(state: str | None = Query(default=None)):
    auth_service = AuthService()
    state_value = state or state_store.issue()
    url = auth_service.build_authorize_url(state_value)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(code: str = Query(...), state: str | None = Query(default=None)):
    if state and not state_store.consume(state):
        raise HTTPException(status_code=400, detail="state 无效或已过期")

    auth_service = AuthService()
    try:
        token = await auth_service.exchange_code(code)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "connected": True,
        "expires_at": token.expires_at,
    }


@router.get("/status")
async def status():
    auth_service = AuthService()
    token = auth_service.get_cached_token()
    return {
        "connected": token is not None,
        "expires_at": token.expires_at if token else None,
    }


@router.post("/logout")
async def logout():
    auth_service = AuthService()
    store = auth_service._token_store
    store.clear()
    return {"connected": False}
