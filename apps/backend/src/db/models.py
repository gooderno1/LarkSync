from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SyncMapping(Base):
    __tablename__ = "sync_mappings"

    file_hash: Mapped[str] = mapped_column(String, primary_key=True)
    feishu_token: Mapped[str] = mapped_column(String, index=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    last_sync_mtime: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SyncLink(Base):
    __tablename__ = "sync_links"

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


class SyncTombstone(Base):
    __tablename__ = "sync_tombstones"

    id: Mapped[str] = mapped_column(String, primary_key=True)
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
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    cloud_folder_token: Mapped[str] = mapped_column(String, nullable=False)
    cloud_folder_name: Mapped[str | None] = mapped_column(String, nullable=True)
    base_path: Mapped[str | None] = mapped_column(String, nullable=True)
    sync_mode: Mapped[str] = mapped_column(String, nullable=False)
    update_mode: Mapped[str] = mapped_column(String, nullable=False, default="auto")
    md_sync_mode: Mapped[str] = mapped_column(String, nullable=False, default="enhanced")
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


class SyncBlockState(Base):
    __tablename__ = "sync_block_states"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    file_hash: Mapped[str] = mapped_column(String, index=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    cloud_token: Mapped[str] = mapped_column(String, index=True)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    block_hash: Mapped[str] = mapped_column(String, nullable=False)
    block_count: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
