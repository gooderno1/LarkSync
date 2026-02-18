from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Iterable

VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-dev\.(\d+))?$")


def parse_version(version: str) -> tuple[int, int, int, int | None]:
    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(f"invalid version format: {version}")
    major, minor, patch, dev = match.groups()
    return int(major), int(minor), int(patch), int(dev) if dev is not None else None


def bump_dev_version(version: str) -> str:
    major, minor, patch, dev = parse_version(version)
    if dev is None:
        # 当前是稳定版，切到下一个 patch 的 dev.1 分支
        patch += 1
        dev = 1
    else:
        dev += 1
    return f"v{major}.{minor}.{patch}-dev.{dev}"


def bump_patch_version(version: str) -> str:
    major, minor, patch, _ = parse_version(version)
    return f"v{major}.{minor}.{patch + 1}"


def to_stable_version(version: str) -> str:
    major, minor, patch, _ = parse_version(version)
    return f"v{major}.{minor}.{patch}"


def is_stable_version(version: str) -> bool:
    _, _, _, dev = parse_version(version)
    return dev is None


def _version_key(version: str) -> tuple[int, int, int]:
    major, minor, patch, _ = parse_version(version)
    return major, minor, patch


def latest_stable_version(versions: Iterable[str]) -> str | None:
    latest: str | None = None
    for raw in versions:
        candidate = raw.strip()
        if not candidate:
            continue
        try:
            major, minor, patch, dev = parse_version(candidate)
        except ValueError:
            continue
        if dev is not None:
            continue
        parsed = f"v{major}.{minor}.{patch}"
        if latest is None or _version_key(parsed) > _version_key(latest):
            latest = parsed
    return latest


def list_git_tags(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "tag", "--list", "v*"],
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def compute_next_stable_version(repo_root: Path, current_version: str) -> str:
    stable_from_current = to_stable_version(current_version)
    latest_tag = latest_stable_version(list_git_tags(repo_root))
    if latest_tag is None:
        return stable_from_current
    if _version_key(stable_from_current) > _version_key(latest_tag):
        return stable_from_current
    return bump_patch_version(latest_tag)


def update_json_version(path: Path, new_version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = new_version
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_pyproject_version(path: Path, new_version: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^version\s*=\s*"[^"]+"', f'version = "{new_version}"', text
    )
    if count == 0:
        raise ValueError("version field not found in pyproject.toml")
    path.write_text(updated, encoding="utf-8")


def update_changelog(path: Path, new_version: str, commit_msg: str, date_str: str) -> None:
    if not commit_msg.strip():
        raise ValueError("commit_msg is required")

    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["# CHANGELOG", ""]

    if not lines or lines[0].strip() != "# CHANGELOG":
        raise ValueError("CHANGELOG must start with '# CHANGELOG'")

    if len(lines) == 1:
        lines.append("")
    if lines[1] != "":
        lines.insert(1, "")

    entry = f"[{date_str}] {new_version} {commit_msg}"
    lines.insert(2, entry)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _strip_v(version: str) -> str:
    return version[1:] if version.startswith("v") else version


def sync_versions(repo_root: Path, new_version: str) -> None:
    update_json_version(repo_root / "package.json", new_version)
    frontend_package = repo_root / "apps/frontend/package.json"
    frontend_data = json.loads(frontend_package.read_text(encoding="utf-8"))
    frontend_current = str(frontend_data.get("version", ""))
    frontend_next = new_version if frontend_current.startswith("v") else _strip_v(new_version)
    update_json_version(frontend_package, frontend_next)
    update_pyproject_version(repo_root / "apps/backend/pyproject.toml", new_version)


def read_current_version(repo_root: Path) -> str:
    backend_pyproject = repo_root / "apps/backend/pyproject.toml"
    text = backend_pyproject.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if match:
        return match.group(1)
    data = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
    version = data.get("version")
    if isinstance(version, str):
        return version
    raise ValueError("unable to read current version")


def run_git(commands: Iterable[list[str]], *, cwd: Path | None = None) -> None:
    for cmd in commands:
        subprocess.run(cmd, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description="LarkSync release helper")
    parser.add_argument("commit_msg", nargs="?", help="commit message")
    parser.add_argument("--version", help="target version")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="发布稳定版：自动计算下一版本、打 tag 并推送",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="仅提交和打 tag，不执行 push",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    current_version = read_current_version(repo_root)
    if args.publish:
        next_version = args.version or compute_next_stable_version(repo_root, current_version)
        commit_msg = args.commit_msg or f"release: {next_version}"
    else:
        if not args.commit_msg:
            parser.error("commit_msg is required when --publish is not set")
        next_version = args.version or bump_dev_version(current_version)
        commit_msg = args.commit_msg

    sync_versions(repo_root, next_version)
    update_changelog(
        repo_root / "CHANGELOG.md",
        next_version,
        commit_msg,
        date.today().isoformat(),
    )

    commands: list[list[str]] = [
        ["git", "add", "."],
        ["git", "commit", "-m", commit_msg],
    ]
    if args.publish:
        commands.append(["git", "tag", next_version])
    if not args.no_push:
        commands.append(["git", "push"])
        if args.publish:
            commands.append(["git", "push", "origin", next_version])

    run_git(commands, cwd=repo_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
