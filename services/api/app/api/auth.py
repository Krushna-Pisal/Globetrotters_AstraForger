"""POST /v1/auth/demo-login (docs/05 §1). Demo users only; runs offline, no external identity provider."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.core.auth import DEMO_USERS, Role, issue_token

router = APIRouter(prefix="/v1/auth", tags=["auth"])


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
    user = DEMO_USERS[body.user]
    return DemoLoginResponse(token=issue_token(body.user), role=user["role"], plants=list(user["plants"]))
