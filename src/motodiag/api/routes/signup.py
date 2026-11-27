"""Self-serve sign-up and the password reset by email (Phase 329 prebuild).

The operator's answers of 2026-11-25: the form is on the website
(getmekno.com/signup); the app only signs in. Pay first. Emails go through
Resend once its key is in the settings file; until then the stand-in
sender. Three switches, all off: shops' sign-up (K141: the first 10 shops
are set up by hand, self-serve after them), individuals' sign-up (K150:
on when 329 ships) and the reset by email. A route, or a plan, whose
switch is off answers 404.

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
   welcome email. An individual's plan makes the login only.

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
    EmailNotConfigured,
    EmailSendError,
    address_check_email,
    get_email_sender,
    password_reset_email,
)
from motodiag.auth.one_time_codes import check_code, issue_code
from motodiag.auth.passwords import PasswordTooShort, hash_password
from motodiag.auth.sessions_repo import revoke_user_sessions
from motodiag.auth.signup_repo import (
    FORM_TIERS,
    SHOP_TIERS,
    SignupTier,
    create_signup,
    emails_sent_to,
    find_code,
    get_signup,
    mark_code_used,
    mark_verified,
    purge_stale,
    set_checkout_session,
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
#: Where Stripe's hosted checkout lives. The button page's post is answered
#: with a redirect there, and browsers hold a redirect to form-action too.
STRIPE_CHECKOUT_ORIGIN = "https://checkout.stripe.com"
#: The errors that mean "no email left the server".
SEND_FAILED = (EmailSendError, EmailNotConfigured)


def page_csp(settings: Settings) -> str:
    """The button pages' policy. Their posts are answered with a redirect to
    the website or to Stripe's checkout, so both are allowed form targets."""
    site = settings.signup_site_url.rstrip("/")
    return ("default-src 'none'; "
            f"form-action 'self' {site} {STRIPE_CHECKOUT_ORIGIN}; "
            "frame-ancestors 'none'")


def _over_cap(settings: Settings, email: str, db_path: str, now: float) -> bool:
    return emails_sent_to(email, now - 3600, db_path=db_path) >= \
        settings.signup_emails_per_address_per_hour


def _site(settings: Settings, page: str) -> str:
    return settings.signup_site_url.rstrip("/") + page


def _go(settings: Settings, page: str) -> RedirectResponse:
    return RedirectResponse(_site(settings, page), status_code=303)


def _problem(settings: Settings, why: str, where: str = "signup") -> RedirectResponse:
    return _go(settings, f"/{where}/problem/#{why}")


def _api_base(request: Request, settings: Settings) -> str:
    return (settings.public_base_url or str(request.base_url)).rstrip("/")


def _page(settings: Settings, title: str, action: str, code: str, fields: str,
          button: str) -> HTMLResponse:
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
    return HTMLResponse(body, headers={"Content-Security-Policy": page_csp(settings),
                                       "Cache-Control": "no-store"})


def _require(on: bool) -> None:
    if not on:
        raise HTTPException(status_code=404, detail="Not Found")


#: The website's form for each plan: Stripe's cancel goes back to it.
FORM_PAGES: dict[str, str] = {"individual": "/signup/individual/",
                              "shop": "/signup/", "company": "/signup/"}


def _tier_open(settings: Settings, tier: SignupTier) -> bool:
    if tier in SHOP_TIERS:
        return settings.self_serve_signup_enabled
    return settings.individual_signup_enabled


def _any_signup(settings: Settings) -> bool:
    return settings.self_serve_signup_enabled or settings.individual_signup_enabled


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
    _require(_any_signup(settings))
    now = time.time()
    purge_stale(now, db_path=db_path)
    if tier not in FORM_TIERS:
        return _problem(settings, "plan")
    plan: SignupTier = tier  # type: ignore[assignment]  # checked just above
    _require(_tier_open(settings, plan))
    # Bug fix #3: the username is kept as typed, never lowered. Sign-in
    # matches it exactly, so a name with capitals is refused here instead
    # of being stored in a case the person did not type.
    email, username = email.strip().lower(), username.strip()
    owner_name, shop_name = owner_name.strip(), shop_name.strip()
    if not EMAIL_RE.match(email) or len(email) > 254:
        return _problem(settings, "email")
    if not owner_name or len(owner_name) > 120:
        return _problem(settings, "name")
    if plan in SHOP_TIERS and (not shop_name or len(shop_name) > 120):
        return _problem(settings, "shop")
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
    if _over_cap(settings, email, db_path, now):
        return _problem(settings, "too-many")
    signup_id = create_signup(
        email=email, owner_name=owner_name, username=username,
        password_hash=password_hash,
        shop_name=shop_name if plan in SHOP_TIERS else None, tier=plan,
        terms_version=TERMS_VERSION, db_path=db_path,
    )
    issued = issue_code("verify_email", f"signup:{signup_id}", now=now)
    store_code(issued.record, db_path=db_path)
    link = f"{_api_base(request, settings)}/v1/signup/confirm?code={issued.code}"
    try:
        get_email_sender(settings.email_provider, settings).send(
            address_check_email(email, link))
    except SEND_FAILED as e:
        logger.error("sign-up %d: the address check was not sent: %s", signup_id, e)
        return _problem(settings, "later")
    logger.info("sign-up %d: address check sent", signup_id)
    return _go(settings, "/signup/check-email/")


@router.get("/signup/confirm")
def signup_confirm_page(
    code: str = "", settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    _require(_any_signup(settings))
    return _page(settings, "Confirm your email", "/v1/signup/confirm", code, "",
                 "Confirm and go to payment")


@router.post("/signup/confirm")
def signup_confirm(
    code: str = Form(""),
    settings: Settings = Depends(get_settings),
    db_path: str = Depends(get_db_path),
    provider: BillingProvider = Depends(get_provider),
) -> RedirectResponse:
    _require(_any_signup(settings))
    record = find_code(code, db_path=db_path)
    if record is None or not record.subject.startswith("signup:"):
        return _problem(settings, "link")
    signup = get_signup(int(record.subject.split(":", 1)[1]), db_path=db_path)
    if signup is None:
        return _problem(settings, "link")
    # A plan whose switch went off after its form was sent goes no further.
    _require(_tier_open(settings, signup.tier))
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
    # Bug fix #4: one sign-up, one payment. Paid already (or paid and stuck
    # for the operator): the paid page. A checkout already open: that same
    # checkout. Only one that expired unpaid makes way for a new one.
    if signup.stripe_subscription_id:
        return _go(settings, "/signup/paid/")
    try:
        if signup.stripe_checkout_session_id:
            prior = provider.retrieve_checkout_session(signup.stripe_checkout_session_id)
            if prior.get("status") == "complete":
                return _go(settings, "/signup/paid/")
            if prior.get("status") == "open" and prior.get("url"):
                return RedirectResponse(str(prior["url"]), status_code=303)
        checkout = provider.create_signup_checkout_session(
            signup.id, signup.email, signup.tier,
            success_url=_site(settings, "/signup/paid/"),
            cancel_url=_site(settings, FORM_PAGES[signup.tier]),
        )
    except BillingProviderError:
        logger.exception("sign-up %d: checkout could not be started", signup.id)
        return _problem(settings, "later")
    set_checkout_session(signup.id, checkout.session_id, db_path=db_path)
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
    now = time.time()
    if EMAIL_RE.match(email) and _over_cap(settings, email, db_path, now):
        logger.info("password reset: the address's hourly cap is reached")
    elif EMAIL_RE.match(email):
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT id FROM users WHERE lower(email) = ? AND is_active = 1 "
                "AND password_hash IS NOT NULL", (email,),
            ).fetchall()
        for row in rows:
            issued = issue_code("reset_password", f"user:{row['id']}", now=now)
            store_code(issued.record, db_path=db_path)
            link = (f"{_api_base(request, settings)}/v1/auth/password-reset/"
                    f"confirm?code={issued.code}")
            try:
                get_email_sender(settings.email_provider, settings).send(
                    password_reset_email(email, link))
            except SEND_FAILED as e:
                # The answer stays the same: it must not say whether the
                # address has a login.
                logger.error("password reset for user id=%d not sent: %s",
                             row["id"], e)
                continue
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
    return _page(settings, "Set a new password", "/v1/auth/password-reset/confirm", code,
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
