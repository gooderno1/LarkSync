from __future__ import annotations

import base64
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable


def hidden_helper_creationflags(subprocess_module: Any) -> int:
    flags = (
        getattr(subprocess_module, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess_module, "CREATE_NO_WINDOW", 0)
    )
    flags |= getattr(subprocess_module, "CREATE_BREAKAWAY_FROM_JOB", 0)
    return flags


def hidden_helper_creationflag_attempts(preferred: int, breakaway_flag: int) -> list[int]:
    attempts: list[int] = []
    for flags in (
        preferred,
        preferred & ~breakaway_flag if breakaway_flag else preferred,
        0,
    ):
        if flags not in attempts:
            attempts.append(flags)
    return attempts


def is_retryable_hidden_helper_launch_error(exc: OSError) -> bool:
    if isinstance(exc, PermissionError):
        return True
    winerror = getattr(exc, "winerror", None)
    errno = getattr(exc, "errno", None)
    return winerror in {5, 13, 1314} or errno == 13


def launch_hidden_helper_process(
    command: list[str],
    *,
    subprocess_module: Any,
    creationflag_attempts: list[int],
    close_fds: bool = True,
    on_fallback: Callable[[str], None] | None = None,
    is_retryable_error: Callable[[OSError], bool] | None = None,
) -> tuple[subprocess.Popen[Any], int]:
    retryable = is_retryable_error or is_retryable_hidden_helper_launch_error
    last_error: OSError | None = None
    for index, flags in enumerate(creationflag_attempts):
        try:
            process = subprocess_module.Popen(command, creationflags=flags, close_fds=close_fds)
            return process, flags
        except OSError as exc:
            if not retryable(exc) or index == len(creationflag_attempts) - 1:
                raise
            last_error = exc
            if on_fallback is not None:
                on_fallback(
                    "隐藏 helper 启动失败，回退 creationflags="
                    f"{flags} ({type(exc).__name__}: {exc})"
                )
    if last_error is not None:
        raise last_error
    raise RuntimeError("未能启动隐藏 helper 进程")


def build_windows_powershell_command(powershell_executable: str, script: str) -> list[str]:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return [
        powershell_executable,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-EncodedCommand",
        encoded,
    ]


def build_windows_powershell_file_command(powershell_executable: str, script_path: Path) -> list[str]:
    return [
        powershell_executable,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(script_path),
    ]


def install_script_stem(path: Path, request_id: str) -> str:
    raw = request_id.strip() or path.stem or f"install-{int(time.time() * 1000)}"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip(".-")
    return (safe or "install")[:80]


def write_powershell_script(path: Path, content: str, *, is_windows: bool) -> None:
    encoding = "utf-8-sig" if is_windows else "utf-8"
    path.write_text(content, encoding=encoding)


def build_windows_installer_worker_script(
    path: Path,
    *,
    silent: bool = False,
    restart_path: Path | None = None,
    log_path: Path | None = None,
    handoff_path: Path | None = None,
    request_id: str = "",
) -> str:
    installer_escaped = str(path).replace("'", "''")
    restart_escaped = str(restart_path).replace("'", "''") if restart_path else ""
    log_escaped = str(log_path).replace("'", "''") if log_path else ""
    handoff_escaped = str(handoff_path).replace("'", "''") if handoff_path else ""
    request_escaped = request_id.replace("'", "''")
    silent_literal = "$true" if silent else "$false"
    return (
        f"$installerPath = '{installer_escaped}'; "
        f"$restartPath = '{restart_escaped}'; "
        f"$logPath = '{log_escaped}'; "
        f"$handoffPath = '{handoff_escaped}'; "
        f"$requestId = '{request_escaped}'; "
        f"$silentInstall = {silent_literal}; "
        "$expectedVersion = ''; "
        "$installerName = [System.IO.Path]::GetFileName($installerPath); "
        "$versionMatch = [regex]::Match($installerName, 'LarkSync-Setup-(v?\\d+\\.\\d+\\.\\d+(?:-dev\\.\\d+)?)', 'IgnoreCase'); "
        "if ($versionMatch.Success) { $expectedVersion = $versionMatch.Groups[1].Value; if (-not $expectedVersion.StartsWith('v')) { $expectedVersion = 'v' + $expectedVersion } }; "
        "function Write-InstallLog([string]$message) { "
        "if ([string]::IsNullOrWhiteSpace($logPath)) { return }; "
        "try { "
        "$parent = Split-Path -Parent $logPath; "
        "if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }; "
        "$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'; "
        "Add-Content -LiteralPath $logPath -Value \"[$timestamp] $message\" -Encoding UTF8 "
        "} catch {} "
        "}; "
        "function Write-Handoff([string]$stage, [string]$message, [int]$exitCode = 0) { "
        "if ([string]::IsNullOrWhiteSpace($handoffPath)) { return }; "
        "try { "
        "$parent = Split-Path -Parent $handoffPath; "
        "if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }; "
        "$payload = @{ request_id = $requestId; stage = $stage; message = $message; exit_code = $exitCode; timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() } | ConvertTo-Json -Compress; "
        "$utf8NoBom = [System.Text.UTF8Encoding]::new($false); "
        "[System.IO.File]::WriteAllText($handoffPath, $payload, $utf8NoBom) "
        "} catch {} "
        "}; "
        "function Test-PortOpen([int]$port) { "
        "try { "
        "$client = New-Object System.Net.Sockets.TcpClient; "
        "$async = $client.BeginConnect('127.0.0.1', $port, $null, $null); "
        "$ok = $async.AsyncWaitHandle.WaitOne(500, $false); "
        "if ($ok) { $client.EndConnect($async) }; "
        "$client.Close(); "
        "return $ok "
        "} catch { return $false } "
        "}; "
        "function Read-InstalledVersion() { "
        "try { "
        "if ([string]::IsNullOrWhiteSpace($restartPath)) { return '' }; "
        "$installDir = Split-Path -Parent $restartPath; "
        "$versionFile = Join-Path $installDir '_internal\\apps\\backend\\pyproject.toml'; "
        "if (-not (Test-Path -LiteralPath $versionFile)) { $versionFile = Join-Path $installDir 'apps\\backend\\pyproject.toml' }; "
        "if (-not (Test-Path -LiteralPath $versionFile)) { return '' }; "
        "$content = Get-Content -LiteralPath $versionFile -Raw -Encoding UTF8; "
        "$match = [regex]::Match($content, '(?m)^version\\s*=\\s*\"([^\"]+)\"'); "
        "if ($match.Success) { return $match.Groups[1].Value.Trim() }; "
        "return '' "
        "} catch { return '' } "
        "}; "
        "function Test-ExpectedVersionInstalled() { "
        "$installedVersion = Read-InstalledVersion; "
        "Write-InstallLog (\"安装后版本复核: expected=\" + $expectedVersion + \" installed=\" + $installedVersion); "
        "if ([string]::IsNullOrWhiteSpace($expectedVersion)) { return $false }; "
        "return ($installedVersion -eq $expectedVersion) "
        "}; "
        "function Start-RestartTarget([string]$reason) { "
        "if ([string]::IsNullOrWhiteSpace($restartPath)) { return $true }; "
        "for ($attempt = 1; $attempt -le 3; $attempt++) { "
        "try { "
        "$delay = [Math]::Min(2 + $attempt, 5); "
        "Start-Sleep -Seconds $delay; "
        "Write-InstallLog (\"尝试启动 LarkSync: reason=\" + $reason + \" attempt=\" + $attempt + \" path=\" + $restartPath); "
        "$restartProcess = Start-Process -FilePath $restartPath -PassThru -ErrorAction Stop; "
        "Write-InstallLog (\"重启进程已启动 pid=\" + $restartProcess.Id + \" attempt=\" + $attempt); "
        "$confirmed = 0; "
        "for ($probe = 1; $probe -le 6; $probe++) { "
        "Start-Sleep -Seconds 1; "
        "$alive = Get-Process -Id $restartProcess.Id -ErrorAction SilentlyContinue; "
        "$running = $false; "
        "if ($alive) { $running = $true }; "
        "if (-not $running -and (Test-PortOpen 48901)) { $running = $true }; "
        "if ($running) { "
        "$confirmed += 1; "
        "Write-InstallLog (\"重启确认探测通过 pid=\" + $restartProcess.Id + \" probe=\" + $probe + \" confirmed=\" + $confirmed); "
        "if ($confirmed -ge 2) { return $true } "
        "} else { "
        "$confirmed = 0 "
        "}; "
        "}; "
        "Write-InstallLog (\"重启进程过早退出 pid=\" + $restartProcess.Id + \" attempt=\" + $attempt); "
        "} catch { Write-InstallLog (\"启动 LarkSync 失败 reason=\" + $reason + \" attempt=\" + $attempt + \": \" + $_.Exception.Message) } "
        "}; "
        "return $false "
        "}; "
        "Write-Handoff 'helper_started' 'helper process started'; "
        "$argumentList = @(); "
        "if ($silentInstall) { $argumentList += '/S' }; "
        "Write-InstallLog (\"启动安装器请求: installer=\" + $installerPath + \" silent=\" + $silentInstall + \" expected=\" + $expectedVersion); "
        "try { "
        "$process = Start-Process -FilePath $installerPath -ArgumentList $argumentList -PassThru -ErrorAction Stop; "
        "} catch { "
        "$message = $_.Exception.Message; "
        "Write-Handoff 'launch_failed' $message 0; "
        "Write-InstallLog (\"启动安装器失败: \" + $message); "
        "if (-not (Start-RestartTarget 'launch_failed')) { Write-InstallLog (\"安装器未启动，恢复启动未确认: \" + $restartPath) }; "
        "exit 1 "
        "}; "
        "Write-Handoff 'installer_started' ('pid=' + $process.Id) 0; "
        "Write-InstallLog (\"安装器进程已启动 pid=\" + $process.Id); "
        "try { "
        "$process.WaitForExit(); "
        "$process.Refresh(); "
        "} catch { "
        "Write-InstallLog (\"等待安装器进程异常，回退 Wait-Process: \" + $_.Exception.Message); "
        "Wait-Process -Id $process.Id -ErrorAction SilentlyContinue; "
        "$process.Refresh() "
        "}; "
        "$exitCode = $null; "
        "try { $exitCode = $process.ExitCode } catch { Write-InstallLog (\"读取安装器退出码失败: \" + $_.Exception.Message) }; "
        "$exitCodeText = if ($null -eq $exitCode) { '<null>' } else { [string]$exitCode }; "
        "Write-InstallLog (\"安装器进程已退出 exit_code=\" + $exitCodeText); "
        "$versionMatched = Test-ExpectedVersionInstalled; "
        "if ($null -eq $exitCode) { Write-InstallLog (\"安装器退出码为空 exit_code=<null>，将以版本复核结果判断: matched=\" + $versionMatched) }; "
        "if (($null -ne $exitCode) -and ($exitCode -ne 0) -and $versionMatched) { Write-InstallLog (\"安装器退出码非 0 但目标版本已安装，按成功处理 exit_code=\" + $exitCodeText) }; "
        "if ((($null -eq $exitCode) -or ($exitCode -ne 0)) -and (-not $versionMatched)) { "
        "$installedVersion = Read-InstalledVersion; "
        "$failure = \"exit_code=\" + $exitCodeText + \"; expected=\" + $expectedVersion + \"; installed=\" + $installedVersion; "
        "Write-Handoff 'install_failed' $failure 1; "
        "Write-InstallLog (\"安装失败: \" + $failure); "
        "if (-not (Start-RestartTarget 'install_failed')) { Write-InstallLog (\"安装失败后恢复启动未确认: \" + $restartPath) }; "
        "exit 1 "
        "}; "
        "Write-Handoff 'install_succeeded' ('installer completed; exit_code=' + $exitCodeText) 0; "
        "if (Start-RestartTarget 'install_succeeded') { "
        "Write-Handoff 'restart_succeeded' 'restart process confirmed' 0 "
        "} else { "
        "Write-Handoff 'restart_failed' 'installed but restart did not stay alive' 0; "
        "Write-InstallLog '安装成功，但自动重启未确认，请手动启动 LarkSync' "
        "}; "
    )


def build_windows_silent_bootstrap_script(
    path: Path,
    *,
    log_path: Path | None = None,
    handoff_path: Path | None = None,
    request_id: str = "",
    powershell_executable: str,
    worker_path: Path,
) -> str:
    installer_escaped = str(path).replace("'", "''")
    log_escaped = str(log_path).replace("'", "''") if log_path else ""
    handoff_escaped = str(handoff_path).replace("'", "''") if handoff_path else ""
    request_escaped = request_id.replace("'", "''")
    powershell_escaped = powershell_executable.replace("'", "''")
    worker_escaped = str(worker_path).replace("'", "''")
    return (
        f"$installerPath = '{installer_escaped}'; "
        f"$logPath = '{log_escaped}'; "
        f"$handoffPath = '{handoff_escaped}'; "
        f"$requestId = '{request_escaped}'; "
        f"$powerShellPath = '{powershell_escaped}'; "
        f"$workerPath = '{worker_escaped}'; "
        "function Write-InstallLog([string]$message) { "
        "if ([string]::IsNullOrWhiteSpace($logPath)) { return }; "
        "try { "
        "$parent = Split-Path -Parent $logPath; "
        "if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }; "
        "$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'; "
        "Add-Content -LiteralPath $logPath -Value \"[$timestamp] $message\" -Encoding UTF8 "
        "} catch {} "
        "}; "
        "function Write-Handoff([string]$stage, [string]$message, [int]$exitCode = 0) { "
        "if ([string]::IsNullOrWhiteSpace($handoffPath)) { return }; "
        "try { "
        "$parent = Split-Path -Parent $handoffPath; "
        "if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }; "
        "$payload = @{ request_id = $requestId; stage = $stage; message = $message; exit_code = $exitCode; timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() } | ConvertTo-Json -Compress; "
        "$utf8NoBom = [System.Text.UTF8Encoding]::new($false); "
        "[System.IO.File]::WriteAllText($handoffPath, $payload, $utf8NoBom) "
        "} catch {} "
        "}; "
        "Write-InstallLog (\"启动静默安装 bootstrap: installer=\" + $installerPath); "
        "try { "
        "$workerArgs = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', $workerPath); "
        "$process = Start-Process -FilePath $powerShellPath -ArgumentList $workerArgs -WindowStyle Hidden -PassThru -ErrorAction Stop; "
        "} catch { "
        "$message = $_.Exception.Message; "
        "Write-Handoff 'launch_failed' $message 0; "
        "Write-InstallLog (\"启动静默安装 worker 失败: \" + $message); "
        "exit 1 "
        "}; "
        "Write-Handoff 'bootstrap_started' ('worker_pid=' + $process.Id) 0; "
        "Write-InstallLog (\"静默安装 worker 已启动 pid=\" + $process.Id); "
    )
