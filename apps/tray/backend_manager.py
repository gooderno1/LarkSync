"""
后端进程管理器 — 启动/停止/健康检查/自动重启
"""

from __future__ import annotations

import subprocess
import sys
import time
import threading
from pathlib import Path

import urllib.request
import urllib.error

from apps.tray.config import (
    BACKEND_DIR,
    BACKEND_HOST,
    BACKEND_PORT,
    HEALTH_CHECK_URL,
    HEALTH_CHECK_TIMEOUT,
    STARTUP_WAIT_TIMEOUT,
    STARTUP_POLL_INTERVAL,
    MAX_RESTART_ATTEMPTS,
    RESTART_COOLDOWN,
    PYTHON_EXE,
)

from loguru import logger


class BackendManager:
    """管理 FastAPI 后端进程的生命周期。"""

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._restart_count: int = 0
        self._lock = threading.Lock()
        self._should_run = False

    @property
    def is_running(self) -> bool:
        """检查后端进程是否存活。"""
        if self._process is None:
            return False
        return self._process.poll() is None

    def health_check(self) -> bool:
        """通过 /health 端点检查后端是否就绪。"""
        try:
            req = urllib.request.Request(HEALTH_CHECK_URL, method="GET")
            with urllib.request.urlopen(req, timeout=HEALTH_CHECK_TIMEOUT) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start(self, wait: bool = True) -> bool:
        """
        启动后端进程。
        wait=True 时等待 /health 就绪后返回。
        返回是否成功。
        """
        with self._lock:
            if self.is_running:
                logger.info("后端已在运行 (PID {})", self._process.pid)
                return True

            self._should_run = True
            logger.info("启动后端服务: {}:{}", BACKEND_HOST, BACKEND_PORT)

            cmd = [
                PYTHON_EXE, "-m", "uvicorn",
                "src.main:app",
                "--host", BACKEND_HOST,
                "--port", str(BACKEND_PORT),
                "--log-level", "warning",
            ]

            # Windows: 使用 CREATE_NO_WINDOW 避免弹出终端
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            try:
                self._process = subprocess.Popen(
                    cmd,
                    cwd=str(BACKEND_DIR),
                    creationflags=creationflags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("后端进程已启动 (PID {})", self._process.pid)
            except Exception as exc:
                logger.error("启动后端失败: {}", exc)
                return False

        if wait:
            return self._wait_for_ready()
        return True

    def stop(self) -> None:
        """优雅停止后端进程。"""
        with self._lock:
            self._should_run = False
            if not self.is_running:
                logger.info("后端未在运行")
                return

            pid = self._process.pid
            logger.info("停止后端服务 (PID {})", pid)

            try:
                self._process.terminate()
                self._process.wait(timeout=5)
                logger.info("后端已正常退出")
            except subprocess.TimeoutExpired:
                logger.warning("后端未响应 SIGTERM，强制终止")
                self._process.kill()
                self._process.wait(timeout=3)
            except Exception as exc:
                logger.error("停止后端异常: {}", exc)
            finally:
                self._process = None
                self._restart_count = 0

    def restart(self) -> bool:
        """重启后端进程。"""
        logger.info("重启后端服务...")
        self.stop()
        time.sleep(1)
        self._should_run = True
        return self.start(wait=True)

    def maybe_auto_restart(self) -> bool:
        """
        检查后端是否异常退出，如果是则自动重启。
        由状态轮询线程调用。
        返回是否需要通知用户。
        """
        if not self._should_run:
            return False

        if self.is_running:
            self._restart_count = 0
            return False

        # 进程退出了
        if self._restart_count >= MAX_RESTART_ATTEMPTS:
            logger.error("后端已连续异常退出 {} 次，停止自动重启", self._restart_count)
            self._should_run = False
            return True  # 需要通知

        self._restart_count += 1
        logger.warning(
            "后端异常退出，第 {}/{} 次自动重启...",
            self._restart_count,
            MAX_RESTART_ATTEMPTS,
        )
        time.sleep(RESTART_COOLDOWN)
        success = self.start(wait=True)
        if not success:
            return True  # 重启失败，需要通知
        return False

    def _wait_for_ready(self) -> bool:
        """等待后端 /health 就绪。"""
        deadline = time.time() + STARTUP_WAIT_TIMEOUT
        while time.time() < deadline:
            if not self.is_running:
                logger.error("后端进程已退出")
                return False
            if self.health_check():
                logger.info("后端就绪 ✓")
                return True
            time.sleep(STARTUP_POLL_INTERVAL)
        logger.error("后端启动超时 ({}s)", STARTUP_WAIT_TIMEOUT)
        return False
