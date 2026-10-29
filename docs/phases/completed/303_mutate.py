"""Phase 303's mutations: each breaks one guard the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/303_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 392's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`P` passwords, `S` sessions, `D` deps, `R` the routes, `L` the live socket
and the logs, `C` the CLI, `K` the operator's K56.

No mutation reads the live database or reaches the network.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

A = "src/motodiag/"
PW, SR, AK = A + "auth/passwords.py", A + "auth/sessions_repo.py", A + "auth/api_key_repo.py"
DE, RT, LV = A + "auth/deps.py", A + "api/routes/auth.py", A + "api/routes/live.py"
SV, AKC, MW = A + "cli/serve.py", A + "cli/apikey.py", A + "api/middleware.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


T_PW = pytest("tests/test_phase303_passwords.py")
T_SR = pytest("tests/test_phase303_sessions_repo.py")
T_API = pytest("tests/test_phase303_auth_api.py")
T_TIER = pytest("tests/test_phase303_tier_for_session.py")
T_LIVE = pytest("tests/test_phase303_live_session.py")
T_LOG = pytest("tests/test_phase303_log_redaction.py")
T_CLI = pytest("tests/test_phase303_user_cli.py")
T_CALL = pytest("tests/test_phase303_caller_on_request.py")

MUTATIONS = [
    # passwords
    ("P1 the constant-time compare", [(PW, "    return hmac.compare_digest(digest, expected)",
                                       "    return digest == expected")], T_PW),
    ("P2 the minimum length", [(PW, "    if len(plain) < MIN_PASSWORD_LENGTH:", "    if False:")], T_PW),
    # sessions
    ("S1 the expiry check", [(SR, '        if now >= _expires(str(row["created_at"]), lifetime_days):',
                              "        if False:")], T_SR),
    ("S2 the revoked check", [(SR, '        if not row["is_active"] or not row["user_is_active"]:',
                               '        if not row["user_is_active"]:')], T_SR),
    ("S3 the active-user check", [(SR, '        if not row["is_active"] or not row["user_is_active"]:',
                                   '        if not row["is_active"]:')], T_SR),
    ("S4 the one-reason login (an inactive user is told so)",
     [(SR, '    if not user.get("is_active"):\n        return None',
       '    if not user.get("is_active"):\n        raise LoginFailedError("account deactivated")')],
     T_API),
    ("S5 the mds_ refusal in verify_api_key",
     [(AK, '    if not plaintext or not plaintext.startswith(("mdk_live_", "mdk_test_")):',
       "    if not plaintext:")], T_SR),
    ("S6 the lists and revokes are confined to sessions",
     [(SR, "_IS_SESSION = f\"substr(key_prefix, 1, {len(SESSION_PREFIX)}) = '{SESSION_PREFIX}'\"",
       '_IS_SESSION = "1 = 1"')], T_SR),
    # deps
    ("D1 the prefix dispatch in resolve_credential",
     [(DE, "    if plaintext.startswith(SESSION_PREFIX):", "    if False:")], T_API),
    ("D2 the session branch of resolve_tier (the tier rule)",
     [(DE, '    if credential.kind != "session":\n        return None',
       "    if True:\n        return None")], T_TIER),
    ("D3 the caller is not left on the request",
     [(DE, "        request.state.caller = Caller(key.user_id, key.kind, key.id)",
       "        pass")], T_CALL),
    ("D4 the limiter's tier is the user's own only",
     [(MW, "            tier = resolve_tier(key, db_path=db_path)",
       "            tier = None")], T_API),
    # the routes
    ("R1 the manage_users gate",
     [(RT, '    require_shop_permission(shop_id, caller.id, "manage_users", db_path=db_path)\n',
       "    pass\n")], T_API),
    ("R2 the reset leaves the member's sessions open",
     [(RT, "    revoked = revoke_user_sessions(user_id, db_path=db_path)", "    revoked = 0")], T_API),
    ("R3 a password change ends the calling session too",
     [(RT, '    keep = user.api_key_id if user.credential_kind == "session" else None',
       "    keep = None")], T_API),
    ("R4 logout takes a key", [(RT, '    if user.credential_kind != "session":\n        raise NotASessionError(',
                                '    if False:\n        raise NotASessionError(')], T_API),
    # the live socket and the logs
    ("L1 the socket takes a session from the query string",
     [(LV, "    if not plaintext or _session_in_query(websocket):", "    if not plaintext:")], T_LIVE),
    ("L2 the redaction filter only on uvicorn.access",
     [(SV, '    for name in ("uvicorn.access", "uvicorn.error"):', '    for name in ("uvicorn.access",):')],
     T_LOG),
    ("L3 the redaction filter replaces nothing",
     [(SV, '            record.args = tuple(\n                SESSION_TOKEN_RE.sub(REDACTED, a)',
       '            record.args = tuple(\n                a')], T_LOG),
    # the CLI
    ("C1 apikey list shows sessions", [(AKC, ') if k.kind == "api_key"]', ")]")], T_CLI),
    # the operator's K56
    ("K1 the reset takes an owner at any shop",
     [(RT, "    if _owner_anywhere(user_id, db_path):", "    if False:")], T_API),
    ("K2 the reset takes a member of another shop",
     [(RT, "        if other.shop_id != shop_id and not has_shop_permission(",
       "        if False and not has_shop_permission(")], T_API),
    ("K3 an unknown name skips the password check",
     [(SR, "    matched = verify_password(password, stored if has_password else DUMMY_HASH)",
       "    matched = has_password and verify_password(password, stored)")], T_SR),
    ("K4 expiry compared as date text",
     [(SR, '        if now >= _expires(str(row["created_at"]), lifetime_days):',
       '        if str(row["created_at"]) < (now - timedelta(days=lifetime_days)).isoformat():')],
     T_SR),
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
