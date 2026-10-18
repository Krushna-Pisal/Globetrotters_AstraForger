"""Role-scoped read endpoints for the prototype (D31). The role comes only from the token; the presenter may ask
for any lens and receives exactly what that role would receive (same builder, same guard).

GET  /v1/datasets
GET  /v1/overview?dataset_id=
GET  /v1/view?dataset_id=&period=YYYY-MM[&lens=]        lens only honoured for the presenter
GET  /v1/events/{event_id}/trace?dataset_id=            engineer, presenter
GET  /v1/workorders?dataset_id=&status=                 operations, presenter
POST /v1/workorders/{id}/transition {"to": ...}          operations, presenter (writes audit_event)
Monitoring only: transitions update the work-order record, never equipment (invariant 12).
"""

from typing import Annotated, Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection, text

from app.api.deps import get_conn
from app.api.views import cfo, engineer, operations, overview
from app.api.views import queries as q
from app.api.views.common import dataset_info, finish, fmt_ts, parse_period
from app.core.auth import Principal, current_principal, require_plant

router = APIRouter(prefix="/v1", tags=["views"])
Conn = Annotated[Connection, Depends(get_conn)]
Who = Annotated[Principal, Depends(current_principal)]
BUILDERS = {"engineer": engineer.build, "operations": operations.build, "cfo": cfo.build}


def _scoped(conn: Connection, principal: Principal, dataset_id: str) -> dict:
    info = dataset_info(conn, dataset_id)
    require_plant(principal, info["plant_id"])
    return info


def _require(principal: Principal, *roles: str) -> None:
    if principal.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="role_not_allowed")


@router.get("/datasets")
def datasets(principal: Who, conn: Conn) -> list[dict]:
    ids = conn.execute(text("SELECT id FROM dataset ORDER BY kind DESC, id")).scalars().all()
    out = []
    for i in ids:
        info = dataset_info(conn, i)
        if info["plant_id"] in principal.plants and info["periods"]:
            out.append(info | {"default_period": _default_period(i, info["periods"])})
    return out


def _default_period(dataset_id: str, periods: list[str]) -> str:
    return "2024-04" if dataset_id == "thar1_demo_2024" and "2024-04" in periods else periods[0]


@router.get("/overview")
def get_overview(dataset_id: str, principal: Who, conn: Conn) -> dict:
    info = _scoped(conn, principal, dataset_id)
    return overview.build(conn, info, principal.role)


@router.get("/view")
def view(dataset_id: str, period: str, principal: Who, conn: Conn, lens: str | None = None) -> dict:
    info = _scoped(conn, principal, dataset_id)
    chosen = principal.role if principal.role != "presenter" else (lens or "engineer")
    if chosen not in BUILDERS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unknown lens")
    payload = BUILDERS[chosen](conn, info, parse_period(period))
    return finish(conn, chosen, payload, principal.sub)


@router.get("/events/{event_id}/trace")
def event_trace(event_id: str, dataset_id: str, principal: Who, conn: Conn) -> dict:
    _require(principal, "engineer", "presenter")
    _scoped(conn, principal, dataset_id)
    ev = q.events(conn, dataset_id)
    ev = ev[ev["id"] == event_id]
    if ev.empty:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    e = ev.iloc[0]
    end = e["end_ts"] if pd.notna(e["end_ts"]) else e["start_ts"] + pd.Timedelta(days=7)
    end = min(end, e["start_ts"] + pd.Timedelta(days=7))
    t = q.trace(conn, dataset_id, e["asset_id"], e["start_ts"] - pd.Timedelta(hours=18), end + pd.Timedelta(hours=18))
    return {
        "event_id": event_id,
        "asset_id": e["asset_id"],
        "cause_code": e["cause_code"],
        "window": [fmt_ts(e["start_ts"]), fmt_ts(e["end_ts"])],
        "unit": "kWh per 15 min",
        "ts": [fmt_ts(x) for x in t["ts_start"]],
        "expected_kwh": t["ep"].round(2).tolist(),
        "actual_kwh": [None if pd.isna(v) else round(float(v), 2) for v in t["ea"]],
        "band_low_kwh": (t["ep"] * (1 - t["band"])).round(2).tolist(),
        "band_high_kwh": (t["ep"] * (1 + t["band"])).round(2).tolist(),
        "band_span_kwh": (t["ep"] * 2 * t["band"]).round(2).tolist(),
        "no_data": [bool(x == "no_data") for x in t["quality"]],
        "status": [None if pd.isna(s) else s for s in t["status"]],
    }


@router.get("/workorders")
def list_workorders(dataset_id: str, principal: Who, conn: Conn, status_: str | None = None) -> list[dict]:
    _require(principal, "operations", "presenter")
    _scoped(conn, principal, dataset_id)
    wos = operations.work_orders(conn, dataset_id)
    if status_:
        wos = wos[wos["status"] == status_]
    return [
        {
            "id": r.id,
            "status": r.status,
            "severity": r.severity,
            "cause_code": r.cause_code,
            "opened": fmt_ts(r.opened_at),
            "restored": fmt_ts(r.restored_at),
        }
        for r in wos.itertuples()
    ]


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: Literal["acknowledged", "onsite", "restored", "verified"]


@router.post("/workorders/{wo_id}/transition")
def transition(wo_id: str, body: Transition, principal: Who, conn: Conn) -> dict:
    _require(principal, "operations", "presenter")
    result = operations.transition(conn, wo_id, body.to, principal.sub)
    if result.get("error") == "not_found":
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    if "error" in result:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=result)
    return result
