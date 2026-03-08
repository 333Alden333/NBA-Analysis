"""Schedule model."""

from sqlalchemy import Integer, String, Text, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Schedule(Base):
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[str | None] = mapped_column(String(10), unique=True, nullable=True)
    season: Mapped[str | None] = mapped_column(String(10), nullable=True)
    game_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    home_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.team_id"), nullable=True)
    away_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.team_id"), nullable=True)
    arena: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
