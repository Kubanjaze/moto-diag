"""F64 — the public base URL guard.

Share links are minted from ``MOTODIAG_PUBLIC_BASE_URL``. A wrong value
fails INVISIBLY to the shop: minting succeeds, the mechanic sends the
link, and only the customer discovers it does not resolve. That
asymmetry is why this is enforced at startup rather than documented in a
runbook.
"""

from __future__ import annotations

import pytest

from motodiag.core.config import Environment
from motodiag.core.public_url import (
    check_public_base_url,
    has_blocking_problem,
)


def blocks(url: str, env: Environment) -> bool:
    return has_blocking_problem(check_public_base_url(url, env))


class TestProductionRefusesUnreachableHosts:
    @pytest.mark.parametrize("url", [
        "",                                # falls back to the Host header
        "http://10.0.0.147:8000",          # RFC1918 — the Phase 204 gate value
        "http://192.168.1.50:8000",
        "http://172.16.4.4:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://macbook.local",           # mDNS, LAN-only
        "http://100.80.109.103:8000",      # CGNAT, where Tailscale lives
    ])
    def test_blocks_in_prod(self, url):
        assert blocks(url, Environment.PROD), (
            f"{url!r} is not reachable by a customer and must not start"
        )

    @pytest.mark.parametrize("url", [
        "https://app.motodiag.com",
        "https://motodiag.example.co.uk/",
    ])
    def test_allows_a_real_public_https_origin(self, url):
        assert not blocks(url, Environment.PROD)


class TestDevStaysWorkable:
    """Local work must not be blocked — the same findings become warnings."""

    @pytest.mark.parametrize("url", [
        "", "http://10.0.0.147:8000", "http://localhost:8000",
    ])
    def test_warns_but_does_not_block(self, url):
        problems = check_public_base_url(url, Environment.DEV)
        assert problems, "a developer should still be told"
        assert not has_blocking_problem(problems)


class TestTailscaleIsTheTrap:
    """A `.ts.net` name resolves in PUBLIC DNS, so every string-level
    check passes — but it routes only inside the tailnet. This is the
    exact state the Phase 204 gate ran in, and the reason a naive
    "is it a real hostname?" test would have been useless."""

    def test_tailnet_name_blocks_in_prod(self):
        assert blocks(
            "https://kerwyns-macbook-air.taila45995.ts.net", Environment.PROD,
        )

    def test_the_message_names_funnel_as_the_way_out(self):
        problems = check_public_base_url(
            "https://box.tailnet.ts.net", Environment.PROD,
        )
        assert any("Funnel" in p.remedy for p in problems)


class TestSchemeAndShape:
    def test_plain_http_blocks_in_prod_even_on_a_public_host(self):
        assert blocks("http://app.motodiag.com", Environment.PROD)

    def test_non_http_scheme_is_always_an_error(self):
        # Not environment-dependent: this can never be right.
        assert blocks("ftp://app.motodiag.com", Environment.DEV)

    def test_a_path_on_the_base_url_warns(self):
        problems = check_public_base_url(
            "https://app.motodiag.com/api", Environment.DEV,
        )
        assert any("path" in p.message for p in problems)

    def test_a_bare_trailing_slash_is_fine(self):
        assert not check_public_base_url(
            "https://app.motodiag.com/", Environment.PROD,
        )
