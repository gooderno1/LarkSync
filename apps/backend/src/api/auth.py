from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from src.services import AuthError, AuthService, AuthStateStore

router = APIRouter(prefix="/auth", tags=["auth"])

state_store = AuthStateStore()


@router.get("/login")
async def login(
    request: Request,
    state: str | None = Query(default=None),
    redirect: str | None = Query(default=None),
):
    auth_service = AuthService()
    redirect_target = _sanitize_redirect(redirect, request)
    state_value = state or state_store.issue(redirect_target)
    try:
        url = auth_service.build_authorize_url(state_value)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url)


@router.get("/callback")
async def callback(code: str = Query(...), state: str | None = Query(default=None)):
    redirect_target = None
    if state:
        valid, redirect_target = state_store.consume(state)
        if not valid:
            raise HTTPException(status_code=400, detail="state 无效或已过期")

    auth_service = AuthService()
    try:
        token = await auth_service.exchange_code(code)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # 捕获所有未预期异常（如 keyring 失败），返回详细错误而非裸 500
        raise HTTPException(
            status_code=500,
            detail=f"OAuth 回调处理异常: {type(exc).__name__}: {exc}",
        ) from exc

    if redirect_target:
        return RedirectResponse(redirect_target)
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


def _sanitize_redirect(redirect: str | None, request: Request) -> str | None:
    if not redirect:
        return None
    value = redirect.strip()
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.scheme:
        return value if value.startswith("/") else None
    if parsed.scheme not in {"http", "https"}:
        return None

    hostname = parsed.hostname or ""
    if hostname in {"localhost", "127.0.0.1"}:
        return value

    request_host = request.headers.get("host", "").split(":")[0]
    if request_host and hostname == request_host:
        return value
    return None
