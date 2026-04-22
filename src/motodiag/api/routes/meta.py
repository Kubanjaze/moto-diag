"""Meta routes: /healthz + /v1/version (Phase 175)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from motodiag.api.deps import get_db_path, get_settings
from motodiag.core.config import Settings
from motodiag.core.database import get_schema_version


router = APIRouter(tags=["meta"])


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str
    schema_version: Optional[int] = None
    detail: Optional[str] = None


class VersionInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    package: str
    schema_version: Optional[int] = None
    api_version: str = "v1"


@router.get(
    "/healthz",
    response_model=HealthStatus,
    summary="Liveness + DB connectivity check",
)
def healthz(
    response: Response,
    db_path: str = Depends(get_db_path),
) -> HealthStatus:
    """Returns 200 when the DB responds; 503 otherwise.

    Used by load balancers / container schedulers. Does not exercise
    any downstream repos — minimal work per probe.
    """
    try:
        schema = get_schema_version(db_path)
    except Exception as e:
        response.status_code = 503
        return HealthStatus(
            status="degraded", detail=f"db unreachable: {e}",
        )
    if schema is None:
        response.status_code = 503
        return HealthStatus(
            status="degraded", detail="schema_version table missing",
        )
    return HealthStatus(status="ok", schema_version=schema)


@router.get(
    "/v1/version",
    response_model=VersionInfo,
    summary="Package + schema version",
)
def version(
    settings: Settings = Depends(get_settings),
    db_path: str = Depends(get_db_path),
) -> VersionInfo:
    """Client contract check.

    Mobile clients (Track I) call this on startup to detect schema
    drift and refuse to write against an incompatible server.
    """
    try:
        schema = get_schema_version(db_path)
    except Exception:
        schema = None
    return VersionInfo(
        package=settings.version,
        schema_version=schema,
        api_version="v1",
    )
