"""Phase 403's mutations: each puts one part of (a) to (e) back the way it
was, or breaks the rule it holds, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/403_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 398's and 399's
harness: exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens, under a throwaway HOME
with FLEET_LEDGER, FLEET_STATE and FLEET_MOBILE unset. No mutation reaches
GitHub, the live database or a model. Exits 1 if any mutation stays green.
An argument runs only the mutations whose name starts with it. Run it only
when `pgrep -x bwrap` is empty (F220).
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

DI = ".claude/skills/fleet/dispatcher.py"
EN = ".claude/skills/fleet/engineer.py"
FG = ".claude/skills/fleet/fleet_git.py"
RT = ".claude/skills/fleet/red_team.py"
PO = ".claude/skills/fleet/plan_order.py"
AC = ".claude/skills/fleet/app_copy.py"
RC = ".claude/skills/refute/refute_check.py"
CC = ".claude/skills/closeout/closeout_check.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


A = pytest("tests/test_phase403_kept_stop.py")
B = pytest("tests/test_phase403_answer_carried.py")
C = pytest("tests/test_phase403_app_copy.py")
D = pytest("tests/test_phase403_briefs.py")
E = pytest("tests/test_phase403_granted_round.py")

MUTATIONS = [
    # (a) the kept stop
    ("M1 a stop with commits holds nothing",
     [(DI, "        if not new:\n", "        if True:\n")], A),
    ("M2 the stop's commits go to the phase branch",
     [(DI, "        side = fleet_git.side_branch(phase, run.name)",
       "        side = branch")], A),
    ("M3 the side mode asks for the model-free run",
     [(FG, "    if not fails and not side:", "    if not fails:")], A),
    ("M4 the side mode takes any phase branch name",
     [(FG, 'rf"phase-{re.escape(phase)}-stopped-[A-Za-z0-9._-]+" if side',
       'rf"phase-{re.escape(phase)}-[A-Za-z0-9._-]+" if side')], A),
    ("M5 the next round starts from GitHub's branch, the kept run unread",
     [(DI, "        held = self.stopped_hold(issue)\n        if held is None:\n"
           "            return self.stage_clone(run, branch)",
       "        held = None\n        if held is None:\n"
       "            return self.stage_clone(run, branch)")], A),
    ("M6 the ancestor rule is not asked",
     [(DI, "            ok = gh is None or self.git(", "            ok = True or self.git(")], A),
    # (b) the answer carried
    ("M7 another login's comment is quoted",
     [(DI, '                if str((c.get("author") or {}).get("login", "")).lower() == me',
       "                if True")], B),
    ("M8 comments from before the stop are quoted",
     [(DI, '                and _time(c["createdAt"]) > after', "                and True")], B),
    ("M9 nothing runs when needs-admiral comes off a stop (F231 as it was)",
     [(DI, '        if "build:open" in labels and (stopped := self.engineer_stop(n)) is not None:',
       '        if False and (stopped := self.engineer_stop(n)) is not None:')], B),
    ("M10 the brief does not say where the answer is",
     [(EN, "        prompt += CARRIED.format(ISSUE=issue, **carried)",
       "        prompt += ''")], B),
    # (c) the app's copy
    ("M11 the app's copy may go on main",
     [(AC, '    if branch in ("main", "master") or not re.fullmatch(',
       "    if branch in () and not re.fullmatch(")], C),
    ("M12 a second file changing in the app is let through",
     [(AC, "    if changed != [SCHEMA]:", "    if False:")], C),
    ("M13 another red check is let through",
     [(DI, "        if not fast.ok:\n            raise Stop(f\"another check",
       "        if False:\n            raise Stop(f\"another check")], C),
    ("M14 Gate 11 is not run again against the new copy",
     [(DI, "        if not after.ok:", "        if False:")], C),
    ("M15 the copy is pushed without the fleet's account",
     [(DI, "        if not ident.is_fleet:\n            raise Stop(\"the app's copy",
       "        if False:\n            raise Stop(\"the app's copy")], C),
    ("M16 the generator is not 372's method",
     [(AC, 'text = json.dumps(create_app().openapi(), indent=2, ensure_ascii=False)',
       'text = json.dumps(create_app().openapi(), indent=2, ensure_ascii=True)')], C),
    ("M17 the held app-copy run is not resumed",
     [(DI, '{"space": SPACE_M, "deploy": DEPLOY_M}.get(why, APP_M)',
       '{"space": SPACE_M, "deploy": DEPLOY_M}.get(why, SPACE_M)')], C),
    # (d) the briefs
    ("M18 rule 3 names sed -i under src/ and tests/ only",
     [(EN, "   The edit guard refuses sed -i wherever it points",
       "   The edit guard refuses sed -i under src/ and tests/")], D),
    ("M19 rule 6 gives no read-back",
     [(EN, "   .venv/bin/python .claude/skills/fleet/engineer.py record {N}\n", "")], D),
    ("M20 the Red Team's brief says nothing of a code finding's row",
     [(RT, 'is open until the Engineer fixes it. The table has no kind "code": a code',
       'is open until the Engineer fixes it. A code')], D),
    # (e) the granted round
    ("M21 C5 takes any round",
     [(RC, "        if k > 0 and (k > len(grants) or grant != grants[k - 1]):",
       "        if False:")], E),
    ("M22 C5 takes any grant's K-id",
     [(RC, "or grant != grants[k - 1]):", "or grant is None):")], E),
    ("M23 a grant for any phase counts",
     [(RC, "    return [kid for kid, p in _GRANT_ROW.findall(decisions_text or \"\") if p == phase]",
       "    return [kid for kid, p in _GRANT_ROW.findall(decisions_text or \"\")]")], E),
    ("M24 an ungranted fourth round runs (F277 as it was)",
     [(DI, "        if rnd > allowed and not resume:", "        if False:")], E),
    ("M25 one grant allows two rounds",
     [(DI, "        allowed = red_team.MAX_ROUNDS + len(grants)\n        if rnd > allowed",
       "        allowed = red_team.MAX_ROUNDS + 2 * len(grants)\n        if rnd > allowed")], E),
    ("M26 a granted round's back is not acted on",
     [(DI, "            if rnd >= red_team.MAX_ROUNDS and not grants:\n                # K9",
       "            if rnd >= red_team.MAX_ROUNDS:\n                # K9")], E),
    ("M27 a fix round runs past round 3 with no grant",
     [(DI, "                if rnd >= red_team.MAX_ROUNDS and not grants:\n                    # Phase",
       "                if False:\n                    # Phase")], E),
    ("M28 the grant is not written into the round's rows",
     [(RT, "        table = with_grant(table, rnd, grants[rnd - MAX_ROUNDS - 1])",
       "        pass")], E),
    ("M29 the record check refuses a grant",
     [(PO, "    if covers == NO_STOP or refute_check.GRANT_COVERS.match(covers):",
       "    if covers == NO_STOP:")], E),
    ("M30 A8 reads no grant",
     [(CC, "def review_grants(repo: pathlib.Path, phase: str) -> list[str]:",
       "def review_grants(repo: pathlib.Path, phase: str) -> list[str]:\n    return []")], E),
    ("M31 the spent-rounds stops name no options",
     [(DI, "        return options if options_only else head + options",
       "        return \"\" if options_only else head")], E),
]


def env_with_throwaway_home() -> dict:
    home = pathlib.Path(tempfile.mkdtemp(prefix="403_mutate_home_"))
    git = pathlib.Path.home() / ".gitconfig"
    if git.is_file():
        shutil.copy(git, home / ".gitconfig")
    env = {k: v for k, v in os.environ.items()
           if k not in ("FLEET_LEDGER", "FLEET_STATE", "FLEET_MOBILE")}
    env["HOME"] = str(home)
    return env


def clear_caches() -> None:
    for top in (ROOT / ".claude" / "skills", ROOT / "tests"):
        for d in top.rglob("__pycache__"):
            for f in d.glob("*.pyc"):
                f.unlink()


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                          env=env_with_throwaway_home()).returncode


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
