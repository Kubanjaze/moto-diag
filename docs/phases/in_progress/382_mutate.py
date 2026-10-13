"""Phase 382's mutations: each breaks one thing the phase built, and the check beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/382_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 381's harness:
exact strings (each must occur once), the check run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`W` where live is, `U` the sync refusal, `D` deploy.py, `S` source-transmission,
`T` the suite's guards, `O` the server's files.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

LIVE = ".claude/skills/deploy/live.py"
DEPLOY = ".claude/skills/deploy/deploy.py"
VERIFY = ".claude/skills/closeout/verify_phase.sh"
CENSUS = ".claude/skills/source-transmission/census.py"
ACQUIRE = ".claude/skills/source-transmission/acquire.py"
ORCH = ".claude/skills/source-transmission/orchestrate.py"
CONFTEST = "tests/conftest.py"
UNIT = "ops/desktop/motodiag-api.service"
TASK = "ops/desktop/motodiag-wsl-boot.xml"
WSLCONFIG = "ops/desktop/wslconfig"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


MINE = pytest("tests/test_phase382_live_location.py")
WIDTH = pytest("tests/test_phase382_suite_width.py")

MUTATIONS = [
    ("W1 a null live is not refused", [(LIVE,
     '    if not entry.get("live"):', '    if False:')], MINE),
    ("W2 a missing file is not refused", [(LIVE,
     "    if not cfg.is_file():", "    if False:")], MINE),
    ("W3 a missing path is not refused", [(LIVE,
     "    if not path.is_file():", "    if False:")], MINE),
    ("U1 a Windows drive passes", [(LIVE,
     "parts[1] == \"mnt\" and len(parts[2]) == 1", "False")], MINE),
    ("U2 OneDrive passes", [(LIVE,
     'SYNC_MARKERS = ("OneDrive", ', "SYNC_MARKERS = (")], MINE),
    ("D1 dryrun falls back to the checkout's copy", [(DEPLOY,
     "    db = db or L.where()\n    L.unsynced(backups)\n    scope_file",
     '    db = db or ROOT / "data" / "motodiag.db"\n    L.unsynced(backups)\n    scope_file')], MINE),
    ("D2 a refusal escapes main as a traceback", [(DEPLOY,
     "    except L.LiveElsewhere as e:\n        print(f\"REFUSED: {e}\", file=sys.stderr)\n        return L.REFUSED\n",
     "    except KeyboardInterrupt:\n        raise\n")], MINE),
    ("D3 backup ignores a synced folder", [(DEPLOY,
     "    L.unsynced(backups)\n    backups.mkdir(parents=True, exist_ok=True)\n    bk = backups / f\"motodiag_{label}",
     "    backups.mkdir(parents=True, exist_ok=True)\n    bk = backups / f\"motodiag_{label}")], MINE),
    ("D4 backup keeps everything", [(DEPLOY,
     '    print("backup:", bk, "removed by retain-5:", retain(backups))\n    print("sha256:"',
     '    print("backup:", bk)\n    print("sha256:"')], MINE),
    ("D5 verify_phase check 8 passes a refusal", [(VERIFY,
     '  echo "  CHECK 8 FAILED: live is not on this machine (live.py exit 4)"\n  FAILED=1',
     '  echo "  live is not on this machine (live.py exit 4)"')], MINE),
    ("S1 census reads the checkout's copy", [(CENSUS,
     "        db = pathlib.Path(named) if named else live_db()",
     '        db = pathlib.Path(named) if named else REPO / "data" / "motodiag.db"')], MINE),
    ("S2 acquire reads the checkout's copy", [(ACQUIRE,
     "    db = db or C.live_db()", '    db = db or C.REPO / "data" / "motodiag.db"')], MINE),
    ("S3 orchestrate does not refuse up front", [(ORCH,
     "        C.live_db()  # every batch", "        pass  # every batch")], MINE),
    ("T1 the suite honours a DB path naming live", [(CONFTEST,
     '    del os.environ["MOTODIAG_DB_PATH"]', "    pass")], MINE),
    ("T2 the suite reads the terminal width", [(CONFTEST,
     'os.environ["COLUMNS"] = "80"', "pass")], WIDTH),
    ("O1 the unit migrates at start", [(UNIT,
     " --skip-migrations\n", "\n")], MINE),
    ("O2 the unit binds every interface", [(UNIT,
     "--host 127.0.0.1", "--host 0.0.0.0")], MINE),
    ("O5 the unit starts with no live database", [(UNIT,
     "ConditionPathExists=/home/lilcu/motodiag/live/motodiag.db\n", "")], MINE),
    ("O6 sudo opens every systemctl verb", [("ops/desktop/install_sudoers.sh",
     ", /usr/bin/systemctl restart motodiag-api.service\n",
     ", /usr/bin/systemctl restart motodiag-api.service, /usr/bin/systemctl *\n")], MINE),
    ("O3 the task waits for a sign-in", [(TASK,
     "<LogonType>S4U</LogonType>", "<LogonType>InteractiveToken</LogonType>")], MINE),
    ("O4 WSL idles the VM out", [(WSLCONFIG,
     "vmIdleTimeout=-1", "vmIdleTimeout=60000")], MINE),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude", ROOT / "scripts"):
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
