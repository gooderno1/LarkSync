from pathlib import Path

from src.core.config import AppConfig, RuntimeProfile
from src.core.runtime_safety import validate_runtime_environment, validate_task_runtime


def test_snapshot_profile_requires_isolated_ports_data_and_file_token_store(tmp_path: Path) -> None:
    config = AppConfig(
        runtime_profile=RuntimeProfile.snapshot_test,
        token_store="keyring",
    )

    issues = validate_runtime_environment(
        config,
        backend_port=8000,
        lock_port=48901,
        runtime_data_dir=tmp_path,
        explicit_data_dir=False,
        production_backend_running=True,
    )

    assert any("8000" in issue for issue in issues)
    assert any("48901" in issue for issue in issues)
    assert any("LARKSYNC_DATA_DIR" in issue for issue in issues)
    assert any("file Token Store" in issue for issue in issues)


def test_live_profile_refuses_to_share_keyring_while_production_is_running(tmp_path: Path) -> None:
    config = AppConfig(runtime_profile=RuntimeProfile.live_readonly, token_store="keyring")

    issues = validate_runtime_environment(
        config,
        backend_port=18200,
        lock_port=49111,
        runtime_data_dir=tmp_path,
        explicit_data_dir=True,
        production_backend_running=True,
    )

    assert issues == ["正式版 8000 仍在运行，共享 keyring 的真实数据测试配置拒绝启动"]


def test_live_bidirectional_requires_allowlisted_root(tmp_path: Path) -> None:
    config = AppConfig(
        runtime_profile=RuntimeProfile.live_bidirectional,
        token_store="keyring",
    )

    issues = validate_runtime_environment(
        config,
        backend_port=18300,
        lock_port=49211,
        runtime_data_dir=tmp_path,
        explicit_data_dir=True,
        production_backend_running=False,
    )

    assert issues == ["live_bidirectional 必须配置至少一个专用飞书根目录 allowlist"]


def test_synthetic_profile_accepts_isolated_runtime(tmp_path: Path) -> None:
    config = AppConfig(runtime_profile=RuntimeProfile.synthetic_test, token_store="file")

    issues = validate_runtime_environment(
        config,
        backend_port=18000,
        lock_port=48911,
        runtime_data_dir=tmp_path,
        explicit_data_dir=True,
        production_backend_running=True,
    )

    assert issues == []


def test_live_readonly_accepts_only_download_task_with_deletion_off() -> None:
    config = AppConfig(runtime_profile=RuntimeProfile.live_readonly)

    assert validate_task_runtime(
        config,
        sync_mode="download_only",
        cloud_folder_token="real-root",
        delete_policy="off",
    ) == []
    assert len(
        validate_task_runtime(
            config,
            sync_mode="bidirectional",
            cloud_folder_token="real-root",
            delete_policy="safe",
        )
    ) == 2


def test_live_bidirectional_task_root_must_match_allowlist() -> None:
    config = AppConfig(
        runtime_profile=RuntimeProfile.live_bidirectional,
        allowed_cloud_roots=["test-root"],
    )

    assert validate_task_runtime(
        config,
        sync_mode="bidirectional",
        cloud_folder_token="business-root",
        delete_policy="safe",
    ) == ["任务云端根目录不在 live_bidirectional allowlist 中"]
