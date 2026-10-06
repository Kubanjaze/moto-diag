"""Phase 370's mutations: each undoes one thing the phase adds, and the
tests named beside it must go red.

M1 is the planted control the prompt asks for: a return to local time in
the API's own session writer.

Run from the repository root: `.venv/bin/python docs/phases/completed/370_mutate.py`
(moved from in_progress/ at close-out). 361's form: each mutation replaces one
exact string (which must occur once), runs its tests with `-B` after
clearing `__pycache__`, and restores the file whatever happens. Prints one
line per mutation and exits 1 if any stayed green.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
T = "tests/test_phase370_session_utc.py"
TESTS = [T]
REPO_ = "src/motodiag/core/session_repo.py"
STAMP = "src/motodiag/core/timestamps.py"
CLI = "src/motodiag/cli/diagnose.py"
API = "src/motodiag/api/routes/sessions.py"
REPORT = "src/motodiag/reporting/builders.py"
MEMORY = "src/motodiag/memory/compile.py"
MIGRATIONS = "src/motodiag/core/migrations.py"
PLUGIN = "tests/support/frozen_clock.py"
LOCAL = "datetime.now().isoformat()"

MUTATIONS = [
    ("M1 the API's session writer returns to local time (the planted control)", REPO_,
     "                utc_now(),\n                owner_user_id,\n",
     f"                {LOCAL},\n                owner_user_id,\n", TESTS),
    ("M2 create_session returns to local time", REPO_,
     "                utc_now(),\n                shop_id,\n",
     f"                {LOCAL},\n                shop_id,\n", TESTS),
    ("M3 update_session stamps local", REPO_,
     "    now = utc_now()\n    changed = False\n",
     f"    now = {LOCAL}\n    changed = False\n", TESTS),
    ("M4 add_symptom stamps local", REPO_,
     "(json.dumps(symptoms), utc_now(), session_id)",
     f"(json.dumps(symptoms), {LOCAL}, session_id)", TESTS),
    ("M5 add_fault_code stamps local", REPO_,
     "(json.dumps(codes), utc_now(), session_id)",
     f"(json.dumps(codes), {LOCAL}, session_id)", TESTS),
    ("M6 set_diagnosis stamps local", REPO_,
     "confidence or 0)\n    now = utc_now()\n",
     f"confidence or 0)\n    now = {LOCAL}\n", TESTS),
    ("M7 close_session stamps local", REPO_,
     "\"Session %d closed\", session_id)\n    now = utc_now()\n",
     f"\"Session %d closed\", session_id)\n    now = {LOCAL}\n", TESTS),
    ("M8 reopen_session stamps local", REPO_,
     "\"Session %d reopened\", session_id)\n    now = utc_now()\n",
     f"\"Session %d reopened\", session_id)\n    now = {LOCAL}\n", TESTS),
    ("M9 append_note's updated_at stamps local", REPO_,
     "{new_entry}\"\n\n    now = utc_now()\n",
     f"{{new_entry}}\"\n\n    now = {LOCAL}\n", TESTS),
    ("M10 the note's stamp loses its offset", REPO_,
     "datetime.now(timezone.utc).astimezone().isoformat(timespec=\"minutes\")",
     "datetime.now().isoformat(timespec=\"minutes\")", TESTS),
    ("M11 the month start leaves the stored format", REPO_,
     "    ).isoformat(timespec=\"milliseconds\")\n",
     "    ).isoformat()\n", TESTS),
    ("M12 utc_now returns naive local time", STAMP,
     "    return datetime.now(timezone.utc).isoformat(timespec=\"milliseconds\")\n",
     "    return datetime.now().isoformat(timespec=\"milliseconds\")\n", TESTS),
    ("M13 diagnose show prints the stored UTC string", CLI,
     "    s = local_display(str(ts))\n", "    s = str(ts)\n", TESTS),
    ("M14 diagnose list's Created column prints the stored string", CLI,
     "                _short_ts(s.get(\"created_at\")),\n",
     "                str(s.get(\"created_at\", \"\"))[:19],\n", TESTS),
    ("M15 diagnose list reads a typed date as UTC", CLI,
     "        parsed = parsed.astimezone()\n    return parsed.astimezone(timezone.utc)",
     "        parsed = parsed.replace(tzinfo=timezone.utc)\n    return parsed.astimezone(timezone.utc)",
     TESTS),
    ("M16 --until is not inclusive of the whole day", CLI,
     "        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999000)\n",
     "        pass\n", TESTS),
    ("M17 the report Timeline prints the stored string", REPORT,
     "(\"Created\", str(local_display(row.get(\"created_at\")) or \"—\")),",
     "(\"Created\", str(row.get(\"created_at\") or \"—\")),", TESTS),
    ("M18 client memory dates by the UTC day", MEMORY,
     "    return str(local_display(str(value)))[:10]\n",
     "    return str(value)[:10]\n", TESTS),
    ("M19 the API's ISO since keeps its own offset", API,
     "    return parsed.astimezone(timezone.utc).isoformat(timespec=\"milliseconds\")\n",
     "    return parsed.isoformat()\n", TESTS),
    ("M20 the API's Nd since leaves the stored format", API,
     "        return cutoff.isoformat(timespec=\"milliseconds\")\n",
     "        return cutoff.isoformat()\n", TESTS),
    ("M21 079 reads a SQLite default as local time", STAMP,
     "    if \" \" in value and \"T\" not in value:\n",
     "    if False:\n", TESTS),
    ("M22 079 has no post_apply", MIGRATIONS,
     "        post_apply=\"motodiag.core.timestamps:convert_session_times_079\",\n",
     "        post_apply=\"\",\n", TESTS),
    ("M23 079's rollback leaves created_at in UTC", MIGRATIONS,
     "             WHERE created_at LIKE '%+00:00';\n",
     "             WHERE 0;\n", TESTS),
    ("M24 the plugin does not freeze the clock", PLUGIN,
     "        importlib.import_module(name).datetime = frozen\n",
     "        pass\n", TESTS),
]


def run_tests(tests: list[str]) -> int:
    for base in (ROOT / "src", ROOT / "tests"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist",
         *tests],
        cwd=ROOT, capture_output=True, text=True,
    ).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].split()[0] in argv]
    every = sorted({t for m in chosen for t in m[4]})
    assert run_tests(every) == 0, "the tests are not green before mutating"
    survivors = []
    for name, rel, old, new, tests in chosen:
        path = ROOT / rel
        original = path.read_text()
        assert original.count(old) == 1, f"{name}: the text occurs {original.count(old)} times"
        try:
            path.write_text(original.replace(old, new))
            code = run_tests(tests)
        finally:
            path.write_text(original)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    assert run_tests(every) == 0, "the tests are not green after restoring"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
