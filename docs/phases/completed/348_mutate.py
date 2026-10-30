"""Phase 348's mutations: each breaks one guard the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/348_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 392's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`M` the middleware and the login, `S` the store, `G` the migration's
triggers, `R` the reader route, `C` the CLI.

No mutation reads the live database or reaches the network.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

A = "src/motodiag/"
MW, LOG, MIG = A + "api/middleware.py", A + "audit/log.py", A + "core/migrations.py"
RT, AUTH = A + "api/routes/audit.py", A + "api/routes/auth.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


T_MW = pytest("tests/test_phase348_audit_middleware.py")
T_LOG = pytest("tests/test_phase348_audit_log.py")
T_MIG = pytest("tests/test_phase348_migration.py")
T_API = pytest("tests/test_phase348_audit_api.py")
T_CLI = pytest("tests/test_phase348_audit_cli.py")

MUTATIONS = [
    # the middleware and the login
    ("M1 the method rule (a GET is recorded too)",
     [(MW, 'AUDITED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})',
       'AUDITED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE", "GET"})')], T_MW),
    ("M2 the query string is kept in the path",
     [(MW, "                    path=request.url.path,\n",
       "                    path=request.url.path + '?' + request.url.query,\n")], T_LOG),
    ("M3 a failed audit write fails the request",
     [(MW, "        except Exception:\n            audit_logger.exception(",
       "        except ZeroDivisionError:\n            audit_logger.exception(")], T_MW),
    ("M4 the login does not set the caller",
     [(AUTH, '    request.state.caller = Caller(row.user_id, "session", row.id)', "    pass")], T_MW),
    # the store
    ("S1 the prev_hash link (every row links to GENESIS)",
     [(LOG, "        prev = last[1] if last else GENESIS", "        prev = GENESIS")], T_LOG),
    ("S2 the order of HASHED_COLUMNS (method and path swapped)",
     [(LOG, '    "method", "path", "endpoint",', '    "path", "method", "endpoint",')], T_LOG),
    ("S3 verify_chain's comparison (the hash not recomputed)",
     [(LOG, "        if bad is None and (stored_prev != prev or "
            "row_hash(stored_prev, values) != stored_hash):",
       "        if bad is None and stored_prev != prev:")], T_LOG),
    ("S4 export's refusal (an existing file overwritten)",
     [(LOG, '    with open(out_path, "x", encoding="utf-8") as f:',
       '    with open(out_path, "w", encoding="utf-8") as f:')], T_LOG),
    # the migration's triggers
    ("G1 the UPDATE trigger is not created",
     [(MIG, "            CREATE TRIGGER IF NOT EXISTS audit_events_no_update\n"
            "                BEFORE UPDATE ON audit_events\n"
            "                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;\n",
       "")], T_MIG),
    ("G2 the DELETE trigger is not created",
     [(MIG, "            CREATE TRIGGER IF NOT EXISTS audit_events_no_delete\n"
            "                BEFORE DELETE ON audit_events\n"
            "                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;\n",
       "")], T_MIG),
    # the reader route
    ("R1 the manage_users gate",
     [(RT, '    require_shop_permission(shop_id, user.id, "manage_users", db_path=db_path)\n',
       "    pass\n")], T_API),
    ("R2 the shop filter",
     [(RT, "            conn, shop_id=shop_id, user_id=user_id,",
       "            conn, shop_id=None, user_id=user_id,")], T_API),
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
