"""Demo auth (docs/05 §1) and the T-SEC-02 / T-SEC-03 foundations: role and plant scope come from the token only."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth import ROLES, Principal, current_principal, decode_token, issue_token, require_plant


@pytest.fixture(autouse=True)
def _demo_login_on(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "demo_login_enabled", True)


@pytest.mark.parametrize("role", ROLES)
def test_demo_login_issues_role_token(client, role):
    r = client.post("/v1/auth/demo-login", json={"user": role})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"token", "role", "plants"}
    assert body["role"] == role
    assert decode_token(body["token"]).role == role


def test_unknown_user_rejected(client):
    assert client.post("/v1/auth/demo-login", json={"user": "admin"}).status_code == 422


def test_role_cannot_be_injected_in_login_body(client):
    r = client.post("/v1/auth/demo-login", json={"user": "engineer", "role": "cfo"})
    assert r.status_code == 422


@pytest.fixture
def probe() -> TestClient:
    """A throwaway app exposing the auth dependency, so the test does not depend on later routers."""
    app = FastAPI()

    @app.get("/probe")
    def probe_route(principal: Annotated[Principal, Depends(current_principal)], role: str | None = None) -> dict:
        return {"role": principal.role}

    return TestClient(app)


def _bearer(user: str) -> dict:
    return {"Authorization": f"Bearer {issue_token(user)}"}


def test_role_comes_from_token_not_query(probe):
    r = probe.get("/probe", params={"role": "cfo"}, headers=_bearer("engineer"))
    assert r.json() == {"role": "engineer"}


def test_missing_token_is_401(probe):
    r = probe.get("/probe")
    assert r.status_code == 401
    assert r.json()["detail"] == "unauthenticated"


def test_forged_signature_is_401(probe):
    forged = jwt.encode({"sub": "x", "role": "cfo", "plants": ["THAR1"]}, "wrong-secret", algorithm="HS256")
    assert probe.get("/probe", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_expired_token_is_401(probe):
    old = issue_token("cfo", now=datetime.now(UTC) - timedelta(days=30))
    assert probe.get("/probe", headers={"Authorization": f"Bearer {old}"}).status_code == 401


def test_plant_outside_scope_is_403():
    principal = decode_token(issue_token("cfo"))
    require_plant(principal, "THAR1")
    with pytest.raises(HTTPException) as exc:
        require_plant(principal, "OTHER-PLANT")
    assert exc.value.status_code == 403
    assert exc.value.detail == "plant_out_of_scope"
