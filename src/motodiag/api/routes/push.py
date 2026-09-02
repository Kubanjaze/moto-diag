"""Phase 199 — device-token registration endpoints.

POST   /v1/push/register — upsert/rebind the caller's device token
DELETE /v1/push/register — remove a token (sign-out hygiene)

Authed via get_current_user (the token binds to a real user — pushes
are personal). Registration is idempotent; re-registering on every app
start is the intended client behavior (token rotation safety).
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user
from motodiag.push.registry import delete_token, register_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/push", tags=["push"])


class PushRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    token: str = Field(..., min_length=16, max_length=512)
    platform: Literal["ios", "android"] = "ios"


class PushRegisterResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    registered: bool


@router.post(
    "/register",
    response_model=PushRegisterResponse,
    summary="Register (or rebind) the caller's push device token",
)
def register_push_token(
    req: PushRegisterRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> PushRegisterResponse:
    register_token(
        user_id=user.id, token=req.token,
        platform=req.platform, db_path=db_path,
    )
    return PushRegisterResponse(registered=True)


@router.delete(
    "/register",
    response_model=PushRegisterResponse,
    summary="Deregister a push device token (sign-out hygiene)",
)
def deregister_push_token(
    req: PushRegisterRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> PushRegisterResponse:
    removed = delete_token(req.token, db_path=db_path)
    return PushRegisterResponse(registered=not removed)
