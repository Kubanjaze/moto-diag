"""Sending an email: the stand-in only (Phase 329 prebuild).

The server sends no email today (the 329 scope: "there is no sender in
`src/`"). Which service sends the address check and the reset, and from
which address, is the operator's answer at 329's Step 0 (question 3), so
this module holds only the shape every sender takes and the stand-in the
tests use. A real sender is added in 329, with its key typed into the
settings file by the operator, never in chat.

``get_email_sender("fake")`` is the stand-in. Any other name is refused
with :class:`EmailNotConfigured`, so nothing can send for real by accident.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Protocol, get_args

Provider = Literal["fake"]
PROVIDERS: tuple[Provider, ...] = get_args(Provider)


class EmailNotConfigured(RuntimeError):
    """No real email service is set up."""


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str


class EmailSender(Protocol):
    def send(self, email: Email) -> None: ...


@dataclass
class FakeEmailSender:
    """Keeps every email in ``outbox`` and sends nothing."""

    outbox: list[Email] = field(default_factory=list)

    def send(self, email: Email) -> None:
        if "@" not in email.to or email.to.strip() != email.to:
            raise ValueError(f"not an email address: {email.to!r}")
        self.outbox.append(email)


def get_email_sender(provider: str) -> EmailSender:
    if provider == "fake":
        return FakeEmailSender()
    raise EmailNotConfigured(
        f"no email service {provider!r}: only the stand-in exists until "
        "Phase 329 adds the operator's chosen service"
    )


def address_check_email(to: str, link: str) -> Email:
    """The sign-up's address check. Wording is a draft for 329."""
    return Email(to, "Confirm your email for Mekno", (
        "Someone, hopefully you, started a Mekno account with this address.\n\n"
        f"Confirm it here (the link works once, for 24 hours):\n{link}\n\n"
        "If this was not you, ignore this email and nothing happens.\n"
    ))


def password_reset_email(to: str, link: str) -> Email:
    """The password reset. Wording is a draft for 329."""
    return Email(to, "Reset your Mekno password", (
        "Someone asked to reset the password for your Mekno login.\n\n"
        f"Set a new one here (the link works once, for 1 hour):\n{link}\n\n"
        "If this was not you, ignore this email: your password stays as it is.\n"
    ))


def welcome_email(to: str, username: str, shop_name: Optional[str]) -> Email:
    """After the plan is paid: the login exists, and for a shop plan the
    shop (``shop_name``; None for an individual). A draft for 329."""
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
