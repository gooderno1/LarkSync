"""
后端进程管理器 — 启动/停止/健康检查/自动重启

核心逻辑：
  1. 启动前检查端口是否已被占用
  2. 如果端口上已有可响应的 /health 服务 → 视为"外部后端"，复用之
  3. 否则启动新的 uvicorn 子进程
  4. 定期检查进程状态，异常退出时自动重启
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

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
    PROJECT_ROOT,
)

from loguru import logger


def _sanitize_pythonpath(raw_pythonpath: str | None) -> tuple[str | None, bool]:
    """移除 PYTHONPATH 中与当前解释器版本不匹配的 site-packages。"""
    if not raw_pythonpath:
        return raw_pythonpath, False

    current_tag = f"{sys.version_info.major}{sys.version_info.minor}"
    kept_entries: list[str] = []
    changed = False

    for entry in raw_pythonpath.split(os.pathsep):
        cleaned = entry.strip()
        if not cleaned:
            continue

        normalized = cleaned.replace("\\", "/").lower()
        version_tags = re.findall(r"python(\d{2,3})", normalized)
        has_mismatch = bool(version_tags) and any(tag != current_tag for tag in version_tags)

        # 仅过滤明显的版本不匹配 site-packages，避免误伤业务路径。
        if has_mismatch and "site-packages" in normalized:
            changed = True
            continue

        kept_entries.append(cleaned)

    if not kept_entries:
        return None, changed or bool(raw_pythonpath.strip())

    sanitized = os.pathsep.join(kept_entries)
    return sanitized, changed or sanitized != raw_pythonpath


class BackendManager:
    """管理 FastAPI 后端进程的生命周期。"""

    def __init__(self, dev_mode: bool = False) -> None:
        self._process: subprocess.Popen | None = None
        self._restart_count: int = 0
        self._lock = threading.Lock()
        self._should_run = False
        self._external_backend = False  # 是否复用外部已有后端
        self._stderr_path: Path | None = None
        self._dev_mode = dev_mode  # 开发模式：启用 --reload

    @property
    def is_running(self) -> bool:
        """检查后端是否可用（自启进程或外部后端）。"""
        if self._external_backend:
            return self.health_check()
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

    def _request_shutdown(self) -> bool:
        """向后端发送优雅关闭请求。"""
        shutdown_url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/system/shutdown"
        try:
            req = urllib.request.Request(shutdown_url, method="POST")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start(self, wait: bool = True) -> bool:
        """
        启动后端进程。

        启动前先检测端口：
        - 端口已有可用后端 → 复用（不启动新进程）
        - 端口被占用但非后端 → 报错
        - 端口空闲 → 启动新 uvicorn

        wait=True 时等待 /health 就绪后返回。
        返回是否成功。
        """
        with self._lock:
            # 已有管理的进程在运行
            if self._process and self._process.poll() is None:
                logger.info("后端已在运行 (PID {})", self._process.pid)
                return True

            self._should_run = True

            # ---- 检测端口占用 ----
            if self._is_port_in_use():
                if self.health_check():
                    logger.info("检测到已有后端服务在 {}:{} 运行，将复用该服务",
                                BACKEND_HOST, BACKEND_PORT)
                    self._external_backend = True
                    return True
                else:
                    logger.error(
                        "端口 {} 已被其他程序占用且非 LarkSync 后端，请先释放端口",
                        BACKEND_PORT,
                    )
                    return False

            # ---- 启动新进程 ----
            self._external_backend = False
            logger.info("启动后端服务: {}:{}", BACKEND_HOST, BACKEND_PORT)

            # 日志文件目录
            log_dir = PROJECT_ROOT / "data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            self._stderr_path = log_dir / "backend-stderr.log"

            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--backend"]
            else:
                cmd = [
                    PYTHON_EXE, "-m", "uvicorn",
                    "src.main:app",
                    "--host", BACKEND_HOST,
                    "--port", str(BACKEND_PORT),
                    "--log-level", "warning",
                ]

                if self._dev_mode:
                    cmd.append("--reload")
                    logger.info("开发模式：后端启用 --reload 热重载")

            # Windows: 使用 CREATE_NO_WINDOW 避免弹出终端
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            try:
                env = self._build_backend_env()
                stderr_file = open(str(self._stderr_path), "a", encoding="utf-8")
                self._process = subprocess.Popen(
                    cmd,
                    cwd=str(BACKEND_DIR),
                    creationflags=creationflags,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_file,
                    env=env,
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

            if self._external_backend:
                logger.info("外部后端，跳过停止")
                self._external_backend = False
                return

            if not self._process or self._process.poll() is not None:
                logger.info("后端未在运行")
                self._process = None
                return

            pid = self._process.pid
            logger.info("停止后端服务 (PID {})", pid)

            graceful_sent = False
            if self.health_check():
                graceful_sent = self._request_shutdown()
                if graceful_sent:
                    logger.info("已发送后端优雅关闭请求")

            if graceful_sent:
                try:
                    self._process.wait(timeout=8)
                    logger.info("后端已正常退出")
                    self._process = None
                    self._restart_count = 0
                    return
                except subprocess.TimeoutExpired:
                    logger.warning("后端优雅关闭超时，执行强制终止")

            try:
                if sys.platform == "win32":
                    # Windows: 使用 taskkill /T /F 杀掉进程树
                    # 这能同时杀掉 uvicorn reloader 父进程和它 fork 的子进程
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True,
                        timeout=5,
                    )
                    try:
                        self._process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
                else:
                    self._process.terminate()
                    self._process.wait(timeout=5)
                logger.info("后端已正常退出")
            except subprocess.TimeoutExpired:
                logger.warning("后端未响应 SIGTERM，强制终止")
                self._process.kill()
                try:
                    self._process.wait(timeout=3)
                except Exception:
                    pass
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

        # 外部后端：只做健康检查
        if self._external_backend:
            if self.health_check():
                return False
            logger.warning("外部后端不可达，尝试自行启动...")
            self._external_backend = False
            # 继续走下面的重启逻辑

        if self._process and self._process.poll() is None:
            self._restart_count = 0
            return False

        # 进程退出了
        if self._restart_count >= MAX_RESTART_ATTEMPTS:
            logger.error("后端已连续异常退出 {} 次，停止自动重启", self._restart_count)
            self._should_run = False
            return True  # 需要通知

        self._restart_count += 1
        exit_code = self._process.returncode if self._process else "unknown"
        logger.warning(
            "后端异常退出 (exit={})，第 {}/{} 次自动重启...",
            exit_code,
            self._restart_count,
            MAX_RESTART_ATTEMPTS,
        )

        # 检查 stderr 日志提供更多信息
        if self._stderr_path and self._stderr_path.is_file():
            try:
                tail = self._stderr_path.read_text(encoding="utf-8")[-500:]
                if tail.strip():
                    logger.warning("后端 stderr 尾部:\n{}", tail.strip())
            except Exception:
                pass

        time.sleep(RESTART_COOLDOWN)
        self._process = None  # 清理旧进程引用
        success = self.start(wait=True)
        if not success:
            return True  # 重启失败，需要通知
        return False

    def _wait_for_ready(self) -> bool:
        """等待后端 /health 就绪。"""
        deadline = time.time() + STARTUP_WAIT_TIMEOUT
        while time.time() < deadline:
            # 检查进程是否还活着
            if self._process and self._process.poll() is not None:
                exit_code = self._process.returncode
                logger.error("后端进程已退出 (exit={})", exit_code)
                # 读取 stderr 输出
                if self._stderr_path and self._stderr_path.is_file():
                    try:
                        err = self._stderr_path.read_text(encoding="utf-8")[-500:]
                        if err.strip():
                            logger.error("后端错误输出:\n{}", err.strip())
                    except Exception:
                        pass
                return False
            if self.health_check():
                logger.info("后端就绪 ✓")
                return True
            time.sleep(STARTUP_POLL_INTERVAL)
        logger.error("后端启动超时 ({}s)", STARTUP_WAIT_TIMEOUT)
        return False

    @staticmethod
    def _build_backend_env() -> dict[str, str]:
        """构建后端子进程环境，避免继承不兼容的 PYTHONPATH。"""
        env = dict(os.environ)
        raw_pythonpath = env.get("PYTHONPATH")
        sanitized, changed = _sanitize_pythonpath(raw_pythonpath)
        if not changed:
            return env

        if sanitized:
            env["PYTHONPATH"] = sanitized
            logger.warning("检测到不兼容 PYTHONPATH，已过滤后端子进程环境")
        else:
            env.pop("PYTHONPATH", None)
            logger.warning("检测到不兼容 PYTHONPATH，已为后端子进程清空该变量")
        return env

    @staticmethod
    def _is_port_in_use() -> bool:
        """检查端口是否已被占用。"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((BACKEND_HOST, BACKEND_PORT))
            return result == 0
