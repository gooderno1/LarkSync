from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT))

from scripts import release  # noqa: E402


def test_parse_version_valid() -> None:
    assert release.parse_version("v0.1.2-dev.3") == (0, 1, 2, 3)


def test_parse_version_invalid() -> None:
    with pytest.raises(ValueError):
        release.parse_version("0.1.2")


def test_bump_dev_version() -> None:
    assert release.bump_dev_version("v0.1.2-dev.3") == "v0.1.2-dev.4"


def test_update_files(tmp_path: Path) -> None:
    package_json = tmp_path / "package.json"
    pyproject = tmp_path / "pyproject.toml"
    changelog = tmp_path / "CHANGELOG.md"

    package_json.write_text('{"name":"demo","version":"v0.1.0-dev.1"}', encoding="utf-8")
    pyproject.write_text('[project]\nversion = "v0.1.0-dev.1"\n', encoding="utf-8")
    changelog.write_text(
        "# CHANGELOG\n\n[2026-01-01] v0.1.0-dev.1 feat: init\n",
        encoding="utf-8",
    )

    release.update_json_version(package_json, "v0.1.0-dev.2")
    release.update_pyproject_version(pyproject, "v0.1.0-dev.2")
    release.update_changelog(changelog, "v0.1.0-dev.2", "feat: bump", "2026-01-27")

    assert "v0.1.0-dev.2" in package_json.read_text(encoding="utf-8")
    assert "v0.1.0-dev.2" in pyproject.read_text(encoding="utf-8")

    lines = changelog.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# CHANGELOG"
    assert lines[2].startswith("[2026-01-27] v0.1.0-dev.2 feat: bump")
