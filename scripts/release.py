from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Iterable

VERSION_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-dev\.(\d+)$")


def parse_version(version: str) -> tuple[int, int, int, int]:
    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(f"invalid version format: {version}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def bump_dev_version(version: str) -> str:
    major, minor, patch, dev = parse_version(version)
    return f"v{major}.{minor}.{patch}-dev.{dev + 1}"


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


def sync_versions(repo_root: Path, new_version: str) -> None:
    update_json_version(repo_root / "package.json", new_version)
    update_json_version(repo_root / "apps/frontend/package.json", new_version)
    update_pyproject_version(repo_root / "apps/backend/pyproject.toml", new_version)


def read_current_version(repo_root: Path) -> str:
    data = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str):
        raise ValueError("package.json missing version")
    return version


def run_git(commands: Iterable[list[str]]) -> None:
    for cmd in commands:
        subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="LarkSync release helper")
    parser.add_argument("commit_msg", help="commit message, e.g. 'feat(core): add sync' ")
    parser.add_argument("--version", help="target version, default bumps dev number")
    args = parser.parse_args()

    repo_root = get_repo_root()
    current_version = read_current_version(repo_root)
    next_version = args.version or bump_dev_version(current_version)

    sync_versions(repo_root, next_version)
    update_changelog(
        repo_root / "CHANGELOG.md",
        next_version,
        args.commit_msg,
        date.today().isoformat(),
    )

    run_git(
        [
            ["git", "add", "."],
            ["git", "commit", "-m", args.commit_msg],
            ["git", "push"],
        ]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
