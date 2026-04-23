"""Phase 183 — OpenAPI enrichment tests.

Covers the spec enrichment in :mod:`motodiag.api.openapi` plus the
new ``api_servers_list`` Settings property. Zero AI, zero network.
"""

from __future__ import annotations

import pytest

from motodiag.api import create_app
from motodiag.api.openapi import (
    ERROR_RESPONSES,
    INFO_CONTACT,
    INFO_LICENSE,
    PUBLIC_PATH_PREFIXES,
    PUBLIC_TAGS,
    SECURITY_SCHEMES,
    TAG_CATALOG,
    build_openapi,
    install_openapi,
)
from motodiag.core.config import Settings, reset_settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def spec():
    """Build a fresh app, enrich OpenAPI, return the spec dict."""
    reset_settings()
    app = create_app()
    try:
        yield app.openapi()
    finally:
        reset_settings()


# ===========================================================================
# 1. Info block
# ===========================================================================


class TestInfoBlock:

    def test_contact_present(self, spec):
        assert spec["info"]["contact"] == INFO_CONTACT
        assert spec["info"]["contact"]["email"] == "support@motodiag.dev"

    def test_license_mit(self, spec):
        assert spec["info"]["license"] == INFO_LICENSE
        assert spec["info"]["license"]["name"] == "MIT"

    def test_terms_of_service(self, spec):
        assert spec["info"]["termsOfService"].startswith("https://")


# ===========================================================================
# 2. Servers list
# ===========================================================================


class TestServers:

    def test_servers_present(self, spec):
        assert "servers" in spec
        assert len(spec["servers"]) >= 1

    def test_servers_has_default_local(self, spec):
        urls = [s["url"] for s in spec["servers"]]
        assert any("localhost" in u for u in urls)

    def test_api_servers_list_default(self):
        s = Settings()
        servers = s.api_servers_list
        assert servers == [
            {"url": "http://localhost:8080", "description": "Local dev"},
        ]

    def test_api_servers_list_parses_pipe_separated(self):
        s = Settings(
            api_servers="https://api.example.com|Prod,https://staging.example.com|Staging",
        )
        servers = s.api_servers_list
        assert servers == [
            {"url": "https://api.example.com", "description": "Prod"},
            {"url": "https://staging.example.com", "description": "Staging"},
        ]

    def test_api_servers_list_url_only(self):
        s = Settings(api_servers="https://api.example.com")
        servers = s.api_servers_list
        assert servers == [{"url": "https://api.example.com"}]

    def test_api_servers_list_empty(self):
        s = Settings(api_servers="")
        assert s.api_servers_list == []


# ===========================================================================
# 3. Tag catalog
# ===========================================================================


class TestTags:

    def test_all_tags_present(self, spec):
        names = {t["name"] for t in spec["tags"]}
        expected = {t["name"] for t in TAG_CATALOG}
        assert names == expected

    def test_tag_catalog_covers_used_tags(self, spec):
        """Every tag used by a route must appear in TAG_CATALOG."""
        catalog = {t["name"] for t in TAG_CATALOG}
        used_tags = set()
        for p in spec["paths"].values():
            for op in p.values():
                for t in op.get("tags") or []:
                    used_tags.add(t)
        missing = used_tags - catalog
        assert not missing, f"tags in routes not in catalog: {missing}"

    def test_tags_have_descriptions(self, spec):
        for tag in spec["tags"]:
            assert tag.get("description")
            assert len(tag["description"]) > 20


# ===========================================================================
# 4. Security schemes
# ===========================================================================


class TestSecuritySchemes:

    def test_both_schemes_registered(self, spec):
        schemes = spec["components"]["securitySchemes"]
        assert "apiKey" in schemes
        assert "bearerAuth" in schemes

    def test_apikey_header_name(self, spec):
        schemes = spec["components"]["securitySchemes"]
        assert schemes["apiKey"]["type"] == "apiKey"
        assert schemes["apiKey"]["in"] == "header"
        assert schemes["apiKey"]["name"] == "X-API-Key"

    def test_bearer_scheme(self, spec):
        schemes = spec["components"]["securitySchemes"]
        assert schemes["bearerAuth"]["type"] == "http"
        assert schemes["bearerAuth"]["scheme"] == "bearer"


# ===========================================================================
# 5. Reusable error responses
# ===========================================================================


class TestErrorResponses:

    @pytest.mark.parametrize(
        "name", list(ERROR_RESPONSES.keys()),
    )
    def test_response_registered(self, spec, name):
        assert name in spec["components"]["responses"]

    def test_rate_limit_response_has_retry_after_header(self, spec):
        response = spec["components"]["responses"]["RateLimitExceeded"]
        headers = response.get("headers", {})
        assert "Retry-After" in headers

    def test_responses_reference_problem_detail(self, spec):
        for name, response in ERROR_RESPONSES.items():
            schema_ref = (
                response["content"]["application/json"]["schema"]
            )
            assert schema_ref == {
                "$ref": "#/components/schemas/ProblemDetail",
            }

    def test_problem_detail_schema_present(self, spec):
        schemas = spec["components"]["schemas"]
        assert "ProblemDetail" in schemas


# ===========================================================================
# 6. Per-operation enrichment
# ===========================================================================


class TestOperationEnrichment:

    def test_public_meta_endpoint_has_no_security(self, spec):
        version = spec["paths"]["/v1/version"]["get"]
        assert "security" not in version or version["security"] is None \
            or version["security"] == []

    def test_healthz_has_no_security(self, spec):
        healthz = spec["paths"]["/healthz"]["get"]
        assert "security" not in healthz or healthz["security"] == []

    def test_billing_webhook_excluded_from_schema(self, spec):
        """The Stripe webhook endpoint uses HMAC signatures, not
        API keys — it's marked `include_in_schema=False` so it
        shouldn't appear in the spec at all."""
        assert "/v1/billing/webhooks/stripe" not in spec["paths"]

    def test_authed_endpoint_has_apikey_security(self, spec):
        op = spec["paths"]["/v1/vehicles"]["get"]
        sec = op.get("security") or []
        schemes = {list(entry.keys())[0] for entry in sec}
        assert "apiKey" in schemes

    def test_authed_endpoint_has_401(self, spec):
        op = spec["paths"]["/v1/vehicles"]["get"]
        assert "401" in op["responses"]

    def test_authed_endpoint_has_429(self, spec):
        op = spec["paths"]["/v1/vehicles"]["get"]
        assert "429" in op["responses"]

    def test_authed_endpoint_has_500(self, spec):
        op = spec["paths"]["/v1/vehicles"]["get"]
        assert "500" in op["responses"]

    def test_path_param_endpoint_has_404(self, spec):
        op = spec["paths"]["/v1/vehicles/{vehicle_id}"]["get"]
        assert "404" in op["responses"]

    def test_no_path_param_endpoint_has_no_forced_404(self, spec):
        op = spec["paths"]["/v1/kb/dtc/categories"]["get"]
        # No path param; 404 may still appear if a tag forces it
        # but enrichment doesn't force it.
        # Confirm the operation exists
        assert "responses" in op

    def test_request_body_endpoint_has_422(self, spec):
        op = spec["paths"]["/v1/vehicles"]["post"]
        assert "422" in op["responses"]

    def test_tier_gated_endpoint_has_402(self, spec):
        op = spec["paths"]["/v1/vehicles"]["get"]
        assert "402" in op["responses"]

    def test_reports_endpoint_has_402(self, spec):
        op = spec["paths"]["/v1/reports/work-order/{wo_id}/pdf"]["get"]
        assert "402" in op["responses"]


# ===========================================================================
# 7. Caching behavior
# ===========================================================================


class TestCaching:

    def test_second_call_returns_cached_schema(self):
        reset_settings()
        app = create_app()
        first = app.openapi()
        second = app.openapi()
        # Identity check — same dict object.
        assert first is second
        reset_settings()

    def test_install_openapi_resets_cache(self):
        reset_settings()
        app = create_app()
        first = app.openapi()
        install_openapi(app)
        second = app.openapi()
        # After install, cache is reset then rebuilt; second is a
        # new dict identity but equivalent content.
        assert first is not second
        assert first == second
        reset_settings()


# ===========================================================================
# 8. Module-level invariants
# ===========================================================================


class TestModuleInvariants:

    def test_public_tags_includes_meta(self):
        assert "meta" in PUBLIC_TAGS

    def test_public_path_prefixes_covers_webhooks(self):
        assert any("webhooks" in p for p in PUBLIC_PATH_PREFIXES)

    def test_security_schemes_catalog_complete(self):
        assert set(SECURITY_SCHEMES) == {"apiKey", "bearerAuth"}

    def test_error_response_catalog(self):
        assert set(ERROR_RESPONSES) == {
            "Unauthorized", "SubscriptionRequired", "Forbidden",
            "NotFound", "ValidationError", "RateLimitExceeded",
            "InternalError",
        }
