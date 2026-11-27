"""Phase 329: break each guard the build added, one at a time, and show a
test goes red. Run from the repository root on a clean tree; every file is
restored after its mutation."""
import os
import subprocess
import sys

TESTS = ["tests/test_phase329_resend_and_limits.py", "tests/test_phase329_signup_flow.py",
         "tests/test_phase408_site.py"]
MUTS = [
    ("cap dropped", "src/motodiag/api/routes/signup.py",
     "    if _over_cap(settings, email, db_path, now):\n        return _problem(settings, \"too-many\")\n", ""),
    ("reset cap dropped", "src/motodiag/api/routes/signup.py",
     "    if EMAIL_RE.match(email) and _over_cap(settings, email, db_path, now):",
     "    if False:"),
    ("purge not run on the form", "src/motodiag/api/routes/signup.py",
     "    purge_stale(now, db_path=db_path)\n", ""),
    ("purge deletes a paid sign-up", "src/motodiag/auth/signup_repo.py",
     "            \"AND stripe_subscription_id IS NULL AND user_id IS NULL \"\n", ""),
    ("company back on the form", "src/motodiag/auth/signup_repo.py",
     'FORM_TIERS: tuple[SignupTier, ...] = ("individual", "shop")',
     'FORM_TIERS: tuple[SignupTier, ...] = ("individual", "shop", "company")'),
    ("checkout not a form target", "src/motodiag/api/routes/signup.py",
     "f\"form-action 'self' {site} {STRIPE_CHECKOUT_ORIGIN}; \"", "\"form-action 'self'; \""),
    ("site not a redirect target", "site/_headers",
     "form-action https://api.getmekno.com https://getmekno.com\n\n",
     "form-action https://api.getmekno.com\n\n"),
    ("cancel to the shops' form", "src/motodiag/api/routes/signup.py",
     "cancel_url=_site(settings, FORM_PAGES[signup.tier])", "cancel_url=_site(settings, \"/signup/\")"),
    ("prod starts with resend and no key", "src/motodiag/api/app.py",
     "        and not app_settings.resend_api_key\n", "        and False\n"),
    ("key in the error", "src/motodiag/auth/email_sender.py",
     "raise EmailSendError(f\"Resend answered {status}\" + (f\" ({name})\" if name else \"\"))",
     "raise EmailSendError(f\"Resend answered {status} {raw!r} {self.api_key}\")"),
    ("form fails open on a send error", "src/motodiag/api/routes/signup.py",
     "        return _problem(settings, \"later\")\n    logger.info(\"sign-up %d: address check sent\"",
     "        pass\n    logger.info(\"sign-up %d: address check sent\""),
    ("welcome failure fails the event", "src/motodiag/billing/webhook_handlers.py",
     "            logger.error(\"sign-up %d: the welcome email was not sent: %s\",\n                         signup_id, mail_error)\n",
     "            raise\n"),
    ("stuck sign-up not kept", "src/motodiag/billing/webhook_handlers.py",
     "            mark_paid(signup_id, sub_id, db_path=db_path)\n", "            pass\n"),
    ("no user agent", "src/motodiag/auth/email_sender.py",
     "                     \"User-Agent\": USER_AGENT},", "                     },"),
]
red = 0
for name, path, a, b in MUTS:
    orig = open(path, encoding="utf-8").read()
    assert orig.count(a) == 1, name
    try:
        open(path, "w", encoding="utf-8").write(orig.replace(a, b))
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                            *TESTS], env=dict(os.environ, PYTHONUTF8="1"),
                           capture_output=True, text=True)
    finally:
        open(path, "w", encoding="utf-8").write(orig)
    verdict = "RED" if r.returncode != 0 else "survived"
    red += verdict == "RED"
    print(name, verdict, flush=True)
print(f"\n{red}/{len(MUTS)} red")
