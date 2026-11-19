"""The Terms of Service: the current version, and a user's acceptance (Phase 334, K84).

``GET /v1/terms`` answers anyone with the current version, its date and the
two pages' addresses; signed in, it adds whether the caller has accepted
that version, and when. ``POST /v1/terms/accept`` records the caller's
acceptance of the version they were shown, which must be the current one,
so a stale screen cannot accept a text the user did not see.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from motodiag.api.deps import get_db_path
from motodiag.auth import terms_acceptance as terms
from motodiag.auth.api_key_repo import ApiKey
from motodiag.auth.deps import AuthedUser, get_api_key, get_current_user
from motodiag.core.config import get_settings

router = APIRouter(prefix="/terms", tags=["terms"])


class TermsInfo(BaseModel):
    version: str
    date: str
    terms_url: str
    privacy_url: str
    accepted: Optional[bool] = Field(
        None, description="Signed in: whether the caller accepted this "
                          "version; null for an anonymous caller")
    accepted_at: Optional[str] = Field(
        None, description="When the caller accepted it, UTC; null if not")


class AcceptRequest(BaseModel):
    version: str = Field(..., description="The version the user was shown")


class Acceptance(BaseModel):
    version: str
    accepted_at: str


@router.get("", response_model=TermsInfo,
            summary="The current Terms of Service, and whether the caller accepted them")
def current_terms(
    api_key: Optional[ApiKey] = Depends(get_api_key),
    db_path: str = Depends(get_db_path),
) -> TermsInfo:
    s = get_settings()
    info = TermsInfo(version=terms.TERMS_VERSION, date=terms.TERMS_DATE,
                     terms_url=s.terms_url, privacy_url=s.privacy_url)
    if api_key is not None:
        row = terms.get_acceptance(api_key.user_id, terms.TERMS_VERSION, db_path)
        info.accepted = row is not None
        info.accepted_at = row["accepted_at"] if row else None
    return info


@router.post("/accept", response_model=Acceptance,
             summary="Accept the current Terms of Service")
def accept_terms(
    body: AcceptRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> Acceptance:
    if body.version != terms.TERMS_VERSION:
        raise terms.TermsVersionStaleError(
            f"version {body.version!r} is not the current one; the current "
            f"version is {terms.TERMS_VERSION} (GET /v1/terms)")
    row = terms.record_acceptance(user.id, terms.TERMS_VERSION, db_path)
    return Acceptance(version=row["version"], accepted_at=row["accepted_at"])
