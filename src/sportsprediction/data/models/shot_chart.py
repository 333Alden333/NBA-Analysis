"""ShotChart model."""

from sqlalchemy import Integer, String, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ShotChart(Base):
    __tablename__ = "shot_charts"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str] = mapped_column(String(10), ForeignKey("games.game_id"), index=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.player_id"), index=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.team_id"), nullable=True)
    period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seconds_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shot_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shot_zone_basic: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shot_zone_area: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shot_zone_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shot_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loc_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loc_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shot_made: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
