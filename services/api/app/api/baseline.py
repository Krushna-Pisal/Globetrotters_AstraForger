"""Baseline versions (docs/05 §5). Approved versions are immutable: PATCH always answers 409 baseline_immutable."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Connection

from app.api.deps import get_conn
from app.baseline import build
from app.core.auth import Principal, current_principal, require_plant
from app.core.bulk import audit

router = APIRouter(prefix="/v1/baseline", tags=["baseline"])
Conn = Annotated[Connection, Depends(get_conn)]
Who = Annotated[Principal, Depends(current_principal)]


def _require_role(principal: Principal, *roles: str) -> None:
    if principal.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="role_not_allowed")


@router.get("/versions")
def versions(plant_id: str, principal: Who, conn: Conn) -> list[dict]:
    _require_role(principal, "cfo", "presenter")
    require_plant(principal, plant_id)
    return [{k: (str(v) if v is not None else None) for k, v in r.items()} for r in build.versions(conn, plant_id)]


@router.post("/{version}/approve")
def approve(version: int, plant_id: str, principal: Who, conn: Conn) -> dict:
    _require_role(principal, "presenter")
    require_plant(principal, plant_id)
    try:
        n = build.approve(conn, plant_id, version, principal.sub)
    except build.BaselineError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="baseline_immutable") from exc
    audit(conn, principal.sub, "baseline.approve", f"{plant_id} v{version}", {"rows": n})
    return {"plant_id": plant_id, "version": version, "status": "approved", "rows": n}


@router.patch("/{version}")
def patch(version: int, plant_id: str, principal: Who, conn: Conn) -> dict:
    statuses = {r["version"]: r["status"] for r in build.versions(conn, plant_id)}
    if statuses.get(version) == "approved":
        audit(conn, principal.sub, "baseline.patch_refused", f"{plant_id} v{version}", {})
        raise HTTPException(status.HTTP_409_CONFLICT, detail="baseline_immutable")
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY, detail="drafts are rebuilt with `make baseline`, not patched"
    )
