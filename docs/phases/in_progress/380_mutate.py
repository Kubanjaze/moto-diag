"""Phase 380's mutations: each breaks one thing the phase built, and the check beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/380_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 378's harness:
exact strings (each must occur once), one or more files per mutation, the
check run after clearing `__pycache__`, every file restored whatever happens.
Exits 1 if any mutation stays green. An argument runs only the mutations
whose name starts with it: `K` the key (F129), `P` the parity check (2A),
`J` the junction (F142).
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

REPO = "src/motodiag/knowledge/issues_repo.py"
LOADER = "src/motodiag/knowledge/loader.py"
MODELS = "src/motodiag/knowledge/models.py"
MIGRATIONS = "src/motodiag/core/migrations.py"
DEPLOY = ".claude/skills/deploy/deploy.py"
CVT = "src/motodiag/knowledge/seed/knowledge/known_issues_cvt.json"


def pytest(*files: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *files]


KEYS = pytest("tests/test_phase380_row_keys.py")
PARITY = pytest("tests/test_phase380_seed_parity.py")
JUNCTION = pytest("tests/test_phase380_junction_per_make.py")

MUTATIONS = [
    ("K1 a seed entry loses its key", [(CVT,
     '    "key": "piaggio-what-a-scooter-cvt-is-in-the-makers-own-words-and-why",\n', "")], KEYS),
    ("K2 the loader's key is ignored", [(REPO,
     "        row_key = key or derived_row_key(make, model, title)",
     "        row_key = derived_row_key(make, model, title)")], KEYS),
    ("K3 085 keys every row from its prose", [(LOADER,
     '        key = keys.get((make or "", model or "", title)) or derived_row_key(make, model, title)',
     "        key = derived_row_key(make, model, title)")], KEYS),
    ("K4 085 keeps the prose identity index", [(MIGRATIONS,
     "            DROP INDEX IF EXISTS idx_known_issues_identity;\n"
     "            CREATE UNIQUE INDEX idx_known_issues_row_key ON known_issues(row_key);",
     "            CREATE UNIQUE INDEX idx_known_issues_row_key ON known_issues(row_key);")], KEYS),
    ("P1 the dry run skips the parity check", [(DEPLOY,
     "        probs += seed_parity(repo, copy, d, parity_build or _default_fresh_seed)\n", "")],
     PARITY),
    ("P2 the apply's fresh run skips it", [(DEPLOY,
     "        probs += seed_parity(repo, fresh, d, parity_build or _default_fresh_seed)\n", "")],
     PARITY),
    ("P3 parity compares no column", [(DEPLOY,
     "            if live[col] != seeded[col]:", "            if False:")], PARITY),
    ("J1 the lookup places nothing", [(MODELS,
     "                claim = lookup_marques(token, marques)", "                claim = set()")],
     JUNCTION),
    ("J2 a marque-prefixed token owns no bare name", [(MODELS,
     "        names.add(token.lower()[len(prefix):])", "        pass")], JUNCTION),
    ("J3 085 leaves the junction as it was", [(LOADER,
     "    sync_model_index(conn)\n    return keyed", "    return keyed")], KEYS),
    ("J4 the sync rewrites every pair", [(MODELS,
     "    conn.execute(\"ROLLBACK TO model_index_sync\")\n    conn.execute(\"RELEASE model_index_sync\")",
     "    conn.execute(\"RELEASE model_index_sync\")\n    return len(old - new), len(new - old)")],
     KEYS),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude"):
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
