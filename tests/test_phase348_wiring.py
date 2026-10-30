"""Phase 348 — the new modules are reached from their integration points.

`create_app` routes `/v1/shop/{shop_id}/audit` and stacks `AuditMiddleware`
inside `RateLimitMiddleware`; the middleware calls `append_event`; the CLI
registers `audit`; and `login` sets the caller. Source is read with
`code_of`, comments and docstrings blanked, as 244G's meta-guard requires.
"""

from __future__ import annotations

from support.source_guards import code_of

from motodiag.api import create_app, middleware
from motodiag.api.routes import auth as auth_routes
from motodiag.api.routes import audit as audit_routes
from motodiag.cli import audit as audit_cli


def test_create_app_routes_the_reader_under_the_audit_tag():
    spec = create_app().openapi()
    op = spec["paths"]["/v1/shop/{shop_id}/audit"]["get"]
    assert op["tags"] == ["audit"]
    assert "audit" in {t["name"] for t in spec["tags"]}


def test_the_audit_middleware_is_inside_the_rate_limit():
    stack = [m.cls for m in create_app().user_middleware]  # outermost first
    assert middleware.AuditMiddleware in stack
    assert stack.index(middleware.AuditMiddleware) > stack.index(middleware.RateLimitMiddleware)


def test_the_middleware_writes_through_append_event_and_one_db_path_helper():
    assert "append_event(" in code_of(middleware.AuditMiddleware)
    for target in (middleware.AuditMiddleware, middleware.RateLimitMiddleware):
        assert "_request_db_path(" in code_of(target), target
    assert "dependency_overrides" not in code_of(middleware.RateLimitMiddleware)


def test_the_reader_gates_on_manage_users_and_filters_by_shop():
    code = code_of(audit_routes.shop_audit)
    assert 'require_shop_permission(shop_id, user.id, "manage_users"' in code
    assert "shop_id=shop_id" in code


def test_the_cli_registers_audit():
    from motodiag.cli.main import cli

    assert "audit" in cli.commands
    assert set(cli.commands["audit"].commands) == {"list", "verify", "export"}
    assert "verify_chain(" in code_of(audit_cli)


def test_login_sets_the_caller():
    assert "request.state.caller = Caller(" in code_of(auth_routes.login)
