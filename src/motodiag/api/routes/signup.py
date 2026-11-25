"""Self-serve sign-up and the password reset by email (Phase 329 prebuild).

The operator's answers of 2026-11-25: the form is on the website
(getmekno.com/signup); the app only signs in. Pay first. Emails go through
Resend once its key is in the settings file; until then the stand-in
sender. Both switches ship off (K101: the first 10 shops are set up by
hand), and every route here is 404 while its switch is off.

The website runs no scripts, so these routes take plain form posts and
answer with a redirect (303) to one of the website's pages, or, for an
email's link, with one small page holding a button. A link only shows the
page; its code is spent by the button's post, so a mail scanner that opens
links does not use it up.

The sign-up, in order:

1. ``POST /v1/signup``: the form. A sign-up row, the password already
   hashed, and an email with a link (24 hours, once).
2. ``GET`` then ``POST /v1/signup/confirm``: the email is proven, and the
   browser goes to Stripe's checkout for the plan.
3. Stripe's subscription event, paid: the webhook makes the login, the
   shop, the membership and the terms acceptance
   (:func:`motodiag.auth.signup_repo.complete_signup`), and sends the
   welcome email.

The reset: ``POST /v1/auth/password-reset`` (an email address; the answer
is the same whether or not a login has it), then ``GET`` and ``POST
/v1/auth/password-reset/confirm`` (1 hour, once), which sets the password
and ends every session of that login.
"""

from __future__ import annotations

import html
import logging
import re
import time

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from motodiag.api.deps import get_db_path, get_settings
from motodiag.api.routes.billing import get_provider
from motodiag.auth.email_sender import (
    address_check_email,
    get_email_sender,
    password_reset_email,
)
from motodiag.auth.one_time_codes import check_code, issue_code
from motodiag.auth.passwords import PasswordTooShort, hash_password
from motodiag.auth.sessions_repo import revoke_user_sessions
from motodiag.auth.signup_repo import (
    SIGNUP_TIERS,
    create_signup,
    find_code,
    get_signup,
    mark_code_used,
    mark_verified,
    store_code,
    username_taken,
)
from motodiag.auth.terms_acceptance import TERMS_VERSION
from motodiag.auth.users_repo import update_user
from motodiag.billing.providers import BillingProvider, BillingProviderError
from motodiag.core.config import Settings
from motodiag.core.database import get_connection

logger = logging.getLogger(__name__)
# No tag: the routes are kept out of the published schema, so none is catalogued.
router = APIRouter(include_in_schema=False)

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PAGE_CSP = "default-src 'none'; form-action 'self'; frame-ancestors 'none'"


def _site(settings: Settings, page: str) -> str:
    return settings.signup_site_url.rstrip("/") + page


def _go(settings: Settings, page: str) -> RedirectResponse:
    return RedirectResponse(_site(settings, page), status_code=303)


def _problem(settings: Settings, why: str, where: str = "signup") -> RedirectResponse:
    return _go(settings, f"/{where}/problem/#{why}")


def _api_base(request: Request, settings: Settings) -> str:
    return (settings.public_base_url or str(request.base_url)).rstrip("/")


def _page(title: str, action: str, code: str, fields: str, button: str) -> HTMLResponse:
    body = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)} · Mekno</title></head><body>"
        f"<h1>{html.escape(title)}</h1>"
        f"<form method=\"post\" action=\"{html.escape(action)}\">"
        f"<input type=\"hidden\" name=\"code\" value=\"{html.escape(code)}\">"
        f"{fields}<p><button type=\"submit\">{html.escape(button)}</button></p>"
        "</form></body></html>"
    )
    return HTMLResponse(body, headers={"Content-Security-Policy": PAGE_CSP,
                                       "Cache-Control": "no-store"})


def _require(on: bool) -> None:
    if not on:
        raise HTTPException(status_code=404, detail="Not Found")


# ---------------------------------------------------------------- sign-up


@router.post("/signup")
def signup_form(
    request: Request,
    email: str = Form(""),
    owner_name: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
    shop_name: str = Form(""),
    tier: str = Form(""),
    accept_terms: str = Form(""),
    settings: Settings = Depends(get_settings),
    db_path: str = Depends(get_db_path),
) -> RedirectResponse:
    _require(settings.self_serve_signup_enabled)
    email, username = email.strip().lower(), username.strip().lower()
    owner_name, shop_name = owner_name.strip(), shop_name.strip()
    if not EMAIL_RE.match(email) or len(email) > 254:
        return _problem(settings, "email")
    if not owner_name or len(owner_name) > 120:
        return _problem(settings, "name")
    if not shop_name or len(shop_name) > 120:
        return _problem(settings, "shop")
    if tier not in SIGNUP_TIERS:
        return _problem(settings, "plan")
    if accept_terms != "yes":
        return _problem(settings, "terms")
    if not USERNAME_RE.match(username):
        return _problem(settings, "username")
    try:
        password_hash = hash_password(password)
    except PasswordTooShort:
        return _problem(settings, "password")
    if username_taken(username, db_path=db_path):
        return _problem(settings, "username-taken")
    signup_id = create_signup(
        email=email, owner_name=owner_name, username=username,
        password_hash=password_hash, shop_name=shop_name,
        tier=tier,  # type: ignore[arg-type]  # checked against SIGNUP_TIERS above
        terms_version=TERMS_VERSION, db_path=db_path,
    )
    issued = issue_code("verify_email", f"signup:{signup_id}", now=time.time())
    store_code(issued.record, db_path=db_path)
    link = f"{_api_base(request, settings)}/v1/signup/confirm?code={issued.code}"
    get_email_sender(settings.email_provider).send(address_check_email(email, link))
    logger.info("sign-up %d: address check sent", signup_id)
    return _go(settings, "/signup/check-email/")


@router.get("/signup/confirm")
def signup_confirm_page(
    code: str = "", settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    _require(settings.self_serve_signup_enabled)
    return _page("Confirm your email", "/v1/signup/confirm", code, "",
                 "Confirm and go to payment")


@router.post("/signup/confirm")
def signup_confirm(
    code: str = Form(""),
    settings: Settings = Depends(get_settings),
    db_path: str = Depends(get_db_path),
    provider: BillingProvider = Depends(get_provider),
) -> RedirectResponse:
    _require(settings.self_serve_signup_enabled)
    record = find_code(code, db_path=db_path)
    if record is None or not record.subject.startswith("signup:"):
        return _problem(settings, "link")
    signup = get_signup(int(record.subject.split(":", 1)[1]), db_path=db_path)
    if signup is None:
        return _problem(settings, "link")
    if signup.status == "completed":
        return _go(settings, "/signup/paid/")
    now = time.time()
    result = check_code(record, code, purpose="verify_email",
                        subject=record.subject, now=now)
    if result.ok:
        mark_code_used(result.record, db_path=db_path)
        mark_verified(signup.id, db_path=db_path)
    elif not (result.outcome == "used" and signup.status == "email_verified"
              and now < record.expires_at):
        # A used link may open the payment again (the payment was left
        # unfinished), within its lifetime; it changes nothing else.
        return _problem(settings, "link")
    try:
        checkout = provider.create_signup_checkout_session(
            signup.id, signup.email, signup.tier,
            success_url=_site(settings, "/signup/paid/"),
            cancel_url=_site(settings, "/signup/"),
        )
    except BillingProviderError:
        logger.exception("sign-up %d: checkout could not be started", signup.id)
        return _problem(settings, "later")
    return RedirectResponse(checkout.checkout_url, status_code=303)


# ---------------------------------------------------------------- password reset


@router.post("/auth/password-reset")
def password_reset_request(
    request: Request,
    email: str = Form(""),
    settings: Settings = Depends(get_settings),
    db_path: str = Depends(get_db_path),
) -> RedirectResponse:
    _require(settings.password_reset_email_enabled)
    email = email.strip().lower()
    if EMAIL_RE.match(email):
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT id FROM users WHERE lower(email) = ? AND is_active = 1 "
                "AND password_hash IS NOT NULL", (email,),
            ).fetchall()
        sender = get_email_sender(settings.email_provider)
        for row in rows:
            issued = issue_code("reset_password", f"user:{row['id']}", now=time.time())
            store_code(issued.record, db_path=db_path)
            link = (f"{_api_base(request, settings)}/v1/auth/password-reset/"
                    f"confirm?code={issued.code}")
            sender.send(password_reset_email(email, link))
            logger.info("password reset sent for user id=%d", row["id"])
    # The same answer whether or not a login has this address.
    return _go(settings, "/reset/sent/")


@router.get("/auth/password-reset/confirm")
def password_reset_page(
    code: str = "", settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    _require(settings.password_reset_email_enabled)
    fields = (
        "<p><label>New password (8 characters or more)<br>"
        "<input type=\"password\" name=\"new_password\" minlength=\"8\" required "
        "autocomplete=\"new-password\"></label></p>"
        "<p><label>The same again<br>"
        "<input type=\"password\" name=\"again\" minlength=\"8\" required "
        "autocomplete=\"new-password\"></label></p>"
    )
    return _page("Set a new password", "/v1/auth/password-reset/confirm", code,
                 fields, "Set the password")


@router.post("/auth/password-reset/confirm")
def password_reset_confirm(
    code: str = Form(""),
    new_password: str = Form(""),
    again: str = Form(""),
    settings: Settings = Depends(get_settings),
    db_path: str = Depends(get_db_path),
) -> RedirectResponse:
    _require(settings.password_reset_email_enabled)
    record = find_code(code, db_path=db_path)
    if record is None or not record.subject.startswith("user:"):
        return _problem(settings, "link", "reset")
    result = check_code(record, code, purpose="reset_password",
                        subject=record.subject, now=time.time())
    if not result.ok:
        return _problem(settings, "link", "reset")
    if new_password != again:
        return _problem(settings, "different", "reset")
    try:
        password_hash = hash_password(new_password)
    except PasswordTooShort:
        return _problem(settings, "password", "reset")
    user_id = int(record.subject.split(":", 1)[1])
    mark_code_used(result.record, db_path=db_path)
    update_user(user_id, {"password_hash": password_hash}, db_path=db_path)
    ended = revoke_user_sessions(user_id, db_path=db_path)
    logger.info("password reset done for user id=%d; %d sessions ended",
                user_id, ended)
    return _go(settings, "/reset/done/")
