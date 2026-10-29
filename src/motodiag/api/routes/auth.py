"""Staff logins: login, the caller, logout, sessions, passwords (Phase 303).

A login returns a session token (``mds_...``) once, in its response body
and nowhere else. The token is a row of ``api_keys`` and is sent the way a
key is (``X-API-Key`` or ``Authorization: Bearer``), so every route that
takes a key takes it too.

Every login failure is one 401 with one problem type: an unknown name, a
wrong password, a user with no password and an inactive user cannot be
told apart.

The one new permission gate is the owner's password reset for a member,
which needs ``manage_users`` at that shop. It refuses a target who is an
owner at any shop, or who belongs to any other shop where the caller has
no ``manage_users`` (the operator's K56), so one shop's owner cannot take
over a login another shop relies on.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user, require_tier
from motodiag.auth.passwords import hash_password, verify_password
from motodiag.auth.sessions_repo import (
    LOGIN_FAILED,
    LoginFailedError,
    LoginSessionNotFoundError,
    NotASessionError,
    authenticate,
    create_session,
    get_session,
    list_user_sessions,
    revoke_session,
    revoke_user_sessions,
    session_client,
    session_expires_at,
)
from motodiag.auth.users_repo import get_user, update_user
from motodiag.core.config import get_settings
from motodiag.core.database import get_connection
from motodiag.shop.rbac import (
    PermissionDenied,
    ShopMembershipNotFoundError,
    get_shop_member,
    has_shop_permission,
    list_member_permissions,
    list_shops_for_user,
    require_shop_permission,
)
from motodiag.shop.shop_repo import get_shop

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    client: Optional[str] = Field(None, max_length=64)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    new_password: str


def _lifetime() -> int:
    return get_settings().session_lifetime_days


def _user_block(user: dict) -> dict:
    return {
        "id": int(user["id"]),
        "username": user["username"],
        "full_name": user.get("full_name"),
        "email": user.get("email"),
    }


def _memberships(user_id: int, db_path: str) -> list[dict]:
    out = []
    for m in list_shops_for_user(user_id, active_only=True, db_path=db_path):
        shop = get_shop(m.shop_id, db_path=db_path) or {}
        out.append({
            "shop_id": m.shop_id,
            "shop_name": shop.get("name"),
            "role": m.role,
            "permissions": list_member_permissions(
                m.shop_id, user_id, db_path=db_path,
            ),
        })
    return out


@router.post("/login", summary="Log in with a username and password")
def login(req: LoginRequest, db_path: str = Depends(get_db_path)) -> dict:
    """A session token, shown once, with the user's shops and roles."""
    user = authenticate(req.username, req.password, db_path=db_path)
    if user is None:
        raise LoginFailedError(LOGIN_FAILED)
    row, token = create_session(int(user["id"]), req.client, db_path=db_path)
    logger.info("login: user id=%d session id=%d", row.user_id, row.id)
    return {
        "token": token,
        "expires_at": session_expires_at(row, _lifetime()),
        "user": _user_block(user),
        "memberships": _memberships(row.user_id, db_path),
    }


@router.get("/me", summary="Who the caller is, and their shops")
def me(
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    row = get_user(user.id, db_path=db_path) or {}
    return {
        "user": _user_block({**row, "id": user.id}),
        "memberships": _memberships(user.id, db_path),
        "credential": {
            "kind": user.credential_kind,
            "id": user.api_key_id,
            "prefix": user.api_key_prefix,
        },
        "tier": user.tier,
    }


@router.post("/logout", status_code=204, summary="End the calling session")
def logout(
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Response:
    if user.credential_kind != "session":
        raise NotASessionError(
            "logout ends a session; an API key is revoked with "
            "`motodiag apikey revoke`"
        )
    revoke_session(user.api_key_id, db_path=db_path)
    return Response(status_code=204)


@router.get("/sessions", summary="The caller's open sessions")
def sessions(
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> dict:
    current = user.api_key_id if user.credential_kind == "session" else None
    items = [
        {
            "id": s.id,
            "prefix": s.key_prefix,
            "client": session_client(s),
            "created_at": s.created_at,
            "expires_at": session_expires_at(s, _lifetime()),
            "last_used_at": s.last_used_at,
            "current": s.id == current,
        }
        for s in list_user_sessions(user.id, db_path=db_path)
    ]
    return {"items": items, "total": len(items)}


@router.delete(
    "/sessions/{session_id}", status_code=204,
    summary="End one of the caller's sessions",
)
def end_session(
    session_id: int,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Response:
    row = get_session(session_id, db_path=db_path)
    if row is None or row.user_id != user.id:
        raise LoginSessionNotFoundError(f"no session id={session_id}")
    revoke_session(session_id, db_path=db_path)
    return Response(status_code=204)


@router.post(
    "/password", status_code=204,
    summary="Change the caller's own password",
)
def change_password(
    req: PasswordChangeRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Response:
    """Every other session of the user is ended; the calling one is kept."""
    row = get_user(user.id, db_path=db_path) or {}
    if not verify_password(req.current_password, row.get("password_hash")):
        raise LoginFailedError("current password is wrong")
    update_user(
        user.id, {"password_hash": hash_password(req.new_password)},
        db_path=db_path,
    )
    keep = user.api_key_id if user.credential_kind == "session" else None
    revoke_user_sessions(user.id, keep_session_id=keep, db_path=db_path)
    return Response(status_code=204)


def _owner_anywhere(user_id: int, db_path: str) -> bool:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM shop_members WHERE user_id = ? AND role = 'owner' "
            "LIMIT 1",
            (user_id,),
        ).fetchone()
    return row is not None


@router.post(
    "/shops/{shop_id}/members/{user_id}/password", status_code=204,
    summary="Set a shop member's password (needs manage_users)",
)
def reset_member_password(
    shop_id: int,
    user_id: int,
    req: PasswordResetRequest,
    caller: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> Response:
    """All the member's sessions are ended."""
    require_shop_permission(shop_id, caller.id, "manage_users", db_path=db_path)
    member = get_shop_member(shop_id, user_id, db_path=db_path)
    if member is None or not member.is_active:
        raise ShopMembershipNotFoundError(
            f"no active member: shop_id={shop_id}, user_id={user_id}"
        )
    # K56: memberships are read active or not, so a member set aside at
    # another shop, or a former owner, is still refused.
    if _owner_anywhere(user_id, db_path):
        raise PermissionDenied(
            f"user id={user_id} is an owner; an owner sets their own password"
        )
    others = list_shops_for_user(user_id, active_only=False, db_path=db_path)
    for other in others:
        if other.shop_id != shop_id and not has_shop_permission(
            other.shop_id, caller.id, "manage_users", db_path=db_path,
        ):
            raise PermissionDenied(
                f"user id={user_id} also belongs to a shop where "
                f"user id={caller.id} lacks 'manage_users'"
            )
    update_user(
        user_id, {"password_hash": hash_password(req.new_password)},
        db_path=db_path,
    )
    revoked = revoke_user_sessions(user_id, db_path=db_path)
    logger.info(
        "password reset: shop id=%d user id=%d by user id=%d, "
        "%d session(s) ended", shop_id, user_id, caller.id, revoked,
    )
    return Response(status_code=204)
