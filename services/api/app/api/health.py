"""GET /health: liveness plus a database round trip."""

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        db_ok = False
    return {"status": "ok", "db": db_ok}
