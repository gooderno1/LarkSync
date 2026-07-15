"""
LarkSync 打包入口（受版本控制）。

用于替代未纳入 Git 的根目录 `LarkSync.pyw`，避免 CI 构建时入口脚本缺失。
"""

from __future__ import annotations

import os
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
    from apps.tray.config import BACKEND_PORT
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
            and _local_port_active(8000)
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


def entrypoint(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--backend" in args:
        _run_backend()
        return 0

    from apps.tray.tray_app import main

    main()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(entrypoint())
    except Exception as exc:
        _write_bootstrap_error(exc)
        raise
