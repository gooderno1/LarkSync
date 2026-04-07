from __future__ import annotations

import argparse
import ipaddress
import json
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
