from pathlib import Path

from src.core import version as version_module


def test_get_version_reads_backend_pyproject(tmp_path: Path, monkeypatch) -> None:
    backend_dir = tmp_path / "apps" / "backend"
    backend_dir.mkdir(parents=True, exist_ok=True)
    (backend_dir / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "v1.2.3"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(version_module, "bundle_root", lambda: None)
    monkeypatch.setattr(version_module, "repo_root", lambda: tmp_path)

    assert version_module.get_version() == "v1.2.3"
