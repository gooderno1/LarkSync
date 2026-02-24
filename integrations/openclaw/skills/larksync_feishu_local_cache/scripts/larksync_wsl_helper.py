from __future__ import annotations

import importlib
import ipaddress
import os
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib import error, request
from urllib.parse import urlparse

HELPER_SCRIPT = Path(__file__).with_name("larksync_skill_helper.py")
DEFAULT_PORT = 8000
DEFAULT_TIMEOUT = 1.5
HEALTH_PATH = "/health"
KNOWN_COMMANDS = {
    "check",
    "configure-download",
    "create-task",
    "run-task",
    "bootstrap-daily",
}
_ROOT_MARKERS = ("apps", "integrations")


@dataclass(frozen=True)
class ProbeResult:
    name: str
    base_url: str
    connect_ok: bool
    health_ok: bool
    health_status: int | None
    latency_ms: int | None
    error: str | None


@dataclass(frozen=True)
class RuntimeOptions:
    auto_start_local_backend: bool
    auto_install_backend_deps: bool


def is_wsl() -> bool:
    if os.getenv("WSL_DISTRO_NAME"):
        return True
    try:
        content = Path("/proc/version").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    lowered = content.lower()
    return "microsoft" in lowered or "wsl" in lowered


def parse_runtime_options(args: list[str]) -> tuple[list[str], RuntimeOptions]:
    cleaned: list[str] = []
    auto_start_local_backend = True
    auto_install_backend_deps = True
    for arg in args:
        if arg == "--no-auto-start-local-backend":
            auto_start_local_backend = False
            continue
        if arg == "--auto-start-local-backend":
            auto_start_local_backend = True
            continue
        if arg == "--no-auto-install-backend-deps":
            auto_install_backend_deps = False
            continue
        if arg == "--auto-install-backend-deps":
            auto_install_backend_deps = True
            continue
        cleaned.append(arg)
    return cleaned, RuntimeOptions(
        auto_start_local_backend=auto_start_local_backend,
        auto_install_backend_deps=auto_install_backend_deps,
    )


def _find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if all((candidate / marker).exists() for marker in _ROOT_MARKERS):
            return candidate
    return None


def resolve_project_root() -> Path | None:
    env_root = os.getenv("LARKSYNC_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if candidate.exists():
            return candidate
    return _find_repo_root(Path(__file__).resolve())


def local_backend_base_url(port: int = DEFAULT_PORT) -> str:
    return f"http://localhost:{port}"


def _has_backend_requirements() -> bool:
    required_modules = ("fastapi", "uvicorn", "sqlalchemy", "pydantic")
    for name in required_modules:
        try:
            importlib.import_module(name)
        except Exception:
            return False
    return True


def _sanitize_pythonpath(raw_pythonpath: str | None) -> tuple[str | None, bool]:
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
        if has_mismatch and "site-packages" in normalized:
            changed = True
            continue
        kept_entries.append(cleaned)

    if not kept_entries:
        return None, changed or bool(raw_pythonpath.strip())

    sanitized = os.pathsep.join(kept_entries)
    return sanitized, changed or sanitized != raw_pythonpath


def _build_runtime_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    raw_pythonpath = env.get("PYTHONPATH")
    sanitized, changed = _sanitize_pythonpath(raw_pythonpath)
    if changed:
        if sanitized:
            env["PYTHONPATH"] = sanitized
        else:
            env.pop("PYTHONPATH", None)
    return env


def _install_backend_requirements(
    backend_dir: Path,
    env: dict[str, str] | None = None,
) -> tuple[bool, str | None]:
    req_file = backend_dir / "requirements.txt"
    if not req_file.is_file():
        return False, f"缺少依赖清单：{req_file}"
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
    try:
        subprocess.check_call(cmd, cwd=str(backend_dir), env=env)
    except Exception as exc:  # noqa: BLE001
        return False, f"安装后端依赖失败: {type(exc).__name__}: {exc}"
    return True, None


def _build_local_backend_env(project_root: Path) -> dict[str, str]:
    env = _build_runtime_env()
    env.setdefault("LARKSYNC_TOKEN_STORE", "file")
    env.setdefault("LARKSYNC_TOKEN_FILE", str(project_root / "data" / "token_store_wsl.json"))
    env.setdefault("LARKSYNC_AUTH_REDIRECT_URI", f"http://localhost:{DEFAULT_PORT}/auth/callback")
    return env


def _start_local_backend_process(
    *,
    backend_dir: Path,
    log_file: Path,
    env: dict[str, str],
) -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(DEFAULT_PORT),
        "--log-level",
        "warning",
    ]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    stream = open(log_file, "a", encoding="utf-8")
    try:
        process = subprocess.Popen(  # noqa: S603
            cmd,
            cwd=str(backend_dir),
            stdout=stream,
            stderr=stream,
            env=env,
            start_new_session=True,
        )
    finally:
        stream.close()
    return process


def _read_log_tail(log_file: Path, max_chars: int = 500) -> str:
    if not log_file.is_file():
        return ""
    try:
        return log_file.read_text(encoding="utf-8", errors="ignore")[-max_chars:]
    except Exception:
        return ""


def _is_base_url_healthy(base_url: str, timeout: float = DEFAULT_TIMEOUT) -> bool:
    probe = _probe_single("local", base_url, timeout=timeout)
    return probe.health_ok


def ensure_local_backend(
    *,
    auto_install_deps: bool = True,
    startup_timeout: float = 20.0,
) -> tuple[bool, str]:
    base_url = local_backend_base_url()
    if _is_base_url_healthy(base_url):
        return True, "本地后端已在运行"

    project_root = resolve_project_root()
    if project_root is None:
        return False, "无法定位项目根目录（需包含 apps/integrations/data）"
    backend_dir = project_root / "apps" / "backend"
    if not (backend_dir / "src" / "main.py").is_file():
        return False, f"未找到后端入口：{backend_dir / 'src' / 'main.py'}"

    if not _has_backend_requirements():
        if not auto_install_deps:
            return False, "缺少后端依赖（fastapi/uvicorn/sqlalchemy/pydantic）"
        env_for_install = _build_runtime_env()
        ok, message = _install_backend_requirements(backend_dir, env=env_for_install)
        if not ok:
            return False, message or "安装后端依赖失败"

    log_file = project_root / "data" / "logs" / "wsl-backend.log"
    env = _build_local_backend_env(project_root)
    process = _start_local_backend_process(
        backend_dir=backend_dir,
        log_file=log_file,
        env=env,
    )

    deadline = time.time() + startup_timeout
    while time.time() < deadline:
        if _is_base_url_healthy(base_url):
            return True, f"已在 WSL 启动本地后端（PID={process.pid}）"
        if process.poll() is not None:
            tail = _read_log_tail(log_file)
            detail = f"后端进程异常退出（exit={process.returncode}）"
            if tail.strip():
                detail = f"{detail}，日志尾部：{tail.strip()}"
            return False, detail
        time.sleep(0.5)

    tail = _read_log_tail(log_file)
    detail = "后端启动超时"
    if tail.strip():
        detail = f"{detail}，日志尾部：{tail.strip()}"
    return False, detail


def parse_default_gateway(route_text: str) -> str | None:
    for raw in route_text.splitlines():
        line = raw.strip()
        if not line or not line.startswith("default"):
            continue
        parts = line.split()
        for index, part in enumerate(parts):
            if part == "via" and index + 1 < len(parts):
                value = parts[index + 1].strip()
                if value:
                    return value
    return None


def parse_resolv_nameservers(text: str) -> list[str]:
    result: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not line.lower().startswith("nameserver"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        value = parts[1].strip()
        if value:
            result.append(value)
    return result


def _read_default_gateway() -> str | None:
    try:
        output = subprocess.check_output(
            ["ip", "route", "show", "default"],
            text=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None
    return parse_default_gateway(output)


def _read_resolv_nameservers() -> list[str]:
    try:
        content = Path("/etc/resolv.conf").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return parse_resolv_nameservers(content)


def candidate_base_urls(port: int = DEFAULT_PORT) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = [
        ("localhost", f"http://localhost:{port}"),
        ("loopback-ipv4", f"http://127.0.0.1:{port}"),
        ("docker-host-alias", f"http://host.docker.internal:{port}"),
    ]
    gateway = _read_default_gateway()
    if gateway:
        pairs.append(("default-gateway", f"http://{gateway}:{port}"))
    for index, ns in enumerate(_read_resolv_nameservers(), start=1):
        pairs.append((f"resolv-nameserver-{index}", f"http://{ns}:{port}"))

    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, base_url in pairs:
        if base_url in seen:
            continue
        seen.add(base_url)
        deduped.append((name, base_url))
    return deduped


def _probe_single(name: str, base_url: str, timeout: float = DEFAULT_TIMEOUT) -> ProbeResult:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    port = parsed.port or 80
    connect_ok = False
    health_ok = False
    status: int | None = None
    error_text: str | None = None
    latency_ms: int | None = None
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            connect_ok = True
        health_url = f"{base_url.rstrip('/')}{HEALTH_PATH}"
        req = request.Request(health_url, headers={"Accept": "application/json"}, method="GET")
        with request.urlopen(req, timeout=timeout) as resp:
            status = int(resp.getcode())
            health_ok = status == 200
            if not health_ok:
                error_text = f"health HTTP {status}"
    except error.HTTPError as exc:
        status = int(exc.code)
        error_text = f"health HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        error_text = f"{type(exc).__name__}: {exc}"
    latency_ms = int((time.perf_counter() - start) * 1000)
    return ProbeResult(
        name=name,
        base_url=base_url,
        connect_ok=connect_ok,
        health_ok=health_ok,
        health_status=status,
        latency_ms=latency_ms,
        error=error_text,
    )


def diagnose_wsl_endpoints(timeout: float = DEFAULT_TIMEOUT) -> list[ProbeResult]:
    return [_probe_single(name, base_url, timeout=timeout) for name, base_url in candidate_base_urls()]


def select_reachable_base_url(results: Iterable[ProbeResult]) -> str | None:
    for item in results:
        if item.health_ok:
            return item.base_url
    return None


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _extract_base_url(args: list[str]) -> str | None:
    for index, arg in enumerate(args):
        if arg == "--base-url":
            if index + 1 < len(args):
                return args[index + 1].strip()
            return None
        if arg.startswith("--base-url="):
            return arg.split("=", 1)[1].strip()
    return None


def _find_command_index(args: list[str]) -> int:
    for index, arg in enumerate(args):
        if arg in KNOWN_COMMANDS:
            return index
    for index, arg in enumerate(args):
        if not arg.startswith("-"):
            return index
    return len(args)


def ensure_remote_allow_flag(args: list[str]) -> list[str]:
    base_url = _extract_base_url(args)
    if not base_url:
        return list(args)
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    if not host or _is_loopback_host(host):
        return list(args)
    if "--allow-remote-base-url" in args:
        return list(args)
    patched = list(args)
    insert_at = _find_command_index(patched)
    patched.insert(insert_at, "--allow-remote-base-url")
    return patched


def _inject_base_url(args: list[str], base_url: str) -> list[str]:
    patched = list(args)
    insert_at = _find_command_index(patched)
    patched[insert_at:insert_at] = ["--base-url", base_url]
    return patched


def _print_diagnostics(results: list[ProbeResult]) -> None:
    print("WSL -> LarkSync 连接诊断:")
    for item in results:
        if item.health_ok:
            status = "OK"
        elif item.connect_ok:
            status = "PORT_OPEN_HEALTH_FAIL"
        else:
            status = "UNREACHABLE"
        health_part = str(item.health_status) if item.health_status is not None else "-"
        latency = f"{item.latency_ms}ms" if item.latency_ms is not None else "-"
        detail = item.error or "-"
        print(
            f"  - [{status}] {item.name}: {item.base_url} "
            f"(health={health_part}, latency={latency}, detail={detail})"
        )


def _run_inner_helper(args: list[str]) -> int:
    cmd = [sys.executable, str(HELPER_SCRIPT), *args]
    return subprocess.call(cmd)


def _print_help() -> None:
    print("用法:")
    print("  python larksync_wsl_helper.py diagnose")
    print("  python larksync_wsl_helper.py <larksync_skill_helper 参数...>")
    print("")
    print("说明:")
    print("  - 在 WSL 下未指定 --base-url 时，会自动探测 Windows 宿主机可达地址。")
    print("  - 若未探测到可达地址，默认自动在 WSL 本地拉起后端（可用 --no-auto-start-local-backend 关闭）。")
    print("  - 若本地缺少后端依赖，默认自动安装（可用 --no-auto-install-backend-deps 关闭）。")
    print("  - 若检测到远程 base-url，会自动补充 --allow-remote-base-url。")


def main(argv: list[str] | None = None) -> int:
    raw_args = list(argv if argv is not None else sys.argv[1:])
    if not raw_args or raw_args[0] in {"-h", "--help"}:
        _print_help()
        return 0
    args, options = parse_runtime_options(raw_args)
    if not args:
        _print_help()
        return 0

    if args[0] == "diagnose":
        results = diagnose_wsl_endpoints()
        _print_diagnostics(results)
        return 0 if select_reachable_base_url(results) else 2

    final_args = list(args)
    if is_wsl() and _extract_base_url(final_args) is None:
        diagnostics = diagnose_wsl_endpoints()
        selected = select_reachable_base_url(diagnostics)
        _print_diagnostics(diagnostics)
        if not selected and options.auto_start_local_backend:
            print("未探测到可达地址，尝试在当前 WSL 自动启动本地 LarkSync 后端...")
            ok, message = ensure_local_backend(
                auto_install_deps=options.auto_install_backend_deps
            )
            print(message)
            if ok:
                diagnostics = diagnose_wsl_endpoints()
                selected = select_reachable_base_url(diagnostics)
                _print_diagnostics(diagnostics)
        if not selected:
            print("未找到可达的 LarkSync 服务地址（:8000）。请先在 Windows 侧启动 LarkSync。")
            print("排查建议：")
            print("  1) Windows 端确认 LarkSync 后端已启动。")
            print("  2) Windows 端若手动设置过 LARKSYNC_BACKEND_BIND_HOST=127.0.0.1，请移除该变量或改为 0.0.0.0 后重启 LarkSync。")
            print("  3) 放行 Windows 防火墙 TCP 8000（WSL 网段）。")
            return 2
        print(f"自动选择可达地址: {selected}")
        final_args = _inject_base_url(final_args, selected)

    final_args = ensure_remote_allow_flag(final_args)
    return _run_inner_helper(final_args)


if __name__ == "__main__":
    raise SystemExit(main())
