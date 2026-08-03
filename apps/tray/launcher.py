"""
LarkSync 打包入口（受版本控制）。

用于替代未纳入 Git 的根目录 `LarkSync.pyw`，避免 CI 构建时入口脚本缺失。
"""

from __future__ import annotations

import multiprocessing
import os
import secrets
import socket
import sys
import time
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _bootstrap_data_dir() -> Path:
    env_dir = (os.getenv("LARKSYNC_DATA_DIR") or "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    if sys.platform == "win32":
        return Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming") / "LarkSync"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LarkSync"
    return Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "LarkSync"


def _write_bootstrap_error(exc: BaseException) -> Path:
    """在日志系统尚未初始化时保留打包入口异常。"""
    path = _bootstrap_data_dir() / "logs" / "bootstrap-error.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp}] {detail}\n")
    return path


def _local_port_active(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def _validate_backend_runtime() -> None:
    from apps.tray.config import BACKEND_PORT, RESERVED_PRODUCTION_BACKEND_PORTS
    from src.core.config import ConfigManager, RuntimeProfile
    from src.core.paths import data_dir
    from src.core.runtime_safety import validate_runtime_environment

    config = ConfigManager.get().config
    raw_lock_port = (os.getenv("LARKSYNC_LOCK_PORT") or "48901").strip()
    try:
        lock_port = int(raw_lock_port)
    except ValueError:
        lock_port = 48901
    issues = validate_runtime_environment(
        config,
        backend_port=BACKEND_PORT,
        lock_port=lock_port,
        runtime_data_dir=data_dir(),
        explicit_data_dir=bool((os.getenv("LARKSYNC_DATA_DIR") or "").strip()),
        production_backend_running=(
            config.runtime_profile is not RuntimeProfile.production
            and any(_local_port_active(port) for port in RESERVED_PRODUCTION_BACKEND_PORTS)
        ),
    )
    if issues:
        raise RuntimeError("运行配置安全检查失败：" + "；".join(issues))


def _run_backend() -> None:
    """在打包环境中直接启动后端（替代 `python -m uvicorn`）。"""
    from apps.tray.config import BACKEND_DIR, BACKEND_HOST, BACKEND_PORT

    _validate_backend_runtime()

    os.chdir(str(BACKEND_DIR))
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from src.main import app
    import uvicorn

    # Windows GUI 子系统中 sys.stdout/sys.stderr 为 None；Uvicorn 默认日志格式器
    # 会调用 isatty() 并在监听端口前退出。应用自身使用 Loguru 记录运行日志。
    uvicorn.run(
        app,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level="warning",
        log_config=None,
        access_log=False,
    )


def _run_keychain_smoke(result_path: Path) -> int:
    """验证安装版能通过系统 Keychain 完成凭证写入、读取和清理。"""
    import json
    import keyring

    account = f"ci-{os.getpid()}-{secrets.token_hex(4)}"
    value = secrets.token_urlsafe(32)
    payload: dict[str, object]
    try:
        keyring.set_password("com.larksync.app.smoke", account, value)
        payload = {"ok": keyring.get_password("com.larksync.app.smoke", account) == value}
    except Exception as exc:
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        try:
            keyring.delete_password("com.larksync.app.smoke", account)
        except Exception:
            pass
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0 if payload.get("ok") else 1


def entrypoint(argv: list[str] | None = None) -> int:
    # PyInstaller replaces this function on every supported platform. It must
    # run before our own argument routing so Cocoa/WKWebView resource tracker
    # children (``-B -S -I -c ...``) do not fall through to the tray parser.
    multiprocessing.freeze_support()
    args = list(sys.argv[1:] if argv is None else argv)
    if "--keychain-smoke-result" in args:
        index = args.index("--keychain-smoke-result")
        try:
            result_path = Path(args[index + 1]).expanduser().resolve()
        except IndexError as exc:
            raise ValueError("--keychain-smoke-result 缺少输出路径") from exc
        return _run_keychain_smoke(result_path)
    if "--backend" in args:
        _run_backend()
        return 0
    if "--desktop-window" in args:
        from apps.tray.desktop_window import main as desktop_window_main

        return desktop_window_main([arg for arg in args if arg != "--desktop-window"])

    from apps.tray.tray_app import main

    main()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(entrypoint())
    except Exception as exc:
        _write_bootstrap_error(exc)
        raise
