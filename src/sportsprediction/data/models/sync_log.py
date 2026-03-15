"""SyncLog model for tracking data synchronization."""

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    last_sync_at: Mapped[str] = mapped_column(DateTime)
    records_synced: Mapped[int] = mapped_column(Integer, default=0)
    season: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success")
