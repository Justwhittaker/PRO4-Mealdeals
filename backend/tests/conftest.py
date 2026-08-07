"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Prefer sync URL for spatial integration tests
DEFAULT_DB = "postgresql://mealdeals:mealdeals@localhost:5432/mealdeals"


def _db_url() -> str:
    return os.getenv("DATABASE_URL_SYNC") or os.getenv("TEST_DATABASE_URL") or DEFAULT_DB


def _postgis_available() -> bool:
    url = _db_url()
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            row = conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')")
            ).scalar()
            return bool(row)
    except OperationalError:
        return False
    except Exception:
        return False


@pytest.fixture(scope="session")
def db_url() -> str:
    return _db_url()


@pytest.fixture(scope="session")
def postgis_ready() -> bool:
    return _postgis_available()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "spatial: requires live PostGIS database"
    )
