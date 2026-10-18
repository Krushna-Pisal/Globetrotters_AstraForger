"""FastAPI application. Monitoring only: no route writes commands to equipment or source systems (invariant 12)."""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, baseline, health, views_router
from app.core.config import get_settings

log = logging.getLogger("ps4")


def _warm_caches() -> None:
    """Build each dataset's default engineer view once so the first page load in a demo is fast."""
    from app.api.views import common, engineer
    from app.core.db import get_engine

    try:
        with get_engine().connect() as conn:
            for ds in conn.exec_driver_sql("SELECT id FROM dataset").scalars().all():
                info = common.dataset_info(conn, ds)
                if info["periods"]:
                    engineer.build(conn, info, common.parse_period(info["periods"][0]))
    except Exception as exc:  # noqa: BLE001 - warm-up is best effort (e.g. empty database before `make demo`)
        log.info("cache warm-up skipped: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if get_settings().warm_caches:
        threading.Thread(target=_warm_caches, name="warmup", daemon=True).start()
    yield


app = FastAPI(title="PS4 Performance Assurance Platform", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(baseline.router)
app.include_router(views_router.router)
