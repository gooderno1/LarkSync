from __future__ import annotations

import argparse
import base64
import getpass
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable


REQUIRED_SECRETS = (
    "MACOS_CERTIFICATE_P12_BASE64",
    "MACOS_CERTIFICATE_PASSWORD",
    "MACOS_CODESIGN_IDENTITY",
    "APPLE_ID",
    "APPLE_TEAM_ID",
    "APPLE_APP_SPECIFIC_PASSWORD",
)
MAX_GITHUB_SECRET_BYTES = 48 * 1024

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def run_command(command: list[str], *, input_text: str = "") -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"command failed: {' '.join(command)}\n{detail}")
    return result


def encode_certificate(path: Path) -> str:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"P12 文件不存在：{resolved}")
    if resolved.suffix.lower() not in {".p12", ".pfx"}:
        raise ValueError("证书文件必须是 .p12 或 .pfx")
    encoded = base64.b64encode(resolved.read_bytes()).decode("ascii")
    if len(encoded.encode("ascii")) > MAX_GITHUB_SECRET_BYTES:
        raise ValueError("P12 Base64 超过 GitHub 单个 Secret 的 48 KB 上限")
    return encoded


def set_repository_secret(
    repository: str,
    name: str,
    value: str,
    *,
    runner: CommandRunner = run_command,
) -> None:
    if name not in REQUIRED_SECRETS:
        raise ValueError(f"不允许写入未声明的 Secret：{name}")
    if not value.strip():
        raise ValueError(f"Secret 不能为空：{name}")
    runner(
        ["gh", "secret", "set", name, "--repo", repository],
        input_text=value,
    )


def list_repository_secrets(
    repository: str,
    *,
    runner: CommandRunner = run_command,
) -> set[str]:
    result = runner(
        ["gh", "secret", "list", "--repo", repository, "--json", "name"],
        input_text="",
    )
    data = json.loads(result.stdout or "[]")
    return {str(item["name"]) for item in data if isinstance(item, dict) and item.get("name")}


def missing_required_secrets(existing: set[str]) -> list[str]:
    return [name for name in REQUIRED_SECRETS if name not in existing]


def resolve_repository(raw: str, *, runner: CommandRunner = run_command) -> str:
    if raw.strip():
        repository = raw.strip()
    else:
        result = runner(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            input_text="",
        )
        repository = result.stdout.strip()
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
        raise ValueError(f"无效 GitHub 仓库：{repository!r}")
    return repository


def discover_developer_id_identity(*, runner: CommandRunner = run_command) -> str:
    if sys.platform != "darwin":
        return ""
    result = runner(
        ["security", "find-identity", "-v", "-p", "codesigning"],
        input_text="",
    )
    identities = re.findall(r'"(Developer ID Application: [^"]+)"', result.stdout)
    unique = list(dict.fromkeys(identities))
    return unique[0] if len(unique) == 1 else ""


def _prompt_required(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip() or default
    if not value:
        raise ValueError(f"{label}不能为空")
    return value


def _prompt_secret(label: str) -> str:
    value = getpass.getpass(f"{label}: ")
    if not value:
        raise ValueError(f"{label}不能为空")
    return value


def configure_secrets(args: argparse.Namespace, *, runner: CommandRunner = run_command) -> None:
    repository = resolve_repository(args.repo, runner=runner)
    runner(["gh", "auth", "status"], input_text="")

    if args.check:
        missing = missing_required_secrets(list_repository_secrets(repository, runner=runner))
        if missing:
            raise RuntimeError("缺少 GitHub Secrets：" + ", ".join(missing))
        print(f"[ok] {repository} 已配置全部 {len(REQUIRED_SECRETS)} 项 macOS 发布 Secret")
        return

    if not args.p12:
        raise ValueError("配置模式必须提供 --p12 /path/to/developer-id.p12")

    certificate_base64 = encode_certificate(Path(args.p12))
    discovered_identity = discover_developer_id_identity(runner=runner)
    identity = args.identity.strip() or _prompt_required(
        "Developer ID Application 完整身份",
        discovered_identity,
    )
    apple_id = args.apple_id.strip() or _prompt_required("Apple ID")
    team_id = args.team_id.strip() or _prompt_required("Apple Developer Team ID")
    p12_password = _prompt_secret("P12 导出密码（输入不回显）")
    app_password = _prompt_secret("Apple 应用专用密码（输入不回显）")

    print(f"将向 {repository} 写入 {len(REQUIRED_SECRETS)} 项 Actions Secrets。")
    confirmation = input("确认继续？输入 YES: ").strip()
    if confirmation != "YES":
        raise RuntimeError("用户取消，未写入 GitHub Secrets")

    values = {
        "MACOS_CERTIFICATE_P12_BASE64": certificate_base64,
        "MACOS_CERTIFICATE_PASSWORD": p12_password,
        "MACOS_CODESIGN_IDENTITY": identity,
        "APPLE_ID": apple_id,
        "APPLE_TEAM_ID": team_id,
        "APPLE_APP_SPECIFIC_PASSWORD": app_password,
    }
    for name in REQUIRED_SECRETS:
        set_repository_secret(repository, name, values[name], runner=runner)
        print(f"[set] {name}")

    missing = missing_required_secrets(list_repository_secrets(repository, runner=runner))
    if missing:
        raise RuntimeError("写入后仍缺少 GitHub Secrets：" + ", ".join(missing))
    print("[ok] 凭据已安全写入；敏感值未写入文件或命令参数。")
    print("下一步：手动运行 Release Build，并设置 validate_macos_credentials=true。")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="安全写入或检查 LarkSync macOS 正式发布所需 GitHub Secrets",
    )
    parser.add_argument("--repo", default="", help="GitHub 仓库 owner/name；默认读取当前仓库")
    parser.add_argument("--check", action="store_true", help="只检查 Secret 名称是否齐全")
    parser.add_argument("--p12", default="", help="Developer ID Application 的 .p12/.pfx 文件")
    parser.add_argument("--identity", default="", help="完整 Developer ID Application 签名身份")
    parser.add_argument("--apple-id", default="", help="用于 notarization 的 Apple ID")
    parser.add_argument("--team-id", default="", help="Apple Developer Team ID")
    args = parser.parse_args()

    try:
        configure_secrets(args)
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
