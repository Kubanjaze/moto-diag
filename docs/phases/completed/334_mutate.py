"""Phase 334's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/334_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness, as
404 used it: exact strings (each must occur once), the tests run after
clearing `__pycache__`, every file restored whatever happens. Exits 1 if any
mutation stays green. An argument runs only the mutations whose name starts
with it: `S` the first switch, `A` the acceptance, `C` the checkout consent,
`T` the texts, `M` the migration.

No mutation reaches Stripe: the consent test builds the params without a
client.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

ACC = "src/motodiag/auth/terms_acceptance.py"
DEP = "src/motodiag/auth/deps.py"
RTE = "src/motodiag/api/routes/terms.py"
PRV = "src/motodiag/billing/providers.py"
MIG = "src/motodiag/core/migrations.py"
TXT = "docs/legal/terms.md"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_ROUTES = pytest("tests/test_phase334_terms_routes.py")
T_CONSENT = pytest("tests/test_phase334_checkout_consent.py")
T_TEXTS = pytest("tests/test_phase334_legal_texts.py")
T_MIG = pytest("tests/test_phase334_migration_091.py")

CHECK = (
    "    if get_settings().terms_required:\n"
    "        if (request.url.path not in terms.TERMS_EXEMPT_PATHS\n"
    "                and not terms.has_accepted(api_key.user_id, terms.TERMS_VERSION,\n"
    "                                           db_path)):\n"
    "            raise terms.TermsNotAcceptedError(\n"
    "                terms.not_accepted_message(terms.TERMS_VERSION))\n"
)
USER_TAIL = (
    "    request.state.caller = Caller(api_key.user_id, api_key.kind, api_key.id)\n"
    "    return AuthedUser(\n"
)
GET_ONE = (
    '    """The user\'s row for exactly this version, or None."""\n'
    "    with get_connection(db_path) as conn:\n"
    "        row = conn.execute(\n"
    '            "SELECT id, user_id, version, accepted_at FROM terms_acceptances "\n'
    '            "WHERE user_id = ? AND version = ?",\n'
)
GET_ANY = (
    '    """The user\'s row for exactly this version, or None."""\n'
    "    with get_connection(db_path) as conn:\n"
    "        row = conn.execute(\n"
    '            "SELECT id, user_id, version, accepted_at FROM terms_acceptances "\n'
    '            "WHERE user_id = ? AND ? IS NOT NULL",\n'
)

MUTATIONS = [
    ("S1 the exempt tuple emptied", [(ACC,
     '    "/v1/terms",\n    "/v1/terms/accept",\n    "/v1/auth/me",\n    "/v1/auth/logout",\n',
     "")], T_ROUTES),
    ("S2 the switch read inverted", [(DEP,
     "    if get_settings().terms_required:\n",
     "    if not get_settings().terms_required:\n")], T_ROUTES),
    ("S3 the check moved from require_api_key into get_current_user", [
        (DEP, CHECK, ""),
        (DEP, USER_TAIL, CHECK + USER_TAIL)], T_ROUTES),
    ("A1 has_accepted matches the user alone, any version", [(ACC,
     GET_ONE, GET_ANY)], T_ROUTES),
    ("A2 a stale version accepted", [(RTE,
     "    if body.version != terms.TERMS_VERSION:\n", "    if False:\n")], T_ROUTES),
    ("C1 consent_collection sent with the switch off", [(PRV,
     "    if terms_consent:\n", "    if True:\n")], T_CONSENT),
    ("T1 TERMS_VERSION out of step with the file's header", [(ACC,
     'TERMS_VERSION = "1.0"', 'TERMS_VERSION = "1.1"')], T_TEXTS),
    ("T2 the cap clause deleted from the terms", [(TXT,
     "a shop, for every claim together, is capped at what the shop paid Mekno in\n"
     "fees in the 12 months before the claim.\n",
     "a shop is capped.\n")], T_TEXTS),
    ("M1 the rollback leaves the table", [(MIG,
     "            DROP TABLE IF EXISTS terms_acceptances;\n", "")], T_MIG),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


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
                assert current.count(old) == 1, f"{name}: the text occurs {current.count(old)} times in {rel}"
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
