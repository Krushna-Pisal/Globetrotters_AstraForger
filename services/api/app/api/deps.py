"""Shared FastAPI dependencies."""

from collections.abc import Iterator

from sqlalchemy import Connection

from app.core.db import get_engine


def get_conn() -> Iterator[Connection]:
    """One transaction per request; tests override this to point at the test database."""
    with get_engine().begin() as conn:
        yield conn
