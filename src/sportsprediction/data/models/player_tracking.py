"""PlayerTracking model."""

from sqlalchemy import Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PlayerTracking(Base):
    __tablename__ = "player_tracking"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.player_id"), index=True)
    season: Mapped[str | None] = mapped_column(String(10), nullable=True)
    games_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    touches: Mapped[float | None] = mapped_column(Float, nullable=True)
    passes: Mapped[float | None] = mapped_column(Float, nullable=True)
    assists_per_touch: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
