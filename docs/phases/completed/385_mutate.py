"""Phase 385's mutations: each breaks the one entry or its pin, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/385_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 383's and 348's
harness: exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it.

E2 to E4 each run one control alone, so its red run is that control seen
failing: E2 the added token row, E3 the rebind, E4 the same column name in
another table.

No mutation reads the live database or reaches the network.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DEPLOY = ".claude/skills/deploy/deploy.py"
PIN = "tests/test_phase383_server_writes.py"
T385 = "tests/test_phase385_server_writes.py"
ENTRY = '"device_tokens": frozenset({"last_seen_at"})'


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


T_ASIDE = pytest(T385, "-k", "TestTheTokenColumnIsSetAside or same_user")
T_ADDED = pytest(T385, "-k", "TestTheControlsStillFail and added_row")
T_REBIND = pytest(T385, "-k", "TestTheControlsStillFail and rebind")
T_OTHER = pytest(T385, "-k", "TestTheControlsStillFail and other_table")
T_PIN = pytest(PIN, "-k", "test_the_list_is_exactly_this")

MUTATIONS = [
    ("E1 the entry removed",
     [(DEPLOY, ',\n                                            ' + ENTRY + '}', '}')], T_ASIDE),
    ("E2 the entry widened to WHOLE_TABLE (the added token row)",
     [(DEPLOY, ENTRY, '"device_tokens": WHOLE_TABLE')], T_ADDED),
    ("E3 the entry widened to last_seen_at and platform (the rebind)",
     [(DEPLOY, ENTRY, '"device_tokens": frozenset({"last_seen_at", "platform"})')], T_REBIND),
    ("E4 last_seen_at listed under the second table instead (another table)",
     [(DEPLOY, ENTRY, '"phones": frozenset({"last_seen_at"})')], T_OTHER),
    ("P1 the pin's literal without the new entry",
     [(PIN, ',\n                               "device_tokens": frozenset({"last_seen_at"})}',
       '}')], T_PIN),
]


def clear_caches() -> None:
    for top in ("src", "tests", ".claude/skills/deploy"):
        for d in (ROOT / top).rglob("__pycache__"):
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
