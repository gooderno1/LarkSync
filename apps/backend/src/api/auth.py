from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from loguru import logger

from src.core.device import current_device_id
from src.services import AuthError, AuthService, AuthStateStore
from src.services.lark_cli_auth_service import LarkCliAuthStatus, get_lark_cli_auth_status
from src.services.update_service import UpdateService

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


@router.get("/authorize-url")
async def authorize_url(
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
    return {
        "authorize_url": url,
        "state": state_value,
        "expires_in": state_store.ttl_seconds,
        "local_callback": _authorize_url_has_local_callback(url),
    }


@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    state: str | None = Query(default=None),
):
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

    _schedule_identity_hydration(auth_service)
    _schedule_login_update_check(request)

    if redirect_target:
        return RedirectResponse(redirect_target)
    return {
        "connected": True,
        "expires_at": token.expires_at,
    }


@router.get("/status")
async def status():
    auth_service = AuthService()
    # 启动页只回答“已授权/未授权”。不刷新 token、不请求飞书、不探测权限。
    # 首次读取 Windows 凭据管理器放到工作线程，避免阻塞整个 API 事件循环。
    token = await asyncio.to_thread(auth_service.get_cached_token)
    result: dict[str, object] = {
        "connected": token is not None,
        "expires_at": token.expires_at if token else None,
        "open_id": token.open_id if token else None,
        "account_name": token.account_name if token else None,
        "device_id": current_device_id(),
    }
    return result


@router.get("/cli/status", response_model=LarkCliAuthStatus)
async def cli_status() -> LarkCliAuthStatus:
    return await asyncio.to_thread(get_lark_cli_auth_status)


@router.post("/logout")
async def logout():
    auth_service = AuthService()
    store = auth_service._token_store
    await asyncio.to_thread(store.clear)
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


def _authorize_url_has_local_callback(authorize_url: str) -> bool:
    parsed = urlparse(authorize_url)
    params = parse_qs(parsed.query)
    redirect_uri = params.get("redirect_uri", [""])[0]
    callback = urlparse(redirect_uri)
    return (callback.hostname or "") in {"localhost", "127.0.0.1"}


def _schedule_login_update_check(request: Request) -> None:
    async def _check_once() -> None:
        # 登录跳转优先；更新检查不与回调后的首屏请求竞争网络和事件循环。
        await asyncio.sleep(5)
        scheduler = getattr(request.app.state, "update_scheduler", None)
        service = scheduler.service if scheduler is not None else UpdateService()
        try:
            await service.check_for_updates(force=True)
        except Exception as exc:
            logger.debug("登录后更新检查失败: {}", exc)

    asyncio.create_task(_check_once())


def _schedule_identity_hydration(auth_service: AuthService) -> None:
    async def _hydrate_once() -> None:
        # 昵称只影响展示，不应延长 OAuth 回调。首屏稳定后再异步补齐。
        await asyncio.sleep(2)
        try:
            await auth_service.ensure_cached_identity()
        except Exception as exc:
            logger.debug("登录后补齐身份信息失败: {}", exc)

    asyncio.create_task(_hydrate_once())
