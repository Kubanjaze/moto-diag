"""Sending an email: the stand-in, and Resend (Phase 329).

The operator's answer of 2026-11-25 (K152): "Resend, with a stand-in sender
until I type its key into the server's settings myself, never in chat."

``get_email_sender("fake")`` is the stand-in, which keeps what it would send
and sends nothing. ``get_email_sender("resend", settings)`` posts each email
to Resend's API with the key from the settings file. Any other name, or
Resend with no key, is refused with :class:`EmailNotConfigured`, so nothing
sends for real by accident. A send that fails raises
:class:`EmailSendError`, whose message names the status and Resend's error
name only: never the key, and never the email's text (which holds a link
with a one-time code).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, get_args

from motodiag import __version__
from motodiag.core.config import EmailProvider, Settings

Provider = EmailProvider
PROVIDERS: tuple[Provider, ...] = get_args(EmailProvider)

RESEND_URL = "https://api.resend.com/emails"
#: Cloudflare-fronted services refuse Python's default agent (409's bug
#: fix #2), so every request names Mekno.
USER_AGENT = f"mekno-server/{__version__}"
TIMEOUT_S = 10.0


class EmailNotConfigured(RuntimeError):
    """No real email service is set up."""


class EmailSendError(RuntimeError):
    """The email service did not take the email."""


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str


class EmailSender(Protocol):
    def send(self, email: Email) -> None: ...


def _check_address(to: str) -> None:
    if "@" not in to or to.strip() != to or "\n" in to:
        raise ValueError(f"not an email address: {to!r}")


@dataclass
class FakeEmailSender:
    """Keeps every email in ``outbox`` and sends nothing."""

    outbox: list[Email] = field(default_factory=list)

    def send(self, email: Email) -> None:
        _check_address(email.to)
        self.outbox.append(email)


#: (request) -> (status, body bytes). The tests replace it; no test reaches
#: the network.
Transport = Callable[[urllib.request.Request], tuple[int, bytes]]


def urllib_transport(req: urllib.request.Request) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 (fixed https URL)
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as e:
        return int(e.code), e.read() or b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise EmailSendError(f"Resend could not be reached: {type(e).__name__}") from None


@dataclass
class ResendEmailSender:
    """One POST to Resend's ``/emails`` per email."""

    api_key: str = field(repr=False)
    sender: str
    reply_to: Optional[str] = None
    transport: Transport = urllib_transport

    def request(self, email: Email) -> urllib.request.Request:
        payload: dict[str, Any] = {"from": self.sender, "to": [email.to],
                                   "subject": email.subject, "text": email.text}
        if self.reply_to:
            payload["reply_to"] = self.reply_to
        return urllib.request.Request(
            RESEND_URL, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json",
                     "User-Agent": USER_AGENT},
        )

    def send(self, email: Email) -> None:
        _check_address(email.to)
        status, raw = self.transport(self.request(email))
        if 200 <= status < 300:
            return
        name = ""
        try:
            parsed = json.loads(raw.decode("utf-8") or "{}")
            if isinstance(parsed, dict):
                name = str(parsed.get("name") or "")[:60]
        except (ValueError, UnicodeDecodeError):
            pass
        raise EmailSendError(f"Resend answered {status}" + (f" ({name})" if name else ""))


def get_email_sender(provider: str, settings: Optional[Settings] = None) -> EmailSender:
    if provider == "fake":
        return FakeEmailSender()
    if provider == "resend":
        if settings is None or not settings.resend_api_key:
            raise EmailNotConfigured(
                "email_provider is 'resend' but MOTODIAG_RESEND_API_KEY is not set")
        return ResendEmailSender(api_key=settings.resend_api_key,
                                 sender=settings.email_from,
                                 reply_to=settings.email_reply_to or None)
    raise EmailNotConfigured(
        f"no email service {provider!r}: the services are {PROVIDERS}")


def address_check_email(to: str, link: str) -> Email:
    """The sign-up's address check."""
    return Email(to, "Confirm your email for Mekno", (
        "Someone, hopefully you, started a Mekno account with this address.\n\n"
        f"Confirm it here (the link works once, for 24 hours):\n{link}\n\n"
        "If this was not you, ignore this email and nothing happens.\n"
    ))


def password_reset_email(to: str, link: str) -> Email:
    """The password reset."""
    return Email(to, "Reset your Mekno password", (
        "Someone asked to reset the password for your Mekno login.\n\n"
        f"Set a new one here (the link works once, for 1 hour):\n{link}\n\n"
        "If this was not you, ignore this email: your password stays as it is.\n"
    ))


def welcome_email(to: str, username: str, shop_name: Optional[str]) -> Email:
    """After the plan is paid: the login exists, and for a shop plan the
    shop (``shop_name``; None for an individual)."""
    if shop_name is None:
        return Email(to, "Your Mekno account is ready", (
            "Your account is set up and its plan is paid.\n\n"
            f"Sign in to the Mekno app with the username {username} and the "
            "password you chose.\n\n"
            "Questions: reply to this email.\n"
        ))
    return Email(to, "Your Mekno shop is ready", (
        f"{shop_name} is set up and its plan is paid.\n\n"
        f"Sign in to the Mekno app with the username {username} and the "
        "password you chose. From the app you can add your mechanics.\n\n"
        "Questions: reply to this email.\n"
    ))


def stuck_signup_email(to: str, signup_id: int, reason: str) -> Email:
    """To the support address: a paid sign-up that could not be completed,
    for the operator to settle and refund by hand (Phase 329)."""
    return Email(to, f"A paid Mekno sign-up needs you (sign-up {signup_id})", (
        f"Sign-up {signup_id} was paid, but its account could not be made:\n"
        f"{reason}\n\n"
        "Settle it by hand, and refund it in Stripe if it cannot be finished.\n"
    ))
