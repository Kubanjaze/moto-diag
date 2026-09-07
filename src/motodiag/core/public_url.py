"""F64 — validation for the customer-facing public base URL.

``MOTODIAG_PUBLIC_BASE_URL`` is baked into every share link minted by
``POST /v1/reports/session/{id}/share``. Getting it wrong is uniquely
nasty because **the failure is invisible to the shop**: minting succeeds,
the mechanic sees a link and sends it, and only the customer discovers it
does not resolve. Nothing in the app or the logs says otherwise.

That asymmetry is why this is a startup check rather than a runbook note.
A wrong value should stop a production deployment, not surface weeks
later as "customers say the link is broken".

Surfaced during the Phase 204 gate, where the value was pointed at a LAN
address so the phone could reach it after a VPN conflict wedged the
tailnet listener — correct for the gate, catastrophic if shipped.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Literal, Optional
from urllib.parse import urlparse

from motodiag.core.config import Environment

Severity = Literal["error", "warning"]

#: Hostnames that are never reachable by a customer, whatever the DNS.
_LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class PublicUrlProblem:
    severity: Severity
    message: str
    remedy: str

    def render(self) -> str:
        return f"[{self.severity.upper()}] {self.message}\n    → {self.remedy}"


def _host_is_unreachable_publicly(host: str) -> Optional[str]:
    """Return a reason when ``host`` can never be reached by a customer.

    Covers loopback, RFC1918, link-local and the carrier-grade NAT range
    100.64.0.0/10 — the last of which matters because Tailscale addresses
    live there and look deceptively like ordinary public IPs.
    """
    lowered = host.lower()
    if lowered in _LOCAL_HOSTNAMES:
        return f"{host!r} is a loopback address"
    if lowered.endswith(".local"):
        return f"{host!r} is an mDNS/Bonjour name, resolvable only on the LAN"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return None  # a real hostname; DNS is someone else's problem
    if ip.is_loopback:
        return f"{host} is a loopback address"
    if ip.is_link_local:
        return f"{host} is link-local"
    if ip.is_private:
        # Python folds 100.64.0.0/10 (CGNAT, where Tailscale lives) into
        # is_private, which is what we want: a tailnet address is not
        # reachable by a customer either.
        return f"{host} is a private address, reachable only from that network"
    return None


def check_public_base_url(
    url: str,
    env: Environment = Environment.DEV,
) -> list[PublicUrlProblem]:
    """Validate the configured public base URL for ``env``.

    In production every finding is an ``error``; in dev and test the same
    findings are ``warning``s, because pointing at localhost or a LAN
    address is the normal and correct way to work locally.
    """
    prod = env == Environment.PROD
    sev: Severity = "error" if prod else "warning"
    problems: list[PublicUrlProblem] = []

    if not url.strip():
        return [PublicUrlProblem(
            severity=sev,
            message=(
                "MOTODIAG_PUBLIC_BASE_URL is not set, so share links fall "
                "back to the request's own Host header"
            ),
            remedy=(
                "Set it to the public origin customers will reach, e.g. "
                "https://app.example.com. The fallback is wrong behind any "
                "proxy that rewrites Host."
            ),
        )]

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        problems.append(PublicUrlProblem(
            severity="error",
            message=f"scheme {parsed.scheme!r} is not http or https",
            remedy="Use an absolute https:// origin.",
        ))
        return problems

    if parsed.scheme != "https":
        problems.append(PublicUrlProblem(
            severity=sev,
            message="share links would be served over plain http",
            remedy=(
                "Use https. The page names a customer, their bike and its "
                "diagnosis, and iOS App Transport Security blocks plain "
                "http to non-private hosts regardless."
            ),
        ))

    host = parsed.hostname or ""
    reason = _host_is_unreachable_publicly(host)
    if reason is not None:
        problems.append(PublicUrlProblem(
            severity=sev,
            message=f"share links would point at {url} — {reason}",
            remedy=(
                "Point it at a publicly resolvable hostname. Verify by "
                "opening a minted link from a device on a DIFFERENT "
                "network (cellular, not the shop wifi)."
            ),
        ))

    # Tailscale names are the trap this check exists for. They resolve
    # in PUBLIC DNS, so every string-level test passes — but they route
    # only inside the tailnet unless Funnel is explicitly enabled. A
    # customer on cellular gets a timeout, and the shop sees nothing
    # wrong. This is exactly the state the Phase 204 gate ran in.
    if host.lower().endswith(".ts.net"):
        problems.append(PublicUrlProblem(
            severity=sev,
            message=(
                f"{host} is a Tailscale name: it resolves in public DNS "
                "but routes only inside your tailnet"
            ),
            remedy=(
                "Either enable Tailscale Funnel for this service, or use "
                "an ordinary public host. Without Funnel a customer off "
                "the tailnet gets a timeout and the shop gets no signal."
            ),
        ))

    if parsed.path not in ("", "/"):
        problems.append(PublicUrlProblem(
            severity="warning",
            message=f"base URL carries a path ({parsed.path!r})",
            remedy=(
                "Share URLs are built by concatenation, so a path here "
                "produces links like <base><path>/v1/share/<token>."
            ),
        ))

    return problems


def has_blocking_problem(problems: list[PublicUrlProblem]) -> bool:
    return any(p.severity == "error" for p in problems)
