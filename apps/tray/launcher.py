"""
LarkSync 打包入口（受版本控制）。

用于替代未纳入 Git 的根目录 `LarkSync.pyw`，避免 CI 构建时入口脚本缺失。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run_backend() -> None:
    """在打包环境中直接启动后端（替代 `python -m uvicorn`）。"""
    from apps.tray.config import BACKEND_DIR, BACKEND_HOST, BACKEND_PORT

    os.chdir(str(BACKEND_DIR))
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from src.main import app
    import uvicorn

    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT, log_level="warning")


def entrypoint(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--backend" in args:
        _run_backend()
        return 0

    from apps.tray.tray_app import main

    main()
    return 0


if __name__ == "__main__":
    raise SystemExit(entrypoint())
