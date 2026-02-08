from pathlib import Path

from src.core import paths


def test_data_dir_env_override(monkeypatch, tmp_path: Path) -> None:
    custom = tmp_path / "custom-data"
    monkeypatch.setenv("LARKSYNC_DATA_DIR", str(custom))
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path / "repo")
    assert paths.data_dir() == custom.resolve()


def test_data_dir_prefers_repo_when_present(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "apps").mkdir(parents=True, exist_ok=True)
    (repo / "data").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("LARKSYNC_DATA_DIR", raising=False)
    monkeypatch.setattr(paths, "repo_root", lambda: repo)
    assert paths.data_dir() == repo / "data"


def test_data_dir_falls_back_to_app_data(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    fallback = tmp_path / "fallback"
    monkeypatch.delenv("LARKSYNC_DATA_DIR", raising=False)
    monkeypatch.setattr(paths, "repo_root", lambda: repo)
    monkeypatch.setattr(paths, "_default_app_data_dir", lambda: fallback)
    assert paths.data_dir() == fallback
