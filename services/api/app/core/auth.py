"""Demo JWT auth (docs/03 §4, docs/05 §1). The role comes ONLY from the token, never from a query or body."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings

Role = Literal["engineer", "operations", "cfo", "presenter"]
ROLES: tuple[Role, ...] = ("engineer", "operations", "cfo", "presenter")
ALGORITHM = "HS256"

# Four demo users, one per role. All see both demo plants.
DEMO_USERS: dict[str, dict] = {role: {"role": role, "plants": ["THAR1", "KGL-P2"]} for role in ROLES}


class Principal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sub: str
    role: Role
    plants: tuple[str, ...]


def issue_token(user: str, now: datetime | None = None) -> str:
    if user not in DEMO_USERS:
        raise ValueError(f"unknown demo user {user!r}")
    settings = get_settings()
    now = now or datetime.now(UTC)
    claims = {
        "sub": user,
        "role": DEMO_USERS[user]["role"],
        "plants": DEMO_USERS[user]["plants"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_ttl_minutes)).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> Principal:
    try:
        claims = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
        return Principal(sub=claims["sub"], role=claims["role"], plants=tuple(claims["plants"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="unauthenticated") from exc


_bearer = HTTPBearer(auto_error=False)


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="unauthenticated")
    return decode_token(credentials.credentials)


def require_plant(principal: Principal, plant_id: str) -> None:
    if plant_id not in principal.plants:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="plant_out_of_scope")
