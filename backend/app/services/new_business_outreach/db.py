"""Short-lived sync sessions for Fishy Finger jobs."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def open_session() -> tuple[Engine, sessionmaker]:
    """One connection, closed when the session closes.

    SQLAlchemy's default pool (5 + 10) times the scrape processes crowds the
    256 MB Postgres. NullPool matches the scrape-cycle digest.
    """
    engine = create_engine(
        get_settings().database_url_sync,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, factory
