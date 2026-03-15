"""Team model."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    abbreviation: Mapped[str | None] = mapped_column(String(5), nullable=True)
    full_name: Mapped[str] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    conference: Mapped[str | None] = mapped_column(String(10), nullable=True)
    division: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
