"""Phase 175 — FastAPI foundation tests (Track H opens).

Five test classes across ~30 tests:

- :class:`TestAppFactory` (4) — create_app wires routes, overrides
  dependencies, fresh per call, version matches Settings.
- :class:`TestMetaEndpoints` (5) — /healthz happy + degraded,
  /v1/version echoes package + schema + api_version,
  /openapi.json + /docs reachable.
- :class:`TestSmokeShopRoute` (4) — GET /v1/shops/{id} 200 happy,
  404 not-found with ProblemDetail, invalid-id coercion, request-id
  echoed.
- :class:`TestErrorHandling` (7) — ValueError catchall,
  InvalidWorkOrderTransition 409, WorkOrderNotFoundError 404,
  PermissionDenied 403, unhandled → 500 with no stack leak,
  request_id embedded in ProblemDetail.
- :class:`TestMiddleware` (3) — X-Request-ID echoed, client-supplied
  id honored, CORS preflight + non-allowed origin.
- :class:`TestServeCLI` (3) — --help works, command invokes
  uvicorn.run with effective host/port/level (mock-patched).

Tests use FastAPI's ``TestClient``; no real uvicorn process spawned.
Zero AI.
"""

from __future__ import annotations

import json as _json
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from motodiag.api import APP_VERSION, create_app
from motodiag.api.deps import get_db_path, get_settings
from motodiag.api.errors import ProblemDetail
from motodiag.api.middleware import REQUEST_ID_HEADER
from motodiag.core.config import Settings, reset_settings
from motodiag.core.database import init_db
from motodiag.shop import create_shop
from motodiag.shop.work_order_repo import (
    InvalidWorkOrderTransition, WorkOrderNotFoundError,
)
from motodiag.shop.rbac import PermissionDenied


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    """Fresh SQLite DB for API tests; returns the path."""
    path = str(tmp_path / "phase175_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    yield path
    reset_settings()


@pytest.fixture
def app(api_db):
    """Fresh FastAPI app pinned to the api_db."""
    return create_app(db_path_override=api_db)


@pytest.fixture
def client(app):
    """FastAPI TestClient."""
    return TestClient(app)


# ===========================================================================
# 1. create_app factory
# ===========================================================================


class TestAppFactory:

    def test_create_app_returns_fastapi(self, app):
        assert isinstance(app, FastAPI)

    def test_expected_routes_registered(self, app):
        paths = {r.path for r in app.routes}
        assert "/healthz" in paths
        assert "/v1/version" in paths
        assert "/v1/shops/{shop_id}" in paths
        assert "/openapi.json" in paths
        assert "/docs" in paths

    def test_fresh_instance_per_call(self, api_db):
        a = create_app(db_path_override=api_db)
        b = create_app(db_path_override=api_db)
        assert a is not b  # factory, not singleton

    def test_db_override_honored(self, api_db):
        app = create_app(db_path_override=api_db)
        override = app.dependency_overrides[get_db_path]
        assert override() == api_db


# ===========================================================================
# 2. Meta endpoints
# ===========================================================================


class TestMetaEndpoints:

    def test_healthz_ok(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["schema_version"] is not None
        assert body["schema_version"] >= 36

    def test_healthz_degraded_on_missing_db(self, tmp_path):
        # Point at a path that doesn't exist
        missing = str(tmp_path / "never-created.db")
        app = create_app(db_path_override=missing)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/healthz")
        # Missing DB → get_schema_version returns None → 503
        assert r.status_code == 503
        assert r.json()["status"] == "degraded"

    def test_version_endpoint(self, client):
        r = client.get("/v1/version")
        assert r.status_code == 200
        body = r.json()
        assert "package" in body
        assert body["api_version"] == "v1"
        assert body["schema_version"] >= 36

    def test_openapi_reachable(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert spec["info"]["title"] == "MotoDiag API"

    def test_docs_reachable(self, client):
        r = client.get("/docs")
        assert r.status_code == 200
        # Redoc HTML page
        assert "text/html" in r.headers.get("content-type", "")


# ===========================================================================
# 3. Shop smoke route
# ===========================================================================


class TestSmokeShopRoute:

    def test_get_shop_happy(self, api_db, client):
        shop_id = create_shop(
            "TestShop", phone="555-0100", db_path=api_db,
        )
        r = client.get(f"/v1/shops/{shop_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == shop_id
        assert body["name"] == "TestShop"

    def test_get_shop_not_found_returns_problem_detail(self, client):
        r = client.get("/v1/shops/99999")
        assert r.status_code == 404
        body = r.json()
        assert body["status"] == 404
        assert body["title"] == "Shop not found"
        assert body["type"].endswith("shop-not-found")
        assert "request_id" in body
        # Instance points to the original path
        assert body["instance"] == "/v1/shops/99999"

    def test_invalid_shop_id_coerced_to_422(self, client):
        # FastAPI's Pydantic coercion rejects non-int
        r = client.get("/v1/shops/not-a-number")
        assert r.status_code == 422

    def test_request_id_echoed_on_shop_route(self, api_db, client):
        shop_id = create_shop("EchoShop", db_path=api_db)
        r = client.get(f"/v1/shops/{shop_id}")
        assert REQUEST_ID_HEADER in r.headers
        assert len(r.headers[REQUEST_ID_HEADER]) >= 16


# ===========================================================================
# 4. Error handling
# ===========================================================================


class TestErrorHandling:

    @pytest.fixture
    def error_app(self, api_db):
        """App with extra routes that raise specific domain exceptions."""
        app = create_app(db_path_override=api_db)
        bench = APIRouter(prefix="/_bench")

        @bench.get("/value-error")
        def raise_value():
            raise ValueError("bad input")

        @bench.get("/transition")
        def raise_transition():
            raise InvalidWorkOrderTransition("open → bogus")

        @bench.get("/notfound")
        def raise_notfound():
            raise WorkOrderNotFoundError("wo id=404")

        @bench.get("/perm")
        def raise_perm():
            raise PermissionDenied("no write_shop")

        @bench.get("/boom")
        def boom():
            raise RuntimeError("unexpected")

        app.include_router(bench)
        return app

    @pytest.fixture
    def error_client(self, error_app):
        return TestClient(error_app, raise_server_exceptions=False)

    def test_value_error_maps_to_400(self, error_client):
        r = error_client.get("/_bench/value-error")
        assert r.status_code == 400
        body = r.json()
        assert body["status"] == 400
        assert "bad input" in (body.get("detail") or "")

    def test_invalid_transition_maps_to_409(self, error_client):
        r = error_client.get("/_bench/transition")
        assert r.status_code == 409
        body = r.json()
        assert body["type"].endswith("invalid-transition")

    def test_not_found_maps_to_404(self, error_client):
        r = error_client.get("/_bench/notfound")
        assert r.status_code == 404
        body = r.json()
        assert body["type"].endswith("work-order-not-found")

    def test_permission_denied_maps_to_403(self, error_client):
        r = error_client.get("/_bench/perm")
        assert r.status_code == 403
        body = r.json()
        assert body["type"].endswith("permission-denied")

    def test_unhandled_maps_to_500_without_leak(self, error_client):
        r = error_client.get("/_bench/boom")
        assert r.status_code == 500
        body = r.json()
        # No stack trace / "RuntimeError" / "unexpected" in body
        assert body.get("detail") is None
        assert "Traceback" not in _json.dumps(body)

    def test_problem_detail_has_request_id(self, error_client):
        r = error_client.get("/_bench/notfound")
        assert r.status_code == 404
        body = r.json()
        assert body.get("request_id") is not None

    def test_problem_detail_model_shape(self):
        # Pure schema test (no HTTP)
        p = ProblemDetail(title="x", status=418)
        d = p.model_dump(exclude_none=True)
        assert d["type"] == "about:blank"
        assert d["status"] == 418


# ===========================================================================
# 5. Middleware
# ===========================================================================


class TestMiddleware:

    def test_request_id_generated_when_absent(self, client):
        r = client.get("/healthz")
        assert REQUEST_ID_HEADER in r.headers
        # UUID4 hex is 32 chars
        assert len(r.headers[REQUEST_ID_HEADER]) >= 16

    def test_client_supplied_request_id_honored(self, client):
        r = client.get(
            "/healthz",
            headers={REQUEST_ID_HEADER: "trace-abc-123"},
        )
        assert r.headers[REQUEST_ID_HEADER] == "trace-abc-123"

    def test_cors_preflight_allows_configured_origin(
        self, api_db,
    ):
        # Explicitly configure CORS origin
        settings = Settings(
            db_path=api_db,
            api_cors_origins="http://example.test",
        )
        app = create_app(settings=settings, db_path_override=api_db)
        client = TestClient(app)
        r = client.options(
            "/v1/version",
            headers={
                "Origin": "http://example.test",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200
        assert (
            r.headers.get("access-control-allow-origin")
            == "http://example.test"
        )


# ===========================================================================
# 6. `motodiag serve` CLI
# ===========================================================================


class TestServeCLI:

    def test_serve_help_works(self):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["serve", "--help"])
        assert r.exit_code == 0
        assert "Launch the MotoDiag HTTP API" in r.output

    def test_serve_invokes_uvicorn_with_overrides(self):
        from motodiag.cli.main import cli
        runner = CliRunner()
        with patch("uvicorn.run") as mocked:
            r = runner.invoke(cli, [
                "serve",
                "--host", "0.0.0.0",
                "--port", "9090",
                "--log-level", "debug",
            ])
            assert r.exit_code == 0, r.output
            mocked.assert_called_once()
            kwargs = mocked.call_args.kwargs
            assert kwargs["host"] == "0.0.0.0"
            assert kwargs["port"] == 9090
            assert kwargs["log_level"] == "debug"
            assert kwargs["factory"] is True

    def test_serve_reload_disables_multi_workers(self):
        from motodiag.cli.main import cli
        runner = CliRunner()
        with patch("uvicorn.run") as mocked:
            r = runner.invoke(cli, [
                "serve", "--reload", "--workers", "4",
            ])
            assert r.exit_code == 0, r.output
            kwargs = mocked.call_args.kwargs
            assert kwargs["reload"] is True
            # Reload forces single worker (uvicorn constraint)
            assert kwargs["workers"] == 1
