"""Auth endpoints (docs/05 §1, D30). Offline, no external identity provider.

POST /v1/auth/login       username + password -> JWT (role and plant scope from app_user)
GET  /v1/auth/me          who the token says you are
POST /v1/auth/demo-login  passwordless demo users; 404 unless DEMO_LOGIN_ENABLED=true
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, text

from app.api.deps import get_conn
from app.core.auth import DEMO_USERS, Principal, Role, current_principal, issue_token
from app.core.bulk import audit
from app.core.config import get_settings
from app.core.passwords import verify_password

router = APIRouter(prefix="/v1/auth", tags=["auth"])

HOME = {"engineer": "/engineer", "operations": "/operations", "cfo": "/cfo", "presenter": "/overview"}


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    username: str
    display_name: str
    role: Role
    plants: list[str]
    home: str
    expires_at: datetime


@router.post("/login", response_model=Session)
def login(body: LoginRequest, conn: Annotated[Connection, Depends(get_conn)]) -> Session:
    row = (
        conn.execute(
            text(
                "SELECT username, display_name, role, plants, password_hash, active FROM app_user WHERE username = :u"
            ),
            {"u": body.username.strip().lower()},
        )
        .mappings()
        .first()
    )
    if row is None or not row["active"] or not verify_password(body.password, row["password_hash"]):
        audit(conn, body.username[:64], "auth.login_failed", "app_user", {})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    now = datetime.now(UTC)
    conn.execute(text("UPDATE app_user SET last_login_at = :t WHERE username = :u"), {"t": now, "u": row["username"]})
    audit(conn, row["username"], "auth.login", "app_user", {"role": row["role"]})
    token = issue_token(
        row["username"], now=now, role=row["role"], plants=list(row["plants"]), name=row["display_name"]
    )
    return Session(
        token=token,
        username=row["username"],
        display_name=row["display_name"],
        role=row["role"],
        plants=list(row["plants"]),
        home=HOME[row["role"]],
        expires_at=now + timedelta(minutes=get_settings().jwt_ttl_minutes),
    )


class Me(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    display_name: str
    role: Role
    plants: list[str]
    home: str


@router.get("/me", response_model=Me)
def me(principal: Annotated[Principal, Depends(current_principal)]) -> Me:
    return Me(
        username=principal.sub,
        display_name=principal.name or principal.sub,
        role=principal.role,
        plants=list(principal.plants),
        home=HOME[principal.role],
    )


class DemoLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: Literal["engineer", "operations", "cfo", "presenter"]


class DemoLoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    role: Role
    plants: list[str]


@router.post("/demo-login", response_model=DemoLoginResponse)
def demo_login(body: DemoLoginRequest) -> DemoLoginResponse:
    if not get_settings().demo_login_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    user = DEMO_USERS[body.user]
    return DemoLoginResponse(token=issue_token(body.user), role=user["role"], plants=list(user["plants"]))
