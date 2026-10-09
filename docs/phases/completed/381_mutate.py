"""Phase 381's mutations: each breaks one thing the phase built, and the check beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/381_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 378's harness, as
380 used it: exact strings (each must occur once), one or more files per
mutation, the check run after clearing `__pycache__`, every file restored
whatever happens. Exits 1 if any mutation stays green. An argument runs only
the mutations whose name starts with it: `A` the alias (F156), `M` migration
086, `P` the parity check, `C` the census (F158), `G` Gate 14.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

RESOLVER = "src/motodiag/knowledge/vehicle_resolver.py"
LOADER = "src/motodiag/knowledge/loader.py"
MIGRATIONS = "src/motodiag/core/migrations.py"
DEPLOY = ".claude/skills/deploy/deploy.py"
CENSUS = "scripts/f158_census.py"
VIDEOS = "src/motodiag/api/routes/videos.py"
DIAGNOSE = "src/motodiag/cli/diagnose.py"
ELEC = "src/motodiag/knowledge/seed/knowledge/known_issues_scooter_electrical.json"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


MINE = pytest("tests/test_phase381_content_batch.py")
GATE14 = pytest("tests/test_phase258_gate14.py", "-k", "metropolitan or sym or ruckus")

MUTATIONS = [
    ("A1 the window ends at the cover's 2006", [(RESOLVER,
     '    ("Honda", "Metropolitan", 2002, 2007, "CHF50"),',
     '    ("Honda", "Metropolitan", 2002, 2006, "CHF50"),')], MINE),
    ("A2 the alias ignores the year", [(RESOLVER,
     "    if year is None:\n        return None\n", "")], MINE),
    ("A3 the tier SQL drops the alias", [(RESOLVER,
     "    also_model = dated_alias(resolved_make, resolved_model or model, year)",
     "    also_model = None")], MINE),
    ("A4 the video door drops the year", [(VIDEOS,
     "        limit=candidate_fetch_size(db_path), year=context.year,",
     "        limit=candidate_fetch_size(db_path),")], MINE),
    ("A5 diagnose drops the year", [(DIAGNOSE,
     "            limit=candidate_fetch_size(db_path), year=year,",
     "            limit=candidate_fetch_size(db_path),")], MINE),
    ("M1 086 overwrites a row edited since", [(LOADER,
     "        if held is None or held[0] != old:",
     "        if held is None:")], MINE),
    ("M2 the seed keeps F152's old sentence", [(ELEC,
     "The manual's cover reads 'CHF50/P/S', 'METROPOLITAN™' and '2002–2006', and its"
     " carburettor table also lists an 'After ’07 model' (p. 1-6).",
     "The manual prints the model only as CHF50, and it names no end year.")], MINE),
    ("M3 086 keeps F149's rows", [(MIGRATIONS,
     '            f"DELETE FROM known_issues WHERE row_key IN ({keys});",\n', "")], MINE),
    ("M4 the rollback restores rows a database never held", [(MIGRATIONS,
     '                   f" WHERE EXISTS (SELECT 1 FROM known_issues WHERE row_key ="\n'
     '                   f" {_sql_text(_RETIRED_SIBLING_086)});")',
     '                   ";")')], MINE),
    ("P1 parity ignores removed rows", [(DEPLOY,
     "             for key in removed if key in by_key]",
     "             for key in removed if False]")], MINE),
    ("C1 the census forgets corpus", [(CENSUS,
     '    "corpus": re.compile(r"\\bcorpus", re.I),\n', "")], MINE),
    ("C2 the census reads row keys", [(CENSUS,
     '    and r[1] not in SKIP_COLUMNS]', '    ]')], MINE),
    ("C3 logged answers count as content", [(CENSUS,
     'OPERATIONAL_TABLES = ("shops", "customer_notifications", "guidance_interactions")',
     'OPERATIONAL_TABLES = ("shops", "customer_notifications")')], MINE),
    ("G1 Gate 14 without the alias", [(RESOLVER,
     "    also_model = dated_alias(resolved_make, resolved_model or model, year)",
     "    also_model = None")], GATE14),
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
