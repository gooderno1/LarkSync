from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.account_runtime import account_runtime_registry
from src.services.account_service import AccountService
from src.services.auth_session_service import AuthSessionService, PendingSession
from src.services.auth_service import AuthError, AuthService
from src.core.account_context import account_scope


router = APIRouter(tags=["accounts"])
account_service = AccountService()
auth_sessions = AuthSessionService(account_service=account_service)


class ManualAppProfileRequest(BaseModel):
    app_id: str = Field(min_length=1)
    app_secret: str = Field(min_length=1)
    brand: str = "feishu"
    display_name: str | None = None


class RegistrationRequest(BaseModel):
    brand: str = "feishu"


class DeviceSessionRequest(BaseModel):
    app_profile_id: str


class ActiveAccountRequest(BaseModel):
    account_id: str | None


class NotificationReadRequest(BaseModel):
    read: bool = True


def _session_response(session: PendingSession) -> dict[str, object]:
    return {
        "session_id": session.id,
        "status": "pending",
        "brand": session.brand,
        "user_code": session.user_code,
        "verification_uri": session.verification_uri,
        "verification_uri_complete": session.verification_uri_complete,
        "expires_at": session.expires_at,
        "interval": session.interval,
    }


def _refresh_requires_reauthorization(exc: AuthError) -> bool:
    return exc.code in {"20026", "20064", "20073"} or any(
        marker in str(exc)
        for marker in ("缺少登录凭证", "refresh_token 不可用", "请重新连接")
    )


@router.get("/accounts")
async def list_accounts() -> list[dict[str, object]]:
    return [asdict(item) for item in await account_service.list_accounts()]


@router.get("/accounts/summary")
async def list_account_summaries() -> list[dict[str, object]]:
    return [asdict(item) for item in await account_service.list_account_summaries()]


@router.get("/accounts/{account_id}")
async def get_account(account_id: str) -> dict[str, object]:
    account = await account_service.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    return asdict(account)


@router.put("/ui/active-account")
async def set_active_account(payload: ActiveAccountRequest) -> dict[str, object]:
    try:
        await account_service.set_active_account(payload.account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"active_account_id": payload.account_id}


@router.post("/accounts/{account_id}/pause")
async def pause_account(account_id: str) -> dict[str, object]:
    return await _set_paused(account_id, True)


@router.post("/accounts/{account_id}/resume")
async def resume_account(account_id: str) -> dict[str, object]:
    return await _set_paused(account_id, False)


async def _set_paused(account_id: str, paused: bool) -> dict[str, object]:
    try:
        await account_service.set_paused(account_id, paused)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"account_id": account_id, "paused": paused}


@router.post("/accounts/{account_id}/disconnect")
async def disconnect_account(account_id: str) -> dict[str, object]:
    try:
        await account_service.disconnect(account_id)
        await account_runtime_registry.reload()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"account_id": account_id, "state": "auth_required"}


@router.delete("/accounts/{account_id}")
async def remove_account(account_id: str) -> dict[str, object]:
    try:
        await account_service.remove(account_id)
        await account_runtime_registry.reload()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"account_id": account_id, "state": "removed"}


@router.get("/app-profiles")
async def list_app_profiles() -> list[dict[str, object]]:
    return [asdict(item) for item in await account_service.list_app_profiles()]


@router.post("/app-profiles/manual")
async def create_manual_app_profile(
    payload: ManualAppProfileRequest,
) -> dict[str, object]:
    try:
        item = await account_service.create_app_profile(
            app_id=payload.app_id,
            app_secret=payload.app_secret,
            brand=payload.brand,
            source="manual",
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return asdict(item)


@router.post("/app-profiles/registration-sessions")
async def begin_app_registration(payload: RegistrationRequest) -> dict[str, object]:
    try:
        return _session_response(await auth_sessions.begin_registration(payload.brand))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/app-profiles/registration-sessions/{session_id}")
async def poll_app_registration(session_id: str) -> dict[str, object]:
    try:
        return await auth_sessions.poll_registration(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/app-profiles/registration-sessions/{session_id}")
async def cancel_app_registration(session_id: str) -> dict[str, bool]:
    return {"cancelled": auth_sessions.cancel(session_id)}


@router.post("/auth/device-sessions")
async def begin_device_session(payload: DeviceSessionRequest) -> dict[str, object]:
    try:
        return _session_response(
            await auth_sessions.begin_device(payload.app_profile_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/auth/device-sessions/{session_id}")
async def poll_device_session(session_id: str) -> dict[str, object]:
    try:
        return await auth_sessions.poll_device(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/auth/device-sessions/{session_id}")
async def cancel_device_session(session_id: str) -> dict[str, bool]:
    return {"cancelled": auth_sessions.cancel(session_id)}


@router.post("/accounts/{account_id}/reauthorize-sessions")
async def begin_reauthorize_session(account_id: str) -> dict[str, object]:
    try:
        account, _profile, _secret = await account_service.get_account_credentials(
            account_id
        )
        return _session_response(
            await auth_sessions.begin_device(
                account.app_profile_id, target_account_id=account.id
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/refresh")
async def refresh_account_token(account_id: str) -> dict[str, object]:
    account = await account_service.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    try:
        with account_scope(account_id):
            token = await AuthService().refresh()
        await account_service.record_auth_result(account_id, state="connected")
        return {
            "account_id": account_id,
            "status": "refreshed",
            "auth_protocol": account.auth_protocol,
            "expires_at": token.expires_at,
            "refresh_expires_at": token.refresh_expires_at,
        }
    except AuthError as exc:
        await account_service.record_auth_result(
            account_id,
            state=(
                "auth_required"
                if _refresh_requires_reauthorization(exc)
                else account.state
            ),
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/notifications")
async def list_notifications(
    account_id: str | None = Query(default=None),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, object]]:
    return [
        asdict(item)
        for item in await account_service.list_notifications(
            account_id=account_id,
            unread_only=unread_only,
            limit=limit,
        )
    ]


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str, payload: NotificationReadRequest
) -> dict[str, object]:
    try:
        await account_service.mark_notification_read(
            notification_id, read=payload.read
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": notification_id, "read": payload.read}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    account_id: str | None = Query(default=None),
) -> dict[str, int]:
    return {
        "updated": await account_service.mark_all_notifications_read(account_id)
    }


__all__ = ["router"]
