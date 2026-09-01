from sqlalchemy import Boolean, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.account_context import current_account_id

from .base import Base


LEGACY_ACCOUNT_ID = "legacy-default-account"


def scoped_account_id() -> str:
    """为同步运行中新建的所有领域记录注入当前账户。"""
    return current_account_id() or LEGACY_ACCOUNT_ID


class AppProfile(Base):
    __tablename__ = "app_profiles"
    __table_args__ = (
        UniqueConstraint("brand", "app_id", name="uq_app_profiles_brand_app_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    brand: Mapped[str] = mapped_column(String, nullable=False, default="feishu", index=True)
    app_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    secret_ref: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint(
            "brand",
            "app_profile_id",
            "open_id",
            name="uq_accounts_brand_profile_open_id",
        ),
        Index("idx_accounts_state_updated", "state", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    app_profile_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String, nullable=False, default="feishu")
    open_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    account_name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_name: Mapped[str | None] = mapped_column(String, nullable=True)
    tenant_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    tenant_display_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tenant_tag: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tenant_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_avatar_cache_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_metadata_status: Mapped[str | None] = mapped_column(String, nullable=True)
    tenant_metadata_updated_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    account_alias: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="connected", index=True)
    granted_scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_auth_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_protocol: Mapped[str] = mapped_column(
        String, nullable=False, default="device_v2", server_default="device_v2", index=True
    )
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)
    removed_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class UiPreference(Base):
    __tablename__ = "ui_preferences"

    device_id: Mapped[str] = mapped_column(String, primary_key=True)
    active_account_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)


class NotificationRecord(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_account_read_created", "account_id", "read_at", "created_at"),
        Index("idx_notifications_account_severity", "account_id", "severity", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="info", index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    source_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    action_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    read_at: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)


class SyncMapping(Base):
    __tablename__ = "sync_mappings"

    account_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=scoped_account_id,
        server_default=LEGACY_ACCOUNT_ID,
        index=True,
    )
    file_hash: Mapped[str] = mapped_column(String, primary_key=True)
    feishu_token: Mapped[str] = mapped_column(String, index=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    last_sync_mtime: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SyncLink(Base):
    __tablename__ = "sync_links"

    account_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True
    )
    local_path: Mapped[str] = mapped_column(String, primary_key=True)
    cloud_token: Mapped[str] = mapped_column(String, index=True)
    cloud_type: Mapped[str] = mapped_column(String, nullable=False)
    task_id: Mapped[str] = mapped_column(String, index=True)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cloud_parent_token: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    local_hash: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    local_size: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    local_mtime: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    cloud_revision: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    cloud_mtime: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    local_resource_signature: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )
    resource_sync_revision: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )
    placeholder_refresh_revision: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )


class SyncTombstone(Base):
    __tablename__ = "sync_tombstones"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    task_id: Mapped[str] = mapped_column(String, index=True)
    local_path: Mapped[str] = mapped_column(String, index=True)
    cloud_token: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    cloud_type: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    source: Mapped[str] = mapped_column(String, nullable=False)  # local/cloud
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    detected_at: Mapped[float] = mapped_column(Float, nullable=False)
    expire_at: Mapped[float] = mapped_column(Float, nullable=False)
    executed_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)


class ConflictRecord(Base):
    __tablename__ = "conflicts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    cloud_token: Mapped[str] = mapped_column(String, nullable=False, index=True)
    local_hash: Mapped[str] = mapped_column(String, nullable=False)
    db_hash: Mapped[str] = mapped_column(String, nullable=False)
    cloud_version: Mapped[int] = mapped_column(Integer, nullable=False)
    db_version: Mapped[int] = mapped_column(Integer, nullable=False)
    local_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    cloud_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_action: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class SyncTask(Base):
    __tablename__ = "sync_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    cloud_folder_token: Mapped[str] = mapped_column(String, nullable=False)
    cloud_folder_name: Mapped[str | None] = mapped_column(String, nullable=True)
    base_path: Mapped[str | None] = mapped_column(String, nullable=True)
    sync_mode: Mapped[str] = mapped_column(String, nullable=False)
    update_mode: Mapped[str] = mapped_column(String, nullable=False, default="auto")
    md_sync_mode: Mapped[str] = mapped_column(String, nullable=False, default="enhanced")
    ignored_subpaths: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    delete_policy: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    delete_grace_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    owner_device_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    owner_open_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)
    last_run_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        Index(
            "idx_sync_runs_task_started_updated",
            "task_id",
            "started_at",
            "updated_at",
        ),
    )

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="running")
    trigger_source: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    run_kind: Mapped[str] = mapped_column(String, nullable=False, default="activity", index=True)
    has_activity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    started_at: Mapped[float] = mapped_column(Float, nullable=False)
    finished_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    last_event_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downloaded_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflict_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delete_pending_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delete_failed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)


class SyncTaskCheckState(Base):
    __tablename__ = "sync_task_check_states"

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    direction: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="idle", index=True)
    trigger_source: Mapped[str] = mapped_column(String, nullable=False, default="scheduled_download")
    started_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    finished_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    last_change_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    change_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_no_change: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)


class SyncRunEvent(Base):
    __tablename__ = "sync_run_events"
    __table_args__ = (
        Index("idx_sync_run_events_run_timestamp", "run_id", "timestamp"),
        Index("idx_sync_run_events_task_timestamp", "task_id", "timestamp"),
        Index("idx_sync_run_events_run_status_timestamp", "run_id", "status", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    task_name: Mapped[str] = mapped_column(String, nullable=False, default="未命名任务")
    run_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True, default=None)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)


class ProblemRecord(Base):
    __tablename__ = "problems"
    __table_args__ = (
        Index("idx_problems_state_last_seen", "state", "last_seen_at"),
        Index("idx_problems_category_state", "category", "state"),
        Index("idx_problems_task_state", "task_id", "state"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    fingerprint: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="open", index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    object_kind: Mapped[str] = mapped_column(String, nullable=False)
    object_key: Mapped[str] = mapped_column(String, nullable=False)
    object_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[float] = mapped_column(Float, nullable=False)
    last_seen_at: Mapped[float] = mapped_column(Float, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    latest_run_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    latest_event_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    classifier_version: Mapped[str] = mapped_column(String, nullable=False)
    resolution_verification: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    ignored_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ignored_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolution_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    operation_family: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    actionability: Mapped[str] = mapped_column(String, nullable=False, default="diagnostic_only")
    resolved_by_run_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    resolved_by_event_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    last_good_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class ProblemRecoveryFact(Base):
    __tablename__ = "problem_recovery_facts"
    __table_args__ = (
        Index("idx_problem_recovery_resolution_time", "resolution_key", "occurred_at"),
        Index("idx_problem_recovery_task_time", "task_id", "occurred_at"),
    )

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    resolution_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    operation_family: Mapped[str] = mapped_column(String, nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    occurred_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)


class ProblemOccurrence(Base):
    __tablename__ = "problem_occurrences"
    __table_args__ = (
        Index(
            "idx_problem_occurrences_problem_occurred",
            "problem_id",
            "occurred_at",
        ),
        Index(
            "idx_problem_occurrences_source",
            "source_kind",
            "source_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    problem_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    event_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    occurred_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class ProblemActionRecord(Base):
    __tablename__ = "problem_actions"
    __table_args__ = (
        Index("idx_problem_actions_problem_requested", "problem_id", "requested_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    problem_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action_key: Mapped[str] = mapped_column(String, nullable=False)
    requested_at: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    finished_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_result: Mapped[str | None] = mapped_column(String, nullable=True)


class SyncMeta(Base):
    __tablename__ = "sync_meta"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)


class SyncBlockState(Base):
    __tablename__ = "sync_block_states"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False, default=scoped_account_id, server_default=LEGACY_ACCOUNT_ID, index=True)
    file_hash: Mapped[str] = mapped_column(String, index=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    cloud_token: Mapped[str] = mapped_column(String, index=True)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    block_hash: Mapped[str] = mapped_column(String, nullable=False)
    block_count: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
