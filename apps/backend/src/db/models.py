from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SyncMapping(Base):
    __tablename__ = "sync_mappings"

    file_hash: Mapped[str] = mapped_column(String, primary_key=True)
    feishu_token: Mapped[str] = mapped_column(String, index=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    last_sync_mtime: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
