from __future__ import annotations

import argparse
import ipaddress
import json
import datetime as dt
import uuid
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urlencode, urlparse

DEFAULT_BASE_URL = "http://localhost:8000"
MODE_CHOICES = ("download_only", "bidirectional", "upload_only")
UNIT_CHOICES = ("seconds", "hours", "days")
TASK_MD_MODE_CHOICES = ("enhanced", "download_only", "doc_only")
TASK_UPDATE_MODE_CHOICES = ("auto", "partial", "full")
DELETE_POLICY_CHOICES = ("off", "safe", "strict")
LOG_ORDER_CHOICES = ("desc", "asc")
CONFLICT_ACTION_CHOICES = ("use_local", "use_cloud")
WORKFLOW_TEMPLATE_CHOICES = ("daily-cache", "refresh-cache", "conflict-audit")
WORKFLOW_ENTRYPOINT_CHOICES = ("cli", "helper", "wsl_helper")
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
WORKFLOW_RUNS_DIR = DATA_DIR / "workflows"


@dataclass(frozen=True)
class ApiResult:
    ok: bool
    status_code: int
    data: Any


def _normalize_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    return value or DEFAULT_BASE_URL


def _build_url(base_url: str, path: str, query: dict[str, Any] | None = None) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    url = f"{_normalize_base_url(base_url)}{path}"
    if not query:
        return url
    filtered: list[tuple[str, str]] = []
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                if item is None or item == "":
                    continue
                filtered.append((key, str(item)))
            continue
        if value == "":
            continue
        filtered.append((key, str(value)))
    if not filtered:
        return url
    return f"{url}?{urlencode(filtered)}"


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_base_url(base_url: str, allow_remote: bool = False) -> str:
    normalized = _normalize_base_url(base_url)
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("base_url 仅支持 http 或 https")

    host = parsed.hostname or ""
    if not host:
        raise ValueError("base_url 缺少有效主机名")

    if not allow_remote and not _is_loopback_host(host):
        raise ValueError(
            "默认仅允许 localhost/127.0.0.1/::1。"
            "如需连接远程地址，请显式传入 --allow-remote-base-url 并确认目标可信。"
        )

    return normalized


def _validate_hhmm(value: str) -> bool:
    parts = value.split(":")
    if len(parts) != 2:
        return False
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59


def infer_md_sync_mode(sync_mode: str) -> str:
    if sync_mode == "download_only":
        return "download_only"
    return "enhanced"


def build_download_config_payload(value: float, unit: str, daily_time: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "download_interval_value": float(value),
        "download_interval_unit": unit,
    }
    if unit == "days":
        if not _validate_hhmm(daily_time):
            raise ValueError("daily_time 格式无效，必须为 HH:MM")
        payload["download_daily_time"] = daily_time
    return payload


def build_task_payload(
    *,
    name: str,
    local_path: str,
    cloud_folder_token: str,
    sync_mode: str,
    enabled: bool = True,
    update_mode: str = "auto",
    md_sync_mode: str | None = None,
    delete_policy: str | None = None,
    delete_grace_minutes: int | None = None,
    cloud_folder_name: str | None = None,
    base_path: str | None = None,
    is_test: bool = False,
) -> dict[str, Any]:
    if sync_mode not in MODE_CHOICES:
        raise ValueError(f"sync_mode 不支持: {sync_mode}")
    if update_mode not in TASK_UPDATE_MODE_CHOICES:
        raise ValueError(f"update_mode 不支持: {update_mode}")
    if not local_path.strip():
        raise ValueError("local_path 不能为空")
    if not cloud_folder_token.strip():
        raise ValueError("cloud_folder_token 不能为空")
    final_md_sync_mode = md_sync_mode or infer_md_sync_mode(sync_mode)
    if final_md_sync_mode not in TASK_MD_MODE_CHOICES:
        raise ValueError(f"md_sync_mode 不支持: {final_md_sync_mode}")
    if delete_policy is not None and delete_policy not in DELETE_POLICY_CHOICES:
        raise ValueError(f"delete_policy 不支持: {delete_policy}")
    payload: dict[str, Any] = {
        "name": name.strip() or "LarkSync CLI 任务",
        "local_path": str(Path(local_path).expanduser()),
        "cloud_folder_token": cloud_folder_token.strip(),
        "sync_mode": sync_mode,
        "update_mode": update_mode,
        "md_sync_mode": final_md_sync_mode,
        "enabled": bool(enabled),
        "is_test": bool(is_test),
    }
    if cloud_folder_name and cloud_folder_name.strip():
        payload["cloud_folder_name"] = cloud_folder_name.strip()
    if base_path and base_path.strip():
        payload["base_path"] = str(Path(base_path).expanduser())
    if delete_policy is not None:
        payload["delete_policy"] = delete_policy
    if delete_grace_minutes is not None:
        payload["delete_grace_minutes"] = int(delete_grace_minutes)
    return payload


def _request_json(
    *,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> ApiResult:
    data_bytes: bytes | None = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(
        _build_url(base_url, path, query=query),
        data=data_bytes,
        headers=headers,
        method=method.upper(),
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            return ApiResult(ok=True, status_code=resp.getcode(), data=parsed)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload_data = json.loads(body) if body else {"detail": body}
        except json.JSONDecodeError:
            payload_data = {"detail": body}
        return ApiResult(ok=False, status_code=exc.code, data=payload_data)
    except Exception as exc:  # noqa: BLE001
        return ApiResult(
            ok=False,
            status_code=0,
            data={"detail": f"{type(exc).__name__}: {exc}"},
        )


def _must_ok(result: ApiResult, action: str) -> Any:
    if result.ok:
        return result.data
    detail = result.data.get("detail") if isinstance(result.data, dict) else result.data
    raise RuntimeError(f"{action} 失败: HTTP {result.status_code} - {detail}")


def _find_existing_task(
    *, base_url: str, local_path: str, cloud_folder_token: str
) -> dict[str, Any] | None:
    result = _request_json(base_url=base_url, method="GET", path="/sync/tasks")
    if not result.ok or not isinstance(result.data, list):
        return None
    normalized_path = str(Path(local_path).expanduser())
    for item in result.data:
        if (
            isinstance(item, dict)
            and item.get("local_path") == normalized_path
            and item.get("cloud_folder_token") == cloud_folder_token
        ):
            return item
    return None


def do_check(base_url: str) -> dict[str, Any]:
    health = _request_json(base_url=base_url, method="GET", path="/health")
    auth = _request_json(base_url=base_url, method="GET", path="/auth/status")
    config = _request_json(base_url=base_url, method="GET", path="/config")
    tasks = _request_json(base_url=base_url, method="GET", path="/sync/tasks")
    task_count = len(tasks.data) if tasks.ok and isinstance(tasks.data, list) else 0
    connected = (
        bool(auth.data.get("connected"))
        if auth.ok and isinstance(auth.data, dict)
        else False
    )
    return {
        "base_url": _normalize_base_url(base_url),
        "health": {"ok": health.ok, "status_code": health.status_code, "data": health.data},
        "auth": {"ok": auth.ok, "status_code": auth.status_code, "data": auth.data},
        "config": {"ok": config.ok, "status_code": config.status_code, "data": config.data},
        "tasks": {
            "ok": tasks.ok,
            "status_code": tasks.status_code,
            "count": task_count,
            "data": tasks.data,
        },
        "ready_for_sync": bool(health.ok and connected),
    }


def do_auth_status(base_url: str) -> dict[str, Any]:
    data = _must_ok(
        _request_json(base_url=base_url, method="GET", path="/auth/status"),
        "获取授权状态",
    )
    return {"action": "auth-status", "status": data}


def do_get_config(base_url: str) -> dict[str, Any]:
    data = _must_ok(
        _request_json(base_url=base_url, method="GET", path="/config"),
        "获取配置",
    )
    return {"action": "config-get", "config": data}


def do_set_config(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = _must_ok(
        _request_json(base_url=base_url, method="PUT", path="/config", payload=payload),
        "更新配置",
    )
    return {"action": "config-set", "payload": payload, "config": data}


def do_configure_download(
    base_url: str, value: float, unit: str, daily_time: str
) -> dict[str, Any]:
    if unit not in UNIT_CHOICES:
        raise ValueError(f"download_unit 不支持: {unit}")
    payload = build_download_config_payload(value, unit, daily_time)
    return do_set_config(base_url, payload)


def do_list_tasks(base_url: str) -> dict[str, Any]:
    items = _must_ok(
        _request_json(base_url=base_url, method="GET", path="/sync/tasks"),
        "获取任务列表",
    )
    return {
        "action": "task-list",
        "items": items,
        "total": len(items) if isinstance(items, list) else 0,
    }


def do_list_task_status(base_url: str) -> dict[str, Any]:
    items = _must_ok(
        _request_json(base_url=base_url, method="GET", path="/sync/tasks/status"),
        "获取任务状态列表",
    )
    return {
        "action": "task-status-list",
        "items": items,
        "total": len(items) if isinstance(items, list) else 0,
    }


def do_create_task(
    *,
    base_url: str,
    name: str,
    local_path: str,
    cloud_folder_token: str,
    sync_mode: str,
    enabled: bool = True,
    update_mode: str = "auto",
    md_sync_mode: str | None = None,
    delete_policy: str | None = None,
    delete_grace_minutes: int | None = None,
    cloud_folder_name: str | None = None,
    base_path: str | None = None,
    is_test: bool = False,
) -> dict[str, Any]:
    payload = build_task_payload(
        name=name,
        local_path=local_path,
        cloud_folder_token=cloud_folder_token,
        sync_mode=sync_mode,
        enabled=enabled,
        update_mode=update_mode,
        md_sync_mode=md_sync_mode,
        delete_policy=delete_policy,
        delete_grace_minutes=delete_grace_minutes,
        cloud_folder_name=cloud_folder_name,
        base_path=base_path,
        is_test=is_test,
    )
    created = _request_json(base_url=base_url, method="POST", path="/sync/tasks", payload=payload)
    if created.ok:
        return {"action": "task-create", "created": True, "task": created.data}
    if created.status_code == 409:
        existing = _find_existing_task(
            base_url=base_url,
            local_path=local_path,
            cloud_folder_token=cloud_folder_token,
        )
        if existing:
            return {
                "action": "task-create",
                "created": False,
                "reason": "task_conflict_reused_existing",
                "task": existing,
                "detail": created.data,
            }
    detail = created.data.get("detail") if isinstance(created.data, dict) else created.data
    raise RuntimeError(f"创建任务失败: HTTP {created.status_code} - {detail}")


def do_update_task(
    *,
    base_url: str,
    task_id: str,
    name: str | None = None,
    local_path: str | None = None,
    cloud_folder_token: str | None = None,
    cloud_folder_name: str | None = None,
    base_path: str | None = None,
    sync_mode: str | None = None,
    update_mode: str | None = None,
    md_sync_mode: str | None = None,
    delete_policy: str | None = None,
    delete_grace_minutes: int | None = None,
    enabled: bool | None = None,
    is_test: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if local_path is not None:
        payload["local_path"] = str(Path(local_path).expanduser())
    if cloud_folder_token is not None:
        payload["cloud_folder_token"] = cloud_folder_token
    if cloud_folder_name is not None:
        payload["cloud_folder_name"] = cloud_folder_name
    if base_path is not None:
        payload["base_path"] = str(Path(base_path).expanduser())
    if sync_mode is not None:
        if sync_mode not in MODE_CHOICES:
            raise ValueError(f"sync_mode 不支持: {sync_mode}")
        payload["sync_mode"] = sync_mode
    if update_mode is not None:
        if update_mode not in TASK_UPDATE_MODE_CHOICES:
            raise ValueError(f"update_mode 不支持: {update_mode}")
        payload["update_mode"] = update_mode
    if md_sync_mode is not None:
        if md_sync_mode not in TASK_MD_MODE_CHOICES:
            raise ValueError(f"md_sync_mode 不支持: {md_sync_mode}")
        payload["md_sync_mode"] = md_sync_mode
    if delete_policy is not None:
        if delete_policy not in DELETE_POLICY_CHOICES:
            raise ValueError(f"delete_policy 不支持: {delete_policy}")
        payload["delete_policy"] = delete_policy
    if delete_grace_minutes is not None:
        payload["delete_grace_minutes"] = int(delete_grace_minutes)
    if enabled is not None:
        payload["enabled"] = bool(enabled)
    if is_test is not None:
        payload["is_test"] = bool(is_test)
    if not payload:
        raise ValueError("至少提供一个待更新字段")
    updated = _must_ok(
        _request_json(
            base_url=base_url,
            method="PATCH",
            path=f"/sync/tasks/{task_id}",
            payload=payload,
        ),
        "更新任务",
    )
    return {"action": "task-update", "task_id": task_id, "task": updated}


def do_delete_task(base_url: str, task_id: str) -> dict[str, Any]:
    data = _must_ok(
        _request_json(base_url=base_url, method="DELETE", path=f"/sync/tasks/{task_id}"),
        "删除任务",
    )
    return {"action": "task-delete", "task_id": task_id, "result": data}


def do_run_task(base_url: str, task_id: str) -> dict[str, Any]:
    if not task_id.strip():
        raise ValueError("task_id 不能为空")
    status = _must_ok(
        _request_json(base_url=base_url, method="POST", path=f"/sync/tasks/{task_id}/run"),
        "执行任务",
    )
    return {"action": "task-run", "task_id": task_id, "status": status}


def do_get_task_status(base_url: str, task_id: str) -> dict[str, Any]:
    status = _must_ok(
        _request_json(base_url=base_url, method="GET", path=f"/sync/tasks/{task_id}/status"),
        "获取任务状态",
    )
    return {"action": "task-status", "task_id": task_id, "status": status}


def do_reset_task_links(base_url: str, task_id: str) -> dict[str, Any]:
    result = _must_ok(
        _request_json(
            base_url=base_url,
            method="POST",
            path=f"/sync/tasks/{task_id}/reset-links",
        ),
        "重置任务映射",
    )
    return {"action": "task-reset-links", "task_id": task_id, "result": result}


def do_get_drive_tree(
    base_url: str,
    folder_token: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    tree = _must_ok(
        _request_json(
            base_url=base_url,
            method="GET",
            path="/drive/tree",
            query={"folder_token": folder_token, "name": name},
        ),
        "获取云端目录树",
    )
    return {"action": "drive-tree", "tree": tree}


def do_update_status(base_url: str) -> dict[str, Any]:
    status = _must_ok(
        _request_json(base_url=base_url, method="GET", path="/system/update/status"),
        "获取更新状态",
    )
    return {"action": "update-status", "status": status}


def do_update_check(base_url: str) -> dict[str, Any]:
    status = _must_ok(
        _request_json(base_url=base_url, method="POST", path="/system/update/check"),
        "检查更新",
    )
    return {"action": "update-check", "status": status}


def do_update_download(base_url: str) -> dict[str, Any]:
    status = _must_ok(
        _request_json(base_url=base_url, method="POST", path="/system/update/download"),
        "下载更新",
    )
    return {"action": "update-download", "status": status}


def do_update_install(base_url: str, download_path: str | None = None) -> dict[str, Any]:
    payload = {"download_path": download_path or None}
    status = _must_ok(
        _request_json(
            base_url=base_url,
            method="POST",
            path="/system/update/install",
            payload=payload,
        ),
        "安装更新",
    )
    return {"action": "update-install", "status": status}


def do_list_conflicts(base_url: str, include_resolved: bool = False) -> dict[str, Any]:
    items = _must_ok(
        _request_json(
            base_url=base_url,
            method="GET",
            path="/conflicts",
            query={"include_resolved": str(include_resolved).lower()},
        ),
        "获取冲突列表",
    )
    return {
        "action": "conflict-list",
        "items": items,
        "total": len(items) if isinstance(items, list) else 0,
    }


def do_resolve_conflict(base_url: str, conflict_id: str, action: str) -> dict[str, Any]:
    if action not in CONFLICT_ACTION_CHOICES:
        raise ValueError(f"conflict action 不支持: {action}")
    item = _must_ok(
        _request_json(
            base_url=base_url,
            method="POST",
            path=f"/conflicts/{conflict_id}/resolve",
            payload={"action": action},
        ),
        "解决冲突",
    )
    return {"action": "conflict-resolve", "conflict_id": conflict_id, "conflict": item}


def do_read_sync_logs(
    base_url: str,
    *,
    limit: int = 50,
    offset: int = 0,
    status: str = "",
    statuses: list[str] | None = None,
    search: str = "",
    task_id: str = "",
    task_ids: list[str] | None = None,
    order: str = "desc",
) -> dict[str, Any]:
    payload = _must_ok(
        _request_json(
            base_url=base_url,
            method="GET",
            path="/sync/logs/sync",
            query={
                "limit": limit,
                "offset": offset,
                "status": status,
                "statuses": statuses or [],
                "search": search,
                "task_id": task_id,
                "task_ids": task_ids or [],
                "order": order,
            },
        ),
        "读取同步日志",
    )
    return {"action": "logs-sync", **payload}


def do_read_file_logs(
    base_url: str,
    *,
    limit: int = 50,
    offset: int = 0,
    level: str = "",
    search: str = "",
    order: str = "desc",
) -> dict[str, Any]:
    payload = _must_ok(
        _request_json(
            base_url=base_url,
            method="GET",
            path="/sync/logs/file",
            query={
                "limit": limit,
                "offset": offset,
                "level": level,
                "search": search,
                "order": order,
            },
        ),
        "读取系统日志",
    )
    return {"action": "logs-file", **payload}


def do_bootstrap_daily(
    *,
    base_url: str,
    name: str,
    local_path: str,
    cloud_folder_token: str,
    sync_mode: str,
    download_value: float,
    download_unit: str,
    download_time: str,
    run_now: bool,
) -> dict[str, Any]:
    check_result = do_check(base_url)
    config_result = do_configure_download(
        base_url=base_url,
        value=download_value,
        unit=download_unit,
        daily_time=download_time,
    )
    task_result = do_create_task(
        base_url=base_url,
        name=name,
        local_path=local_path,
        cloud_folder_token=cloud_folder_token,
        sync_mode=sync_mode,
    )
    run_result: dict[str, Any] | None = None
    if run_now:
        task = task_result.get("task") or {}
        task_id = str(task.get("id", "")).strip()
        if task_id:
            run_result = do_run_task(base_url, task_id)
    return {
        "action": "bootstrap-daily",
        "check": check_result,
        "configure_download": config_result,
        "task": task_result,
        "run_now": run_result,
    }


def do_bootstrap_cache(
    *,
    base_url: str,
    name: str,
    local_path: str,
    cloud_folder_token: str,
    sync_mode: str,
    download_value: float,
    download_unit: str,
    download_time: str,
    run_now: bool,
    enabled: bool = True,
    update_mode: str = "auto",
    md_sync_mode: str | None = None,
    delete_policy: str | None = None,
    delete_grace_minutes: int | None = None,
    cloud_folder_name: str | None = None,
    base_path: str | None = None,
    is_test: bool = False,
) -> dict[str, Any]:
    check_result = do_check(base_url)
    health = check_result.get("health") if isinstance(check_result, dict) else {}
    auth = check_result.get("auth") if isinstance(check_result, dict) else {}
    health_ok = bool(health.get("ok")) if isinstance(health, dict) else False
    auth_data = auth.get("data") if isinstance(auth, dict) and isinstance(auth.get("data"), dict) else {}
    normalized_base_url = _normalize_base_url(base_url)

    if not health_ok:
        return {
            "action": "bootstrap-cache",
            "phase": "blocked_backend_unreachable",
            "completed": False,
            "ready_for_sync": False,
            "summary": "LarkSync 后端当前不可达，首次配置已暂停。",
            "check": check_result,
            "next_step": {
                "type": "start_backend",
                "message": "请先启动 LarkSync（托盘版或 npm run dev），确认 /health 可达后重试。",
                "health_url": _build_url(normalized_base_url, "/health"),
            },
        }

    if not bool(auth_data.get("connected")):
        return {
            "action": "bootstrap-cache",
            "phase": "needs_oauth",
            "completed": False,
            "ready_for_sync": False,
            "summary": "当前尚未完成飞书 OAuth 授权，已暂停首次配置。",
            "check": check_result,
            "next_step": {
                "type": "complete_oauth",
                "message": "请先在浏览器完成一次飞书授权，完成后重新执行 bootstrap-cache。",
                "login_url": _build_url(normalized_base_url, "/auth/login"),
            },
        }

    if auth_data.get("drive_ok") is False:
        return {
            "action": "bootstrap-cache",
            "phase": "needs_drive_permission",
            "completed": False,
            "ready_for_sync": False,
            "summary": "当前账号已连接，但缺少可用的飞书 Drive 权限，首次配置已暂停。",
            "check": check_result,
            "next_step": {
                "type": "grant_drive_permission",
                "message": "请检查飞书应用权限范围与当前账号授权状态，确认 Drive 访问权限可用后重试。",
            },
        }

    config_result = do_configure_download(
        base_url=base_url,
        value=download_value,
        unit=download_unit,
        daily_time=download_time,
    )
    task_result = do_create_task(
        base_url=base_url,
        name=name,
        local_path=local_path,
        cloud_folder_token=cloud_folder_token,
        sync_mode=sync_mode,
        enabled=enabled,
        update_mode=update_mode,
        md_sync_mode=md_sync_mode,
        delete_policy=delete_policy,
        delete_grace_minutes=delete_grace_minutes,
        cloud_folder_name=cloud_folder_name,
        base_path=base_path,
        is_test=is_test,
    )

    run_result: dict[str, Any] | None = None
    task_status: dict[str, Any] | None = None
    task = task_result.get("task") if isinstance(task_result, dict) else {}
    task_id = str(task.get("id", "")).strip() if isinstance(task, dict) else ""
    if run_now and task_id:
        run_result = do_run_task(base_url, task_id)
        task_status = do_get_task_status(base_url, task_id)

    return {
        "action": "bootstrap-cache",
        "phase": "configured",
        "completed": True,
        "ready_for_sync": True,
        "summary": "首次本地缓存同步已配置完成。",
        "check": check_result,
        "configure_download": config_result,
        "task": task_result,
        "run_now": run_result,
        "task_status": task_status,
        "next_step": {
            "type": "use_local_cache",
            "message": "后续可直接读取本地同步目录；如需立即刷新，可再次执行 task-run。",
        },
    }


def _workflow_template_catalog() -> dict[str, dict[str, Any]]:
    common_entrypoints = {
        "cli": "python scripts/larksync_cli.py",
        "helper": (
            "python integrations/openclaw/skills/larksync_feishu_local_cache/"
            "scripts/larksync_skill_helper.py"
        ),
        "wsl_helper": (
            "python integrations/openclaw/skills/larksync_feishu_local_cache/"
            "scripts/larksync_wsl_helper.py"
        ),
    }
    return {
        "daily-cache": {
            "name": "daily-cache",
            "title": "每日缓存初始化",
            "description": "首次接入或新目录接入时，创建 download_only 缓存任务并按需立即跑一次。",
            "entrypoints": common_entrypoints,
            "inputs": [
                {"name": "local_path", "required": True, "description": "本地缓存目录"},
                {"name": "cloud_folder_token", "required": True, "description": "飞书云目录 token"},
                {"name": "download_time", "required": False, "default": "01:00", "type": "string"},
            ],
            "steps": [
                {
                    "id": "bootstrap",
                    "title": "初始化缓存任务",
                    "command": "bootstrap-cache",
                    "notes": "推荐主入口；会自动处理后端不可达、未授权、缺 Drive 权限等前置分支。",
                    "render": [
                        {"flag": "--name", "value": "LarkSync Agent 本地缓存"},
                        {"flag": "--local-path", "input": "local_path"},
                        {"flag": "--cloud-folder-token", "input": "cloud_folder_token"},
                        {"flag": "--cloud-folder-name", "input": "cloud_folder_name", "required": False},
                        {"flag": "--base-path", "input": "base_path", "required": False},
                        {"flag": "--sync-mode", "value": "download_only"},
                        {"flag": "--update-mode", "value": "auto"},
                        {"flag": "--md-sync-mode", "input": "md_sync_mode", "required": False},
                        {"flag": "--delete-policy", "input": "delete_policy", "required": False},
                        {
                            "flag": "--delete-grace-minutes",
                            "input": "delete_grace_minutes",
                            "required": False,
                        },
                        {"flag": "--is-test", "kind": "flag", "input": "is_test", "required": False},
                        {"flag": "--download-value", "value": 1},
                        {"flag": "--download-unit", "value": "days"},
                        {"flag": "--download-time", "input": "download_time"},
                        {"flag": "--run-now", "kind": "flag", "value": True},
                    ],
                },
                {
                    "id": "inspect-task",
                    "title": "读取任务状态",
                    "command": "task-status",
                    "notes": "当 bootstrap-cache 返回 task_id 后，用于确认首次执行状态。",
                    "render": [
                        {
                            "flag": "--task-id",
                            "from_step": "bootstrap",
                            "json_path": "task.task.id",
                        }
                    ],
                },
            ],
            "branching": [
                {
                    "phase": "blocked_backend_unreachable",
                    "next_step_type": "start_backend",
                    "message": "先启动 LarkSync，再重试 bootstrap-cache。",
                },
                {
                    "phase": "needs_oauth",
                    "next_step_type": "complete_oauth",
                    "message": "提示用户完成一次 OAuth，然后重试 bootstrap-cache。",
                },
                {
                    "phase": "needs_drive_permission",
                    "next_step_type": "grant_drive_permission",
                    "message": "提示检查飞书应用权限范围与用户授权。",
                },
                {
                    "phase": "configured",
                    "next_step_type": "use_local_cache",
                    "message": "任务已可用，后续读取优先走本地缓存目录。",
                },
            ],
        },
        "refresh-cache": {
            "name": "refresh-cache",
            "title": "按需刷新本地缓存",
            "description": "对已有任务执行一次手动刷新，并读取状态与最近日志。",
            "entrypoints": common_entrypoints,
            "inputs": [
                {"name": "task_id", "required": True, "description": "已有同步任务 ID"},
                {"name": "log_limit", "required": False, "default": 20, "type": "int"},
            ],
            "steps": [
                {
                    "id": "run-task",
                    "title": "立即触发任务",
                    "command": "task-run",
                    "notes": "用于用户要求“现在同步一次”的场景。",
                    "render": [{"flag": "--task-id", "input": "task_id"}],
                },
                {
                    "id": "task-status",
                    "title": "读取任务运行状态",
                    "command": "task-status",
                    "notes": "确认当前是否在运行、最近结果是否成功。",
                    "render": [{"flag": "--task-id", "input": "task_id"}],
                },
                {
                    "id": "sync-logs",
                    "title": "读取最近同步日志",
                    "command": "logs-sync",
                    "notes": "失败时优先结合日志定位问题。",
                    "render": [
                        {"flag": "--task-id", "input": "task_id"},
                        {"flag": "--limit", "input": "log_limit"},
                    ],
                },
            ],
            "branching": [
                {
                    "phase": "success",
                    "next_step_type": "report_status",
                    "message": "向用户回报任务已触发，并附上最近状态。",
                },
                {
                    "phase": "error",
                    "next_step_type": "inspect_logs",
                    "message": "读取 logs-sync 和 task-status，汇总失败点。",
                },
            ],
        },
        "conflict-audit": {
            "name": "conflict-audit",
            "title": "冲突巡检",
            "description": "面向双向同步场景，定期拉取冲突列表并按需给出处理建议。",
            "entrypoints": common_entrypoints,
            "inputs": [
                {"name": "include_resolved", "required": False, "default": False, "type": "bool"},
            ],
            "steps": [
                {
                    "id": "list-conflicts",
                    "title": "查询冲突列表",
                    "command": "conflict-list",
                    "notes": "日常巡检默认只查未解决冲突。",
                    "render": [
                        {"flag": "--include-resolved", "input": "include_resolved", "kind": "flag"}
                    ],
                },
                {
                    "id": "read-logs",
                    "title": "按任务读取同步日志",
                    "command": "logs-sync",
                    "notes": "对存在冲突的任务补充上下文。",
                    "render": [
                        {
                            "flag": "--task-ids",
                            "from_step": "list-conflicts",
                            "json_path": "items[*].task_id",
                        }
                    ],
                },
                {
                    "id": "resolve-conflict",
                    "title": "按确认结果解决冲突",
                    "command": "conflict-resolve",
                    "notes": "只有在用户明确选择 use_local 或 use_cloud 后才执行。",
                    "render": [
                        {"flag": "--conflict-id", "input": "conflict_id", "required": False},
                        {"flag": "--action", "input": "resolution_action", "required": False},
                    ],
                },
            ],
            "branching": [
                {
                    "phase": "no_conflict",
                    "next_step_type": "report_clean",
                    "message": "当前没有待处理冲突，可结束巡检。",
                },
                {
                    "phase": "has_conflict",
                    "next_step_type": "request_resolution",
                    "message": "先给出冲突摘要和风险，不自动替用户选 use_local/use_cloud。",
                },
            ],
        },
    }


def do_list_workflow_templates() -> dict[str, Any]:
    catalog = _workflow_template_catalog()
    items = [
        {
            "name": item["name"],
            "title": item["title"],
            "description": item["description"],
        }
        for item in catalog.values()
    ]
    return {"action": "workflow-template-list", "items": items, "total": len(items)}


def do_get_workflow_template(template_name: str) -> dict[str, Any]:
    catalog = _workflow_template_catalog()
    try:
        workflow = catalog[template_name]
    except KeyError as exc:
        raise ValueError(f"workflow template 不支持: {template_name}") from exc
    return {
        "action": "workflow-template",
        "template": template_name,
        "workflow": workflow,
    }


def _extract_json_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if current is None:
            return None
        if part.endswith("[*]"):
            key = part[:-3]
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if not isinstance(current, list):
                return None
            continue
        if isinstance(current, list):
            extracted: list[Any] = []
            for item in current:
                if isinstance(item, dict):
                    extracted.append(item.get(part))
                else:
                    extracted.append(None)
            current = extracted
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _quote_command_arg(value: Any) -> str:
    text = str(value)
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'


def _parse_template_set_args(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise ValueError(f"--set 参数格式无效，必须为 key=value: {item}")
        result[key.strip()] = value
    return result


def _coerce_template_value(value: Any, declared_type: str | None) -> Any:
    if declared_type == "bool":
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        raise ValueError(f"布尔模板参数仅支持 true/false: {value}")
    if declared_type == "int":
        return int(value)
    if declared_type == "float":
        return float(value)
    return value


def _materialize_template_inputs(
    workflow: dict[str, Any], values: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    materialized: dict[str, Any] = {}
    missing: list[str] = []
    for item in workflow.get("inputs", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        declared_type = item.get("type")
        if name in values:
            materialized[name] = _coerce_template_value(values[name], declared_type)
            continue
        if "default" in item:
            materialized[name] = _coerce_template_value(item.get("default"), declared_type)
            continue
        if bool(item.get("required")):
            missing.append(name)
    return materialized, missing


def _build_rendered_step(
    *,
    step: dict[str, Any],
    base_command: str,
    inputs: dict[str, Any],
    external_missing_inputs: list[str],
) -> dict[str, Any]:
    argv = [base_command, str(step.get("command", ""))]
    missing_inputs: list[str] = []
    dynamic_inputs: list[dict[str, Any]] = []
    for spec in step.get("render", []):
        if not isinstance(spec, dict):
            continue
        flag = str(spec.get("flag", "")).strip()
        if not flag:
            continue
        kind = str(spec.get("kind", "value"))
        if "from_step" in spec:
            dynamic_inputs.append(
                {
                    "flag": flag,
                    "from_step": spec.get("from_step"),
                    "json_path": spec.get("json_path"),
                }
            )
            continue
        required = bool(spec.get("required", True))
        value = spec.get("value")
        input_name = spec.get("input")
        if input_name is not None:
            if str(input_name) in inputs:
                value = inputs[str(input_name)]
            elif required:
                missing_inputs.append(str(input_name))
                continue
            else:
                value = None
        if kind == "flag":
            if bool(value):
                argv.append(flag)
            continue
        if value is None:
            continue
        argv.extend([flag, str(value)])

    ready = not external_missing_inputs and not missing_inputs and not dynamic_inputs
    command_line = " ".join(
        [_quote_command_arg(part) if index == 0 or index % 2 == 1 and part.startswith("--") is False else part
         for index, part in enumerate(argv)]
    )
    # Rebuild command line with consistent quoting for value positions.
    rendered_parts: list[str] = []
    for index, part in enumerate(argv):
        if index < 2:
            rendered_parts.append(str(part))
            continue
        if part.startswith("--"):
            rendered_parts.append(part)
            continue
        rendered_parts.append(_quote_command_arg(part))
    command_line = " ".join(rendered_parts)
    return {
        "id": step.get("id"),
        "title": step.get("title"),
        "command": step.get("command"),
        "notes": step.get("notes"),
        "ready": ready,
        "argv": argv,
        "command_line": command_line,
        "missing_inputs": missing_inputs,
        "dynamic_inputs": dynamic_inputs,
    }


def do_build_workflow_plan(
    template_name: str,
    *,
    entrypoint: str = "cli",
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if entrypoint not in WORKFLOW_ENTRYPOINT_CHOICES:
        raise ValueError(f"workflow entrypoint 不支持: {entrypoint}")
    template_result = do_get_workflow_template(template_name)
    workflow = template_result["workflow"]
    raw_values = dict(values or {})
    materialized_inputs, missing_inputs = _materialize_template_inputs(workflow, raw_values)
    base_command = str(workflow["entrypoints"][entrypoint])
    steps = [
        _build_rendered_step(
            step=step,
            base_command=base_command,
            inputs=materialized_inputs,
            external_missing_inputs=missing_inputs,
        )
        for step in workflow.get("steps", [])
        if isinstance(step, dict)
    ]
    return {
        "action": "workflow-plan",
        "template": template_name,
        "entrypoint": entrypoint,
        "ready": len(missing_inputs) == 0,
        "missing_inputs": missing_inputs,
        "values": materialized_inputs,
        "plan": {
            "name": workflow.get("name"),
            "title": workflow.get("title"),
            "description": workflow.get("description"),
            "steps": steps,
            "branching": workflow.get("branching", []),
        },
    }


def _resolve_step_runtime_args(
    step: dict[str, Any],
    *,
    inputs: dict[str, Any],
    prior_results: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    values: dict[str, Any] = {}
    missing: list[str] = []
    for spec in step.get("render", []):
        if not isinstance(spec, dict):
            continue
        flag = str(spec.get("flag", "")).strip()
        if not flag:
            continue
        normalized_flag = flag.lstrip("-").replace("-", "_")
        kind = str(spec.get("kind", "value"))
        value = spec.get("value")
        input_name = spec.get("input")
        required = bool(spec.get("required", True))
        if "from_step" in spec:
            source_step = str(spec.get("from_step"))
            source_payload = prior_results.get(source_step)
            if source_payload is None:
                missing.append(f"{source_step}:{spec.get('json_path')}")
                continue
            value = _extract_json_path(source_payload, str(spec.get("json_path", "")))
            if value in (None, "", []):
                missing.append(f"{source_step}:{spec.get('json_path')}")
                continue
        elif input_name is not None:
            if str(input_name) in inputs:
                value = inputs[str(input_name)]
            elif required:
                missing.append(str(input_name))
                continue
            else:
                value = None
        if kind == "flag":
            values[normalized_flag] = bool(value)
            continue
        if value is None:
            continue
        values[normalized_flag] = value
    return values, missing


def _workflow_command_executor(command: str):
    mapping = {
        "bootstrap-cache": do_bootstrap_cache,
        "task-status": lambda **kwargs: do_get_task_status(
            str(kwargs["base_url"]), str(kwargs["task_id"])
        ),
        "task-run": lambda **kwargs: do_run_task(str(kwargs["base_url"]), str(kwargs["task_id"])),
        "logs-sync": lambda **kwargs: do_read_sync_logs(
            str(kwargs["base_url"]),
            limit=int(kwargs.get("limit", 50)),
            offset=int(kwargs.get("offset", 0)),
            status=str(kwargs.get("status", "")),
            statuses=list(kwargs.get("statuses", [])),
            search=str(kwargs.get("search", "")),
            task_id=str(kwargs.get("task_id", "")),
            task_ids=list(kwargs.get("task_ids", [])),
            order=str(kwargs.get("order", "desc")),
        ),
        "conflict-list": lambda **kwargs: do_list_conflicts(
            str(kwargs["base_url"]),
            include_resolved=bool(kwargs.get("include_resolved", False)),
        ),
        "conflict-resolve": lambda **kwargs: do_resolve_conflict(
            str(kwargs["base_url"]),
            str(kwargs["conflict_id"]),
            str(kwargs["action"]),
        ),
    }
    try:
        return mapping[command]
    except KeyError as exc:
        raise ValueError(f"workflow execute 暂不支持命令: {command}") from exc


def _workflow_command_default_kwargs(command: str) -> dict[str, Any]:
    if command == "bootstrap-cache":
        return {
            "name": "LarkSync Agent 本地缓存",
            "cloud_folder_name": None,
            "base_path": None,
            "update_mode": "auto",
            "md_sync_mode": None,
            "delete_policy": None,
            "delete_grace_minutes": None,
            "enabled": True,
            "is_test": False,
        }
    return {}


def _select_workflow_steps(
    steps: list[dict[str, Any]],
    *,
    from_step: str | None = None,
    to_step: str | None = None,
) -> list[dict[str, Any]]:
    indexed: list[tuple[str, dict[str, Any]]] = []
    for item in steps:
        if not isinstance(item, dict):
            continue
        step_id = str(item.get("id", "")).strip()
        if not step_id:
            continue
        indexed.append((step_id, item))
    step_ids = [step_id for step_id, _ in indexed]
    start_index = 0
    end_index = len(indexed) - 1
    if from_step:
        if from_step not in step_ids:
            raise ValueError(f"workflow from_step 不存在: {from_step}")
        start_index = step_ids.index(from_step)
    if to_step:
        if to_step not in step_ids:
            raise ValueError(f"workflow to_step 不存在: {to_step}")
        end_index = step_ids.index(to_step)
    if indexed and start_index > end_index:
        raise ValueError("workflow from_step 不能位于 to_step 之后")
    return [item for _, item in indexed[start_index:end_index + 1]]


def _load_workflow_resume_payload(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        return None
    return data


def _workflow_run_path(run_id: str) -> Path:
    return WORKFLOW_RUNS_DIR / f"{run_id}.json"


def _save_workflow_run_payload(payload: dict[str, Any]) -> Path:
    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        raise ValueError("workflow 结果缺少 run_id，无法保存运行记录")
    WORKFLOW_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = _workflow_run_path(run_id)
    payload["run_file"] = str(path)
    payload["saved_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_workflow_resume_payload_for_run(
    path: Path | None, run_id: str | None = None
) -> dict[str, Any] | None:
    if path is not None:
        return _load_workflow_resume_payload(path)
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    run_path = _workflow_run_path(normalized_run_id)
    return _load_workflow_resume_payload(run_path)


def _workflow_run_summary(path: Path) -> dict[str, Any]:
    payload = _load_workflow_resume_payload(path) or {}
    stat = path.stat()
    run_id = str(payload.get("run_id", path.stem)).strip() or path.stem
    return {
        "run_id": run_id,
        "template": payload.get("template"),
        "entrypoint": payload.get("entrypoint"),
        "completed": payload.get("completed"),
        "dry_run": payload.get("dry_run"),
        "executed_steps": payload.get("executed_steps"),
        "failed_steps": payload.get("failed_steps"),
        "skipped_steps": payload.get("skipped_steps"),
        "saved_at": payload.get("saved_at"),
        "path": str(path),
        "modified_at": dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc).isoformat(),
    }


def do_list_workflow_runs(limit: int = 20) -> dict[str, Any]:
    effective_limit = max(0, int(limit))
    if not WORKFLOW_RUNS_DIR.is_dir():
        return {"action": "workflow-run-list", "count": 0, "items": []}
    files = sorted(
        WORKFLOW_RUNS_DIR.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    items = [_workflow_run_summary(path) for path in files[:effective_limit]]
    return {"action": "workflow-run-list", "count": len(items), "items": items}


def do_show_workflow_run(run_id: str) -> dict[str, Any]:
    normalized_run_id = str(run_id).strip()
    if not normalized_run_id:
        raise ValueError("run_id 不能为空")
    path = _workflow_run_path(normalized_run_id)
    payload = _load_workflow_resume_payload(path)
    if payload is None:
        raise FileNotFoundError(f"未找到 workflow run: {normalized_run_id}")
    payload.setdefault("action", "workflow-run-show")
    payload.setdefault("run_file", str(path))
    return payload


def do_prune_workflow_runs(keep: int = 20) -> dict[str, Any]:
    effective_keep = max(0, int(keep))
    if not WORKFLOW_RUNS_DIR.is_dir():
        return {
            "action": "workflow-run-prune",
            "kept": effective_keep,
            "deleted": [],
            "remaining": 0,
        }
    files = sorted(
        WORKFLOW_RUNS_DIR.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    deleted: list[str] = []
    for path in files[effective_keep:]:
        deleted.append(path.stem)
        path.unlink(missing_ok=True)
    remaining = len(list(WORKFLOW_RUNS_DIR.glob("*.json")))
    return {
        "action": "workflow-run-prune",
        "kept": effective_keep,
        "deleted": deleted,
        "remaining": remaining,
    }


def do_execute_workflow(
    *,
    template_name: str,
    entrypoint: str = "cli",
    values: dict[str, Any] | None = None,
    base_url: str,
    dry_run: bool = False,
    from_step: str | None = None,
    to_step: str | None = None,
    continue_on_error: bool = False,
    output_json_file: Path | None = None,
    run_id: str | None = None,
    resume_from_file: Path | None = None,
    skip_completed: bool = False,
) -> dict[str, Any]:
    plan_result = do_build_workflow_plan(template_name, entrypoint=entrypoint, values=values)
    workflow = do_get_workflow_template(template_name)["workflow"]
    selected_steps = _select_workflow_steps(
        [item for item in workflow.get("steps", []) if isinstance(item, dict)],
        from_step=from_step,
        to_step=to_step,
    )
    effective_run_id = (run_id or "").strip() or uuid.uuid4().hex
    resumed_payload = _load_workflow_resume_payload_for_run(resume_from_file, effective_run_id)
    resumed_results: dict[str, Any] = {}
    resumed_errors: list[dict[str, Any]] = []
    resumed = False
    if resumed_payload is not None:
        resumed_run_id = str(resumed_payload.get("run_id", "")).strip()
        if resumed_run_id and resumed_run_id == effective_run_id:
            resumed = True
            payload_results = resumed_payload.get("results")
            payload_errors = resumed_payload.get("errors")
            if isinstance(payload_results, dict):
                resumed_results = dict(payload_results)
            if isinstance(payload_errors, list):
                resumed_errors = [item for item in payload_errors if isinstance(item, dict)]
    if dry_run:
        result = {
            "action": "workflow-execute",
            "template": template_name,
            "entrypoint": entrypoint,
            "run_id": effective_run_id,
            "run_file": None,
            "resumed": resumed,
            "dry_run": True,
            "completed": False,
            "executed_steps": 0,
            "failed_steps": 0,
            "skipped_steps": 0,
            "missing_inputs": plan_result["missing_inputs"],
            "plan": {**plan_result["plan"], "steps": [step for step in plan_result["plan"]["steps"] if step["id"] in {str(item.get("id", "")) for item in selected_steps}]},
            "results": {},
            "errors": [],
        }
        if output_json_file is not None:
            output_json_file.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return result
    if plan_result["missing_inputs"]:
        raise ValueError(f"workflow 缺少必要输入: {', '.join(plan_result['missing_inputs'])}")

    inputs = dict(plan_result["values"])
    results: dict[str, Any] = dict(resumed_results)
    execution_log: list[dict[str, Any]] = []
    executed_steps = 0
    skipped_steps = 0
    errors: list[dict[str, Any]] = list(resumed_errors)
    selected_ids = {str(item.get("id", "")) for item in selected_steps}
    filtered_plan_steps = [
        step for step in plan_result["plan"]["steps"] if step["id"] in selected_ids
    ]
    for step in selected_steps:
        step_id = str(step.get("id", "")).strip()
        command = str(step.get("command", "")).strip()
        if not step_id or not command:
            continue
        if skip_completed and step_id in results:
            skipped_steps += 1
            continue
        runtime_args, missing = _resolve_step_runtime_args(
            step,
            inputs=inputs,
            prior_results=results,
        )
        defaults = _workflow_command_default_kwargs(command)
        for key, value in defaults.items():
            runtime_args.setdefault(key, value)
        if missing:
            error_payload = {
                "step_id": step_id,
                "command": command,
                "error": f"RuntimeError: workflow step {step_id} 缺少运行时输入: {', '.join(missing)}",
            }
            if not continue_on_error:
                raise RuntimeError(error_payload["error"].split(": ", 1)[1])
            errors.append(error_payload)
            continue
        executor = _workflow_command_executor(command)
        try:
            payload = executor(base_url=base_url, **runtime_args)
        except Exception as exc:  # noqa: BLE001
            error_payload = {
                "step_id": step_id,
                "command": command,
                "error": f"{type(exc).__name__}: {exc}",
            }
            if not continue_on_error:
                raise
            errors.append(error_payload)
            continue
        results[step_id] = payload
        execution_log.append(
            {
                "step_id": step_id,
                "command": command,
                "runtime_args": runtime_args,
            }
        )
        executed_steps += 1
    result = {
        "action": "workflow-execute",
        "template": template_name,
        "entrypoint": entrypoint,
        "run_id": effective_run_id,
        "run_file": None,
        "resumed": resumed,
        "dry_run": False,
        "completed": len(errors) == 0,
        "executed_steps": executed_steps,
        "failed_steps": len(errors),
        "skipped_steps": skipped_steps,
        "missing_inputs": [],
        "plan": {**plan_result["plan"], "steps": filtered_plan_steps},
        "results": results,
        "execution_log": execution_log,
        "errors": errors,
    }
    _save_workflow_run_payload(result)
    if output_json_file is not None:
        output_json_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LarkSync CLI：为 Agent/Skill 提供统一命令入口")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="LarkSync API 地址（默认仅允许 localhost）",
    )
    parser.add_argument(
        "--allow-remote-base-url",
        action="store_true",
        help="显式允许非 localhost 地址（存在令牌泄露风险，仅在可信网络使用）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="检查健康、授权、配置与任务概况")
    sub.add_parser("auth-status", help="读取授权状态")
    sub.add_parser("config-get", help="读取当前配置")
    sub.add_parser("workflow-template-list", help="列出可供 Agent 使用的标准工作流模板")
    template = sub.add_parser("workflow-template", help="读取单个标准工作流模板")
    template.add_argument("--template", choices=WORKFLOW_TEMPLATE_CHOICES, required=True)
    plan = sub.add_parser("workflow-plan", help="将工作流模板实例化为可执行命令计划")
    plan.add_argument("--template", choices=WORKFLOW_TEMPLATE_CHOICES, required=True)
    plan.add_argument("--entrypoint", choices=WORKFLOW_ENTRYPOINT_CHOICES, default="cli")
    plan.add_argument("--set", action="append", default=[], help="模板参数，格式 key=value，可重复")
    run_list = sub.add_parser("workflow-run-list", help="列出标准工作流执行记录")
    run_list.add_argument("--limit", type=int, default=20)
    run_show = sub.add_parser("workflow-run-show", help="读取单个工作流执行记录")
    run_show.add_argument("--run-id", required=True)
    run_prune = sub.add_parser("workflow-run-prune", help="清理过旧工作流执行记录")
    run_prune.add_argument("--keep", type=int, default=20)
    execute = sub.add_parser("workflow-execute", help="按模板与参数顺序执行工作流")
    execute.add_argument("--template", choices=WORKFLOW_TEMPLATE_CHOICES, required=True)
    execute.add_argument("--entrypoint", choices=WORKFLOW_ENTRYPOINT_CHOICES, default="cli")
    execute.add_argument("--set", action="append", default=[], help="模板参数，格式 key=value，可重复")
    execute.add_argument("--dry-run", action="store_true", help="仅生成计划，不实际执行")
    execute.add_argument("--from-step", help="仅从指定 step id 开始执行")
    execute.add_argument("--to-step", help="仅执行到指定 step id 为止")
    execute.add_argument("--continue-on-error", action="store_true", help="单步失败后继续执行后续步骤并汇总错误")
    execute.add_argument("--output-json-file", help="将执行结果写入指定 JSON 文件")
    execute.add_argument("--run-id", help="显式指定工作流运行 ID；与 resume/skip 配合使用")
    execute.add_argument("--resume-from-file", help="从已有 workflow-execute JSON 结果恢复执行状态")
    execute.add_argument("--skip-completed", action="store_true", help="恢复执行时跳过结果中已成功的步骤")

    cfg = sub.add_parser("config-set", help="更新配置")
    cfg.add_argument("--download-value", type=float)
    cfg.add_argument("--download-unit", choices=UNIT_CHOICES)
    cfg.add_argument("--download-time")
    cfg.add_argument("--upload-value", type=float)
    cfg.add_argument("--upload-unit", choices=UNIT_CHOICES)
    cfg.add_argument("--upload-time")
    cfg.add_argument("--auto-update-enabled", choices=("true", "false"))
    cfg.add_argument("--update-check-interval-hours", type=int)
    cfg.add_argument("--allow-dev-to-stable", choices=("true", "false"))
    cfg.add_argument("--device-display-name")
    cfg.add_argument("--delete-policy", choices=DELETE_POLICY_CHOICES)
    cfg.add_argument("--delete-grace-minutes", type=int)
    cfg.add_argument("--sync-mode", choices=MODE_CHOICES)

    down = sub.add_parser("configure-download", help="配置低频下载策略")
    down.add_argument("--download-value", type=float, default=1.0)
    down.add_argument("--download-unit", choices=UNIT_CHOICES, default="days")
    down.add_argument("--download-time", default="01:00")

    sub.add_parser("task-list", help="列出同步任务")
    sub.add_parser("task-status-list", help="列出所有任务状态")

    create = sub.add_parser("task-create", help="创建同步任务")
    create.add_argument("--name", default="LarkSync CLI 任务")
    create.add_argument("--local-path", required=True)
    create.add_argument("--cloud-folder-token", required=True)
    create.add_argument("--cloud-folder-name")
    create.add_argument("--base-path")
    create.add_argument("--sync-mode", choices=MODE_CHOICES, default="download_only")
    create.add_argument("--update-mode", choices=TASK_UPDATE_MODE_CHOICES, default="auto")
    create.add_argument("--md-sync-mode", choices=TASK_MD_MODE_CHOICES)
    create.add_argument("--delete-policy", choices=DELETE_POLICY_CHOICES)
    create.add_argument("--delete-grace-minutes", type=int)
    create.add_argument("--disabled", action="store_true")
    create.add_argument("--is-test", action="store_true")

    update = sub.add_parser("task-update", help="更新同步任务")
    update.add_argument("--task-id", required=True)
    update.add_argument("--name")
    update.add_argument("--local-path")
    update.add_argument("--cloud-folder-token")
    update.add_argument("--cloud-folder-name")
    update.add_argument("--base-path")
    update.add_argument("--sync-mode", choices=MODE_CHOICES)
    update.add_argument("--update-mode", choices=TASK_UPDATE_MODE_CHOICES)
    update.add_argument("--md-sync-mode", choices=TASK_MD_MODE_CHOICES)
    update.add_argument("--delete-policy", choices=DELETE_POLICY_CHOICES)
    update.add_argument("--delete-grace-minutes", type=int)
    update.add_argument("--enabled", action="store_const", const=True, default=None)
    update.add_argument("--disabled", dest="enabled", action="store_const", const=False)
    update.add_argument("--is-test", action="store_const", const=True, default=None)
    update.add_argument("--not-test", dest="is_test", action="store_const", const=False)

    delete = sub.add_parser("task-delete", help="删除同步任务")
    delete.add_argument("--task-id", required=True)

    run = sub.add_parser("task-run", help="立即执行任务")
    run.add_argument("--task-id", required=True)

    status = sub.add_parser("task-status", help="读取单个任务状态")
    status.add_argument("--task-id", required=True)

    reset = sub.add_parser("task-reset-links", help="清空任务映射")
    reset.add_argument("--task-id", required=True)

    drive = sub.add_parser("drive-tree", help="读取飞书目录树")
    drive.add_argument("--folder-token")
    drive.add_argument("--name")

    sub.add_parser("update-status", help="读取更新状态")
    sub.add_parser("update-check", help="检查更新")
    sub.add_parser("update-download", help="下载更新包")
    install = sub.add_parser("update-install", help="请求安装更新包")
    install.add_argument("--download-path")

    conflicts = sub.add_parser("conflict-list", help="列出冲突")
    conflicts.add_argument("--include-resolved", action="store_true")

    resolve = sub.add_parser("conflict-resolve", help="解决冲突")
    resolve.add_argument("--conflict-id", required=True)
    resolve.add_argument("--action", choices=CONFLICT_ACTION_CHOICES, required=True)

    sync_logs = sub.add_parser("logs-sync", help="读取同步日志")
    sync_logs.add_argument("--limit", type=int, default=50)
    sync_logs.add_argument("--offset", type=int, default=0)
    sync_logs.add_argument("--status", default="")
    sync_logs.add_argument("--statuses", action="append", default=[])
    sync_logs.add_argument("--search", default="")
    sync_logs.add_argument("--task-id", default="")
    sync_logs.add_argument("--task-ids", action="append", default=[])
    sync_logs.add_argument("--order", choices=LOG_ORDER_CHOICES, default="desc")

    file_logs = sub.add_parser("logs-file", help="读取系统日志")
    file_logs.add_argument("--limit", type=int, default=50)
    file_logs.add_argument("--offset", type=int, default=0)
    file_logs.add_argument("--level", default="")
    file_logs.add_argument("--search", default="")
    file_logs.add_argument("--order", choices=LOG_ORDER_CHOICES, default="desc")

    bootstrap = sub.add_parser("bootstrap-daily", help="一键配置每日低频同步并创建任务")
    bootstrap.add_argument("--name", default="LarkSync CLI 每日同步")
    bootstrap.add_argument("--local-path", required=True)
    bootstrap.add_argument("--cloud-folder-token", required=True)
    bootstrap.add_argument("--sync-mode", choices=MODE_CHOICES, default="download_only")
    bootstrap.add_argument("--download-value", type=float, default=1.0)
    bootstrap.add_argument("--download-unit", choices=UNIT_CHOICES, default="days")
    bootstrap.add_argument("--download-time", default="01:00")
    bootstrap.add_argument("--run-now", action="store_true")

    cache = sub.add_parser(
        "bootstrap-cache",
        help="面向 Agent 的首次缓存初始化：检查状态、等待 OAuth、配置策略并建任务",
    )
    cache.add_argument("--name", default="LarkSync Agent 本地缓存")
    cache.add_argument("--local-path", required=True)
    cache.add_argument("--cloud-folder-token", required=True)
    cache.add_argument("--cloud-folder-name")
    cache.add_argument("--base-path")
    cache.add_argument("--sync-mode", choices=MODE_CHOICES, default="download_only")
    cache.add_argument("--update-mode", choices=TASK_UPDATE_MODE_CHOICES, default="auto")
    cache.add_argument("--md-sync-mode", choices=TASK_MD_MODE_CHOICES)
    cache.add_argument("--delete-policy", choices=DELETE_POLICY_CHOICES)
    cache.add_argument("--delete-grace-minutes", type=int)
    cache.add_argument("--disabled", action="store_true")
    cache.add_argument("--is-test", action="store_true")
    cache.add_argument("--download-value", type=float, default=1.0)
    cache.add_argument("--download-unit", choices=UNIT_CHOICES, default="days")
    cache.add_argument("--download-time", default="01:00")
    cache.add_argument("--run-now", action="store_true")

    return parser


def _bool_arg(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError(f"布尔值仅支持 true/false: {value}")


def _build_config_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if args.download_value is not None:
        payload["download_interval_value"] = float(args.download_value)
    if args.download_unit is not None:
        payload["download_interval_unit"] = str(args.download_unit)
    if args.download_time is not None:
        if not _validate_hhmm(str(args.download_time)):
            raise ValueError("download_time 格式无效，必须为 HH:MM")
        payload["download_daily_time"] = str(args.download_time)
    if args.upload_value is not None:
        payload["upload_interval_value"] = float(args.upload_value)
    if args.upload_unit is not None:
        payload["upload_interval_unit"] = str(args.upload_unit)
    if args.upload_time is not None:
        if not _validate_hhmm(str(args.upload_time)):
            raise ValueError("upload_time 格式无效，必须为 HH:MM")
        payload["upload_daily_time"] = str(args.upload_time)
    auto_update_enabled = _bool_arg(args.auto_update_enabled)
    if auto_update_enabled is not None:
        payload["auto_update_enabled"] = auto_update_enabled
    allow_dev_to_stable = _bool_arg(args.allow_dev_to_stable)
    if allow_dev_to_stable is not None:
        payload["allow_dev_to_stable"] = allow_dev_to_stable
    if args.update_check_interval_hours is not None:
        payload["update_check_interval_hours"] = int(args.update_check_interval_hours)
    if args.device_display_name is not None:
        payload["device_display_name"] = str(args.device_display_name)
    if args.delete_policy is not None:
        payload["delete_policy"] = str(args.delete_policy)
    if args.delete_grace_minutes is not None:
        payload["delete_grace_minutes"] = int(args.delete_grace_minutes)
    if args.sync_mode is not None:
        payload["sync_mode"] = str(args.sync_mode)
    if not payload:
        raise ValueError("至少提供一个配置项")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        base_url = validate_base_url(
            args.base_url,
            allow_remote=bool(getattr(args, "allow_remote_base_url", False)),
        )
        if args.command == "check":
            result = do_check(base_url)
        elif args.command == "auth-status":
            result = do_auth_status(base_url)
        elif args.command == "config-get":
            result = do_get_config(base_url)
        elif args.command == "workflow-template-list":
            result = do_list_workflow_templates()
        elif args.command == "workflow-template":
            result = do_get_workflow_template(str(args.template))
        elif args.command == "workflow-plan":
            result = do_build_workflow_plan(
                str(args.template),
                entrypoint=str(args.entrypoint),
                values=_parse_template_set_args(list(args.set or [])),
            )
        elif args.command == "workflow-run-list":
            result = do_list_workflow_runs(limit=int(args.limit))
        elif args.command == "workflow-run-show":
            result = do_show_workflow_run(str(args.run_id))
        elif args.command == "workflow-run-prune":
            result = do_prune_workflow_runs(keep=int(args.keep))
        elif args.command == "workflow-execute":
            result = do_execute_workflow(
                template_name=str(args.template),
                entrypoint=str(args.entrypoint),
                values=_parse_template_set_args(list(args.set or [])),
                base_url=base_url,
                dry_run=bool(args.dry_run),
                from_step=args.from_step,
                to_step=args.to_step,
                continue_on_error=bool(args.continue_on_error),
                output_json_file=Path(args.output_json_file) if args.output_json_file else None,
                run_id=args.run_id,
                resume_from_file=Path(args.resume_from_file) if args.resume_from_file else None,
                skip_completed=bool(args.skip_completed),
            )
        elif args.command == "config-set":
            result = do_set_config(base_url, _build_config_payload(args))
        elif args.command == "configure-download":
            result = do_configure_download(
                base_url=base_url,
                value=float(args.download_value),
                unit=str(args.download_unit),
                daily_time=str(args.download_time),
            )
        elif args.command == "task-list":
            result = do_list_tasks(base_url)
        elif args.command == "task-status-list":
            result = do_list_task_status(base_url)
        elif args.command == "task-create":
            result = do_create_task(
                base_url=base_url,
                name=str(args.name),
                local_path=str(args.local_path),
                cloud_folder_token=str(args.cloud_folder_token),
                cloud_folder_name=args.cloud_folder_name,
                base_path=args.base_path,
                sync_mode=str(args.sync_mode),
                update_mode=str(args.update_mode),
                md_sync_mode=args.md_sync_mode,
                delete_policy=args.delete_policy,
                delete_grace_minutes=args.delete_grace_minutes,
                enabled=not bool(args.disabled),
                is_test=bool(args.is_test),
            )
        elif args.command == "task-update":
            result = do_update_task(
                base_url=base_url,
                task_id=str(args.task_id),
                name=args.name,
                local_path=args.local_path,
                cloud_folder_token=args.cloud_folder_token,
                cloud_folder_name=args.cloud_folder_name,
                base_path=args.base_path,
                sync_mode=args.sync_mode,
                update_mode=args.update_mode,
                md_sync_mode=args.md_sync_mode,
                delete_policy=args.delete_policy,
                delete_grace_minutes=args.delete_grace_minutes,
                enabled=args.enabled,
                is_test=args.is_test,
            )
        elif args.command == "task-delete":
            result = do_delete_task(base_url, str(args.task_id))
        elif args.command == "task-run":
            result = do_run_task(base_url, str(args.task_id))
        elif args.command == "task-status":
            result = do_get_task_status(base_url, str(args.task_id))
        elif args.command == "task-reset-links":
            result = do_reset_task_links(base_url, str(args.task_id))
        elif args.command == "drive-tree":
            result = do_get_drive_tree(base_url, folder_token=args.folder_token, name=args.name)
        elif args.command == "update-status":
            result = do_update_status(base_url)
        elif args.command == "update-check":
            result = do_update_check(base_url)
        elif args.command == "update-download":
            result = do_update_download(base_url)
        elif args.command == "update-install":
            result = do_update_install(base_url, args.download_path)
        elif args.command == "conflict-list":
            result = do_list_conflicts(base_url, include_resolved=bool(args.include_resolved))
        elif args.command == "conflict-resolve":
            result = do_resolve_conflict(
                base_url,
                conflict_id=str(args.conflict_id),
                action=str(args.action),
            )
        elif args.command == "logs-sync":
            result = do_read_sync_logs(
                base_url,
                limit=int(args.limit),
                offset=int(args.offset),
                status=str(args.status),
                statuses=list(args.statuses or []),
                search=str(args.search),
                task_id=str(args.task_id),
                task_ids=list(args.task_ids or []),
                order=str(args.order),
            )
        elif args.command == "logs-file":
            result = do_read_file_logs(
                base_url,
                limit=int(args.limit),
                offset=int(args.offset),
                level=str(args.level),
                search=str(args.search),
                order=str(args.order),
            )
        elif args.command == "bootstrap-daily":
            result = do_bootstrap_daily(
                base_url=base_url,
                name=str(args.name),
                local_path=str(args.local_path),
                cloud_folder_token=str(args.cloud_folder_token),
                sync_mode=str(args.sync_mode),
                download_value=float(args.download_value),
                download_unit=str(args.download_unit),
                download_time=str(args.download_time),
                run_now=bool(args.run_now),
            )
        elif args.command == "bootstrap-cache":
            result = do_bootstrap_cache(
                base_url=base_url,
                name=str(args.name),
                local_path=str(args.local_path),
                cloud_folder_token=str(args.cloud_folder_token),
                cloud_folder_name=args.cloud_folder_name,
                base_path=args.base_path,
                sync_mode=str(args.sync_mode),
                update_mode=str(args.update_mode),
                md_sync_mode=args.md_sync_mode,
                delete_policy=args.delete_policy,
                delete_grace_minutes=args.delete_grace_minutes,
                enabled=not bool(args.disabled),
                is_test=bool(args.is_test),
                download_value=float(args.download_value),
                download_unit=str(args.download_unit),
                download_time=str(args.download_time),
                run_now=bool(args.run_now),
            )
        else:
            parser.error(f"未知命令: {args.command}")
            return 2
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
