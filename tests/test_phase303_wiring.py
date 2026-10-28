"""Phase 303 — the new modules are reached from their integration points.

`create_app` routes `/v1/auth/*` and the OpenAPI schema lists the login as
public; the CLI registers `user`; and the one tier function and the one
credential function are what deps, the middleware and the socket call.
"""

from __future__ import annotations

from support.source_guards import code_of

from motodiag.api import create_app
from motodiag.api import middleware
from motodiag.api.openapi import PUBLIC_PATH_PREFIXES
from motodiag.api.routes import live
from motodiag.auth import deps


def test_create_app_routes_the_auth_paths():
    paths = create_app().openapi()["paths"]
    for path in ("/v1/auth/login", "/v1/auth/me", "/v1/auth/logout", "/v1/auth/sessions",
                 "/v1/auth/sessions/{session_id}", "/v1/auth/password",
                 "/v1/auth/shops/{shop_id}/members/{user_id}/password"):
        assert path in paths, path


def test_the_login_is_public_and_the_rest_are_not():
    spec = create_app().openapi()
    assert "/v1/auth/login" in PUBLIC_PATH_PREFIXES
    assert not spec["paths"]["/v1/auth/login"]["post"].get("security")
    assert spec["paths"]["/v1/auth/me"]["get"].get("security")
    assert "auth" in {t["name"] for t in spec["tags"]}
    assert "mds_" in spec["components"]["securitySchemes"]["bearerAuth"]["description"]


def test_the_cli_registers_user():
    from motodiag.cli.main import cli

    assert "user" in cli.commands
    assert set(cli.commands["user"].commands) == {
        "create", "list", "set-password", "deactivate", "sessions", "logout"}


def test_one_credential_function_and_one_tier_function():
    for module in (middleware, live):
        code = code_of(module)
        assert "resolve_credential(" in code and "resolve_tier(" in code, module
        assert "verify_api_key(" not in code and "get_active_subscription(" not in code
    assert "resolve_credential(" in code_of(deps.get_api_key)
    assert "resolve_tier(" in code_of(deps.get_current_user)
