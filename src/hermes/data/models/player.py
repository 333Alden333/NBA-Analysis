"""Player model."""

from sqlalchemy import Integer, String, Float, Text, Boolean, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Player(Base):
    __tablename__ = "players"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    full_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.team_id"), nullable=True)
    position: Mapped[str | None] = mapped_column(String(10), nullable=True)
    height: Mapped[str | None] = mapped_column(String(10), nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    season_exp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jersey: Mapped[str | None] = mapped_column(String(5), nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
