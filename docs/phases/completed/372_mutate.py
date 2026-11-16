"""Phase 372's mutations: each breaks one guard the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/372_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 348's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`R` the routes, `O` the OpenAPI document, `E` the error map.

The wiring file runs first, so a mutation it sees stops the run early; the
route tests run after it. No mutation reads the live database or reaches
the network.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

A = "src/motodiag/api/"
RT, OA, ER = A + "routes/payments.py", A + "openapi.py", A + "errors.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


T = pytest("tests/test_phase372_wiring.py", "tests/test_phase372_payment_routes.py")
# The behaviour alone, for the mutations whose effect is an answer, not a text.
T_ROUTES = pytest("tests/test_phase372_payment_routes.py")

MUTATIONS = [
    # the routes
    ("R1 the membership check removed (the account read)",
     [(RT, "    require_shop_access(shop_id, user, db_path)\n", "")], T_ROUTES),
    ("R2 connect's permission dropped to manage_shop",
     [(RT, 'permission="manage_billing"', 'permission="manage_shop"')], T_ROUTES),
    ("R3 a start's permission dropped to membership (checkout)",
     [(RT, '    require_shop_access(shop_id, user, db_path, permission="manage_shop")\n'
           "    _require_invoice_at_shop(invoice_id, shop_id, db_path)\n"
           "    p = start_checkout(",
       "    require_shop_access(shop_id, user, db_path)\n"
       "    _require_invoice_at_shop(invoice_id, shop_id, db_path)\n"
       "    p = start_checkout(")], T_ROUTES),
    ("R4 the invoice's shop not checked",
     [(RT, "    if _invoice_shop_id(invoice_id, db_path) != shop_id:",
       "    if _invoice_shop_id(invoice_id, db_path) is None:")], T_ROUTES),
    ("R5 user_id not passed to the start (checkout)",
     [(RT, "start_checkout(invoice_id, user_id=user.id, db_path=db_path)",
       "start_checkout(invoice_id, db_path=db_path)")], T_ROUTES),
    ("R6 refresh=true ignored",
     [(RT, "    if refresh:\n", "    if False:\n")], T_ROUTES),
    ("R7 the 403 reference dropped from connect's responses",
     [(RT, "    responses={\n        **ERRORS,\n",
       "    responses={\n        **{k: v for k, v in ERRORS.items() if k != 403},\n")], T),
    # the OpenAPI document
    ("O1 a payments route added to PUBLIC_PATH_PREFIXES",
     [(OA, '    "/v1/share",\n)', '    "/v1/share",\n    "/v1/shop/{shop_id}/payments",\n)')], T),
    ("O2 payments missing from TAG_CATALOG",
     [(OA, '        "name": "payments",\n', '        "name": "card-payments",\n')], T),
    ("O3 payments missing from _ALWAYS_TIER_GATED_TAGS (no 402 envelope)",
     [(OA, '    "vehicles", "sessions", "payments",\n', '    "vehicles", "sessions",\n')], T),
    # the error map
    ("E1 the ConnectError row reverted (a paid invoice answers 400)",
     [(ER, '        (ConnectError, 409, "payment-refused", "Payment refused"),\n', "")],
     T_ROUTES),
    ("E2 the StripeUnavailable row reverted (Stripe down answers 500)",
     [(ER, '        (StripeUnavailable, 503, "stripe-unavailable",\n'
           '         "Stripe is unavailable"),\n', "")], T_ROUTES),
    ("E3 the LiveKeyRefused row reverted (a live key out of prod answers 500)",
     [(ER, '        (LiveKeyRefused, 503, "payments-not-configured",\n'
           '         "Payments are not configured on this server"),\n', "")], T_ROUTES),
]


def clear_caches() -> None:
    for d in (ROOT / "src").rglob("__pycache__"):
        for f in d.glob("*.pyc"):
            f.unlink()


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals = {}
        try:
            for rel, old, new in edits:
                path = ROOT / rel
                originals.setdefault(rel, path.read_text())
                current = path.read_text()
                assert current.count(old) == 1, \
                    f"{name}: the text occurs {current.count(old)} times in {rel}"
                path.write_text(current.replace(old, new))
            code = run(command)
        finally:
            for rel, text in originals.items():
                (ROOT / rel).write_text(text)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
