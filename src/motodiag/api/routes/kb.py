"""Knowledge base endpoints (Phase 179).

Thin read-only HTTP layer over Phase 05/06/08/09 KB repos.
All endpoints require `require_api_key` (no per-tier gating —
KB is a core product feature, not premium content).

No new repo code, no migration, no schema change.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import ApiKey, require_api_key
from motodiag.core.search import search_all
from motodiag.knowledge.dtc_repo import (
    get_dtc, list_all_categories, search_dtcs,
)
from motodiag.knowledge.issues_repo import (
    get_known_issue, search_known_issues,
)
from motodiag.knowledge.symptom_repo import search_symptoms


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kb", tags=["knowledge-base"])


# Cap list sizes to prevent abuse
_MAX_LIMIT = 200


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DTCResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    make: Optional[str] = None
    common_causes: list[str] = Field(default_factory=list)
    fix_summary: Optional[str] = None


class DTCListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    items: list[DTCResponse]
    total: int


class DTCCategoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: str
    description: Optional[str] = None


class SymptomResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    related_systems: list[str] = Field(default_factory=list)


class SymptomListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    items: list[SymptomResponse]
    total: int


class KnownIssueResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    description: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    severity: Optional[str] = None
    symptoms: list[str] = Field(default_factory=list)
    dtc_codes: list[str] = Field(default_factory=list)
    causes: list[str] = Field(default_factory=list)
    fix_procedure: Optional[str] = None
    parts_needed: list[str] = Field(default_factory=list)
    estimated_hours: Optional[float] = None


class KnownIssueListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    items: list[KnownIssueResponse]
    total: int


class UnifiedSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str
    dtcs: list[dict] = Field(default_factory=list)
    symptoms: list[dict] = Field(default_factory=list)
    known_issues: list[dict] = Field(default_factory=list)
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_list(value) -> list:
    """Coerce a JSON-or-already-list field to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    import json as _json
    try:
        parsed = _json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []


def _dtc_row_to_response(row: dict) -> DTCResponse:
    return DTCResponse(
        code=str(row.get("code", "")),
        description=row.get("description"),
        category=row.get("category"),
        severity=row.get("severity"),
        make=row.get("make"),
        common_causes=_as_list(row.get("common_causes")),
        fix_summary=row.get("fix_summary"),
    )


def _symptom_row_to_response(row: dict) -> SymptomResponse:
    return SymptomResponse(
        id=int(row.get("id", 0)),
        name=str(row.get("name", "")),
        description=row.get("description"),
        category=row.get("category"),
        related_systems=_as_list(row.get("related_systems")),
    )


def _issue_row_to_response(row: dict) -> KnownIssueResponse:
    return KnownIssueResponse(
        id=int(row.get("id", 0)),
        title=str(row.get("title", "")),
        description=row.get("description"),
        make=row.get("make"),
        model=row.get("model"),
        year_start=row.get("year_start"),
        year_end=row.get("year_end"),
        severity=row.get("severity"),
        symptoms=_as_list(row.get("symptoms")),
        dtc_codes=_as_list(row.get("dtc_codes")),
        causes=_as_list(row.get("causes")),
        fix_procedure=row.get("fix_procedure"),
        parts_needed=_as_list(row.get("parts_needed")),
        estimated_hours=row.get("estimated_hours"),
    )


# ---------------------------------------------------------------------------
# DTC routes
# ---------------------------------------------------------------------------


@router.get(
    "/dtc/categories",
    response_model=list[DTCCategoryResponse],
    summary="List DTC categories",
)
def list_categories_endpoint(
    _api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> list[DTCCategoryResponse]:
    rows = list_all_categories(db_path=db_path)
    return [
        DTCCategoryResponse(
            category=str(r.get("dtc_category") or r.get("category") or ""),
            description=r.get("description"),
        )
        for r in rows
    ]


@router.get(
    "/dtc",
    response_model=DTCListResponse,
    summary="Search DTCs",
)
def search_dtcs_endpoint(
    q: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    make: Optional[str] = None,
    limit: int = Query(50, ge=1, le=_MAX_LIMIT),
    _api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> DTCListResponse:
    rows = search_dtcs(
        query=q, category=category, severity=severity, make=make,
        db_path=db_path,
    )
    items = [_dtc_row_to_response(r) for r in rows[:limit]]
    return DTCListResponse(items=items, total=len(rows))


@router.get(
    "/dtc/{code}",
    response_model=DTCResponse,
    summary="Fetch a single DTC by code",
)
def get_dtc_endpoint(
    code: str,
    make: Optional[str] = None,
    _api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> DTCResponse:
    row = get_dtc(code, make=make, db_path=db_path)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"DTC code {code!r} not found",
        )
    return _dtc_row_to_response(row)


# ---------------------------------------------------------------------------
# Symptom routes
# ---------------------------------------------------------------------------


@router.get(
    "/symptoms",
    response_model=SymptomListResponse,
    summary="Search symptoms",
)
def search_symptoms_endpoint(
    q: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=_MAX_LIMIT),
    _api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> SymptomListResponse:
    rows = search_symptoms(
        query=q, category=category, db_path=db_path,
    )
    items = [_symptom_row_to_response(r) for r in rows[:limit]]
    return SymptomListResponse(items=items, total=len(rows))


# ---------------------------------------------------------------------------
# Known-issue routes
# ---------------------------------------------------------------------------


@router.get(
    "/issues",
    response_model=KnownIssueListResponse,
    summary="Search known issues",
)
def search_issues_endpoint(
    q: Optional[str] = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = Query(50, ge=1, le=_MAX_LIMIT),
    _api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> KnownIssueListResponse:
    rows = search_known_issues(
        query=q, make=make, model=model, year=year, db_path=db_path,
    )
    items = [_issue_row_to_response(r) for r in rows[:limit]]
    return KnownIssueListResponse(items=items, total=len(rows))


@router.get(
    "/issues/{issue_id}",
    response_model=KnownIssueResponse,
    summary="Fetch a single known issue by id",
)
def get_issue_endpoint(
    issue_id: int,
    _api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> KnownIssueResponse:
    row = get_known_issue(issue_id, db_path=db_path)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"known issue id={issue_id} not found",
        )
    return _issue_row_to_response(row)


# ---------------------------------------------------------------------------
# Unified search
# ---------------------------------------------------------------------------


@router.get(
    "/search",
    response_model=UnifiedSearchResponse,
    summary="Unified search across DTCs + symptoms + known issues",
)
def unified_search_endpoint(
    q: str = Query(..., min_length=1, max_length=200),
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    _api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> UnifiedSearchResponse:
    result = search_all(
        query=q, make=make, model=model, year=year, db_path=db_path,
    )
    return UnifiedSearchResponse(
        query=q,
        dtcs=result.get("dtc_codes", []),
        symptoms=result.get("symptoms", []),
        known_issues=result.get("known_issues", []),
        total=int(result.get("total", 0)),
    )
