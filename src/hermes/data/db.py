"""Database connection and session management."""

from contextlib import contextmanager

from .models.base import Base, create_db_engine, get_session_factory


def init_db(db_path: str = "data/hermes.db"):
    """Create engine, create all tables, return engine."""
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def get_session(engine):
    """Context manager yielding a database session."""
    Session = get_session_factory(engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
