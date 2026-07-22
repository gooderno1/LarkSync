from __future__ import annotations

from pathlib import Path

from src.core.config import AppConfig, RuntimeProfile


_RESERVED_PRODUCTION_BACKEND_PORTS = {18765, 8000}


def validate_runtime_environment(
    config: AppConfig,
    *,
    backend_port: int,
    lock_port: int,
    runtime_data_dir: Path,
    explicit_data_dir: bool,
    production_backend_running: bool,
) -> list[str]:
    """返回阻止当前运行配置启动的安全问题；空列表表示可启动。"""
    profile = config.runtime_profile
    if profile is RuntimeProfile.production:
        return []

    issues: list[str] = []
    if backend_port in _RESERVED_PRODUCTION_BACKEND_PORTS:
        issues.append(f"非 production 配置禁止使用正式版保留后端端口 {backend_port}")
    if lock_port == 48901:
        issues.append("非 production 配置禁止使用正式版实例锁端口 48901")
    if not explicit_data_dir:
        issues.append("非 production 配置必须显式设置独立 LARKSYNC_DATA_DIR")
    if not str(runtime_data_dir).strip():
        issues.append("运行数据目录不能为空")

    if profile in {RuntimeProfile.synthetic_test, RuntimeProfile.snapshot_test}:
        if config.token_store.strip().lower() != "file":
            issues.append(f"{profile.value} 必须使用隔离的 file Token Store")

    if profile in {RuntimeProfile.live_readonly, RuntimeProfile.live_bidirectional}:
        if config.token_store.strip().lower() != "keyring":
            issues.append(f"{profile.value} 必须复用系统 keyring，禁止复制 Token 文件")
        if production_backend_running:
            issues.append("正式版仍在运行，共享 keyring 的真实数据测试配置拒绝启动")

    if (
        profile is RuntimeProfile.live_bidirectional
        and not config.allowed_cloud_roots
    ):
        issues.append("live_bidirectional 必须配置至少一个专用飞书根目录 allowlist")

    return issues


def validate_task_runtime(
    config: AppConfig,
    *,
    sync_mode: str,
    cloud_folder_token: str,
    delete_policy: str | None,
) -> list[str]:
    """校验真实数据测试配置下单个任务的云端边界。"""
    issues: list[str] = []
    if config.runtime_profile is RuntimeProfile.snapshot_test:
        return ["snapshot_test 禁止执行同步任务"]
    if config.runtime_profile is RuntimeProfile.live_readonly:
        if sync_mode != "download_only":
            issues.append("live_readonly 仅允许 download_only 任务")
        if delete_policy != "off":
            issues.append("live_readonly 要求 delete_policy=off")
    if config.runtime_profile is RuntimeProfile.live_bidirectional:
        if cloud_folder_token not in config.allowed_cloud_roots:
            issues.append("任务云端根目录不在 live_bidirectional allowlist 中")
    return issues
