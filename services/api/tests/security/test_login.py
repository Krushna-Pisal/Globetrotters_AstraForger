"""Password login (D30): good and bad credentials, /me, demo-login off by default."""

import pytest

from app.core.auth import decode_token
from app.core.config import get_settings

pytestmark = pytest.mark.db


@pytest.mark.parametrize("user", ["engineer", "operations", "cfo", "presenter"])
def test_login_issues_role_token(api, user):
    r = api.post("/v1/auth/login", json={"username": user, "password": f"thar1-{user}"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == user and decode_token(body["token"]).role == user
    me = api.get("/v1/auth/me", headers={"Authorization": f"Bearer {body['token']}"}).json()
    assert me["username"] == user and me["home"] == body["home"]


@pytest.mark.parametrize("username,password", [("cfo", "wrong"), ("nobody", "thar1-cfo"), ("cfo", "THAR1-CFO")])
def test_bad_credentials_are_401_without_detail(api, username, password):
    r = api.post("/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_credentials"


def test_username_is_case_and_space_insensitive(api):
    assert api.post("/v1/auth/login", json={"username": " CFO", "password": "thar1-cfo"}).status_code == 200


def test_role_cannot_be_injected_into_login(api):
    r = api.post("/v1/auth/login", json={"username": "engineer", "password": "thar1-engineer", "role": "cfo"})
    assert r.status_code == 422


def test_demo_login_disabled_by_default(api):
    assert get_settings().demo_login_enabled is False
    assert api.post("/v1/auth/demo-login", json={"user": "cfo"}).status_code == 404
