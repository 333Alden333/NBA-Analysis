"""SQLAlchemy base, engine factory, and session factory."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def create_db_engine(db_path: str = "data/hermes.db"):
    """Create a SQLite engine with PRAGMA foreign_keys=ON."""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_session_factory(engine):
    """Return a sessionmaker bound to the given engine."""
    return sessionmaker(bind=engine)
