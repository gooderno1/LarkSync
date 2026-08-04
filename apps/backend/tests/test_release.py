from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT))

from scripts import release  # noqa: E402


def test_parse_version_valid() -> None:
    assert release.parse_version("v0.1.2-dev.3") == (0, 1, 2, 3)
    assert release.parse_version("0.1.2") == (0, 1, 2, None)


def test_parse_version_invalid() -> None:
    with pytest.raises(ValueError):
        release.parse_version("0.1")


def test_bump_dev_version() -> None:
    assert release.bump_dev_version("v0.1.2-dev.3") == "v0.1.2-dev.4"
    assert release.bump_dev_version("v0.1.2") == "v0.1.3-dev.1"


def test_compute_next_stable_version_uses_current_dev_when_ahead(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(release, "list_git_tags", lambda _repo: ["v0.1.2", "v0.1.1"])
    next_version = release.compute_next_stable_version(tmp_path, "v0.1.3-dev.4")
    assert next_version == "v0.1.3"


def test_compute_next_stable_version_bumps_from_latest_tag(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(release, "list_git_tags", lambda _repo: ["v0.1.2", "v0.1.1"])
    next_version = release.compute_next_stable_version(tmp_path, "v0.1.2")
    assert next_version == "v0.1.3"


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


def test_sync_versions_updates_frontend_lockfile(tmp_path: Path) -> None:
    backend = tmp_path / "apps" / "backend"
    frontend = tmp_path / "apps" / "frontend"
    backend.mkdir(parents=True)
    frontend.mkdir(parents=True)
    (tmp_path / "package.json").write_text(
        '{"name":"root","version":"v0.8.20-dev.3"}',
        encoding="utf-8",
    )
    (backend / "pyproject.toml").write_text(
        '[project]\nversion = "v0.8.20-dev.3"\n',
        encoding="utf-8",
    )
    (frontend / "package.json").write_text(
        '{"name":"frontend","version":"0.8.20-dev.3"}',
        encoding="utf-8",
    )
    (frontend / "package-lock.json").write_text(
        '{"name":"frontend","version":"0.8.20-dev.3","packages":{"":{"name":"frontend","version":"0.8.20-dev.3"}}}',
        encoding="utf-8",
    )

    release.sync_versions(tmp_path, "v0.8.20")

    assert json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))["version"] == "v0.8.20"
    assert 'version = "v0.8.20"' in (backend / "pyproject.toml").read_text(encoding="utf-8")
    assert json.loads((frontend / "package.json").read_text(encoding="utf-8"))["version"] == "0.8.20"
    lock = json.loads((frontend / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["version"] == "0.8.20"
    assert lock["packages"][""]["version"] == "0.8.20"


def test_verify_publish_prerequisites_accepts_complete_macos_secrets(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        release.macos_secrets,
        "resolve_repository",
        lambda _raw: "gooderno1/LarkSync",
    )
    monkeypatch.setattr(
        release.macos_secrets,
        "list_repository_secrets",
        lambda _repo: set(release.macos_secrets.REQUIRED_SECRETS),
    )

    release.verify_publish_prerequisites(tmp_path)


def test_verify_publish_prerequisites_rejects_missing_macos_secrets(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        release.macos_secrets,
        "resolve_repository",
        lambda _raw: "gooderno1/LarkSync",
    )
    monkeypatch.setattr(
        release.macos_secrets,
        "list_repository_secrets",
        lambda _repo: {"APPLE_ID"},
    )

    with pytest.raises(RuntimeError, match="MACOS_CERTIFICATE_P12_BASE64"):
        release.verify_publish_prerequisites(tmp_path)
