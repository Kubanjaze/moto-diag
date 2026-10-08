"""Phase 379's mutations: each breaks one fix, and the check beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/379_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 378's harness:
exact strings (each must occur once), one or more files per mutation, the
check run after clearing `__pycache__`, every file restored whatever happens.
Exits 1 if any mutation stays green. An argument runs only the mutations
whose name starts with it, one letter per finding.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DEPLOY = ".claude/skills/deploy/deploy.py"
VERIFY = ".claude/skills/closeout/verify_phase.sh"
WHOLETREE = ".claude/skills/closeout/wholetree.py"
REGISTRY = "src/motodiag/vehicles/registry.py"
TIMESTAMPS = "src/motodiag/core/timestamps.py"
RECORDER = "src/motodiag/hardware/recorder.py"
DRIFT = "src/motodiag/advanced/drift.py"
LOOKUP = "src/motodiag/knowledge/transmission.py"
ROWS = "src/motodiag/knowledge/prompt_rows.py"
WORKER = "src/motodiag/media/analysis_worker.py"
VIDEOS = "src/motodiag/api/routes/videos.py"


def pytest(*files: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *files]


MUTATIONS = [
    # F197
    ("A1 verify-live exits 0 on a mismatch", [(DEPLOY,
     "    return 3 if gaps else 0", "    return 0")],
     pytest("tests/test_phase379_verify_live_fails.py")),
    ("A2 check 8 ignores verify-live's exit", [(VERIFY,
     "    FAILED=1\n", "    :\n")], pytest("tests/test_phase379_verify_live_fails.py")),
    ("A3 the later-migration cause is never named", [(DEPLOY,
     "            if phase_head is not None and live_head is not None and live_head > phase_head:",
     "            if False:")], pytest("tests/test_phase379_verify_live_fails.py")),
    # F176
    ("B1 garage remove deletes without asking what names the bike", [(REGISTRY,
     "    if dependents:\n        raise VehicleInUse(vehicle_id, dependents)",
     "    if False:\n        raise VehicleInUse(vehicle_id, dependents)")],
     pytest("tests/test_phase379_garage_remove.py")),
    ("B2 NO ACTION tables are not counted", [(REGISTRY,
     'fk[6] not in ("RESTRICT", "NO ACTION")', 'fk[6] not in ("RESTRICT",)')],
     pytest("tests/test_phase379_garage_remove.py")),
    # F193
    ("C1 the recorder compares the typed text again", [(RECORDER,
     "            params.append(column_cutoff(since))", "            params.append(since)")],
     pytest("tests/test_phase379_sensor_windows.py")),
    ("C2 drift compares the typed text again", [(DRIFT,
     "    since, until = column_cutoff(since), column_cutoff(until)\n", "")],
     pytest("tests/test_phase379_sensor_windows.py")),
    ("C3 the bound carries a fraction, so a sample on the second is missed", [(TIMESTAMPS,
     '.strftime("%Y-%m-%dT%H:%M:%S+00:00")', '.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")')],
     pytest("tests/test_phase379_sensor_windows.py")),
    # F154
    ("D1 no Fiddle 50 entry", [(LOOKUP,
     '    _E("SYM", "Fiddle 50", CVT, ("fiddle 50", "fiddle50"),',
     '    _E("SYM", "Fiddle 50", CVT, ("fiddle 5o",),')],
     pytest("tests/test_phase379_lookup_and_relevance.py")),
    # F155
    ("E1 plurals are not made singular", [(ROWS,
     "    return {_singular(t) for t in _TOKEN.findall((text or \"\").lower()) if t not in _STOP}",
     "    return {t for t in _TOKEN.findall((text or \"\").lower()) if t not in _STOP}")],
     pytest("tests/test_phase379_lookup_and_relevance.py")),
    ("E2 'ies' is not 'y'", [(ROWS,
     '        return token[:-3] + "y"', '        return token[:-1]')],
     pytest("tests/test_phase379_lookup_and_relevance.py")),
    # F131
    ("F1 an entry's own canonical name is not matched", [(LOOKUP,
     "        if _alias_match(entry.make, model, (*entry.aliases, entry.canonical)):",
     "        if _alias_match(entry.make, model, entry.aliases):")],
     pytest("tests/test_phase379_lookup_and_relevance.py")),
    # F140: the check is the test itself; its planted control is in the file.
    # F173
    ("H1 the whole output is not kept", [(WHOLETREE,
     '    log.write_text(proc.stdout + ("\\n" + proc.stderr if proc.stderr else ""), encoding="utf-8")',
     '    log.write_text(proc.stdout[-1500:], encoding="utf-8")')],
     pytest("tests/test_phase379_wholetree_output.py")),
    ("H2 only the last lines are printed", [(WHOLETREE,
     '        print("\\n".join(ln for ln in lines if ln.startswith(("FAILED", "ERROR"))))',
     '        print("\\n".join(lines[-15:]))')],
     pytest("tests/test_phase379_wholetree_output.py")),
    # F144
    ("I1 the context leaves the powertrain unset", [(WORKER,
     "        powertrain=powertrain,\n    )", "    )")],
     pytest("tests/test_phase379_ask_powertrain.py")),
    ("I2 /ask ignores the context's powertrain", [(VIDEOS,
     "        powertrain=context.powertrain,", "        powertrain=None,")],
     pytest("tests/test_phase379_ask_powertrain.py")),
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
