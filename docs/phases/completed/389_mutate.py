"""Phase 389's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/389_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`F` the fence, `G` the push gate and identity, `D` the dispatcher, `S` the
Science Officer, `C` the Captain, `E` the Engineer, `R` the Red Team.

No mutation makes a real model call or reaches GitHub: every rank is judged
against stand-ins, and the fence's against fake tokens.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

FE = ".claude/skills/fleet/fence.sh"
NE = ".claude/skills/fleet/fence_net.py"
GI = ".claude/skills/fleet/fleet_git.py"
DI = ".claude/skills/fleet/dispatcher.py"
SC = ".claude/skills/fleet/scout.py"
CA = ".claude/skills/fleet/captain.py"
EN = ".claude/skills/fleet/engineer.py"
RT = ".claude/skills/fleet/red_team.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_FE = pytest("tests/test_phase388_fence_boundary.py", "-k",
              "TokenPipe or VenvAndTheMobile or TheEnvironment")
T_GI = pytest("tests/test_phase389_fleet_git.py")
T_DI = pytest("tests/test_phase389_dispatcher.py", "tests/test_phase388_dispatcher.py")
T_SC = pytest("tests/test_phase389_scout.py")
T_CA = pytest("tests/test_phase389_captain.py")
T_EN = pytest("tests/test_phase389_engineer.py")
T_RT = pytest("tests/test_phase389_red_team.py")

MUTATIONS = [
    # the fence
    ("F1 the old token variable let through", [(FE,
     '[ -z "${CLAUDE_CODE_OAUTH_TOKEN+x}" ] \\\n  || refuse', 'true \\\n  || refuse')], T_FE),
    ("F2 the network helper drops the token's pipe", [(NE,
     "pass_fds=(int(fd),) if fd else ()", "pass_fds=()")], T_FE),
    ("F3 the descriptor variable not set", [(FE,
     '[ -n "$tokenfd" ] && args+=(--setenv CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR 3)',
     'true')], T_FE),
    ("F4 the venv bound writable", [(FE,
     '[ -n "$venv" ] && args+=(--ro-bind "$venv" "$INSIDE/.venv")',
     '[ -n "$venv" ] && args+=(--bind "$venv" "$INSIDE/.venv")')], T_FE),
    ("F5 a missing venv not refused", [(FE,
     '[ -d "$venv" ] || refuse "no virtualenv directory: $venv"', 'true')], T_FE),
    ("F6 fd 3 not checked", [(FE,
     '{ true <&3; } 2>/dev/null || refuse "--token-fd, but file descriptor 3 is not open"',
     'true')], T_FE),
    # the push gate and the identity
    ("G1 master allowed", [(GI, 'if branch == "master" or not re.fullmatch',
                            'if False and not re.fullmatch')], T_GI),
    ("G2 a non-fast-forward allowed", [(GI,
     'if _git(clone, "merge-base", "--is-ancestor", base, head).returncode != 0:',
     'if False:')], T_GI),
    ("G3 the scout may touch anything", [(GI, '    if rank == "scout":\n        return (',
                                           '    if rank == "scout":\n        return True or (')], T_GI),
    ("G3b the guards and the fleet open to the engineer", [(GI,
     'if any(path == n or (n.endswith("/") and path.startswith(n)) for n in NEVER):',
     'if False:')], T_GI),
    ("G3c another phase's row may change", [(GI,
     'fails += [f"G3 the engineer may not change another phase\'s row: {r[:60]!r}" for r in others]',
     'pass')], T_GI),
    ("G4 no credential scan", [(GI, "    if any(SECRET.search(ln) for ln in added):",
                                "    if False:")], T_GI),
    ("G5 the ledger not checked", [(GI, 'fails += [f"G5 {d}" for d in drift]', "pass")], T_GI),
    ("G6 an untested commit allowed", [(GI, "        if not ok:\n            fails.append(f\"G6",
                                         "        if False:\n            fails.append(f\"G6")], T_GI),
    ("G7 any issue may use the operator's login", [(GI,
     "    if TRIAL_MARKER in (issue_body or \"\"):", "    if True:")], T_GI),
    ("G8 a file others can read accepted", [(GI,
     "    if stat.S_IMODE(path.stat().st_mode) & 0o077:", "    if False:")], T_GI),
    ("G9 the operator's own account accepted", [(GI,
     '    if user.lower() == "kubanjaze":', "    if False:")], T_GI),
    ("G10 the operator's credential helper not reset", [(GI,
     'git += ["-c", "credential.helper=", "-c",', 'git += ["-c",')], T_GI),
    # the dispatcher
    ("D1 no Fable gate", [(DI, "    if pct >= FABLE_CEILING:", "    if False:")], T_DI),
    ("D2 a closed phase gets a stage", [(DI,
     "            if rows.get(phase) != roadmap_check.ACTIVE:",
     "            if False:")], T_DI),
    ("D3 an operator-held issue gets a stage", [(DI,
     "            if labels & set(OPERATOR) or not labels & {\"mission\", *STATE_LABELS}:",
     "            if not labels & {\"mission\", *STATE_LABELS}:")], T_DI),
    ("D4 the token in the environment again", [(DI,
     '        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}\n        r_fd, kw = token_pipe',
     '        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), '
     '"CLAUDE_CODE_OAUTH_TOKEN": self.fleet.token}\n        r_fd, kw = token_pipe')], T_DI),
    ("D5 the Engineer's checks ignored", [(DI,
     "        if fails:\n            self.escalate(issue, \"engineer\", \"needs-admiral\",\n"
     "                          f\"Chief Engineer, phase {phase}: the work says",
     "        if False:\n            self.escalate(issue, \"engineer\", \"needs-admiral\",\n"
     "                          f\"Chief Engineer, phase {phase}: the work says")], T_DI),
    ("D6 a failed model-free run not counted", [(DI,
     "        if not check.ok:\n            fails.append(", "        if False:\n            fails.append(")],
     T_DI),
    ("D7 no limit on Red Team rounds", [(DI, "            if rnd >= red_team.MAX_ROUNDS:",
                                         "            if False:")], T_DI),
    ("D8 the revision does not make the XO due", [(DI,
     "        if items:\n            self.reapply(issue, REVIEW)",
     "        if items:\n            self.set_state(issue, REVIEW)")], T_DI),
    ("D9 the body's branch name ignored", [(DI,
     "        branch = branch or (named.group(1) if named else",
     "        branch = branch or (None if named else")], T_DI),
    ("D10 a watcher's reason ignored", [(DI,
     "        if reason:\n            self.escalate(issue, \"engineer\", \"needs-admiral\",",
     "        if False:\n            self.escalate(issue, \"engineer\", \"needs-admiral\",")], T_DI),
    ("D11 a non-trial issue pushed without an account", [(DI,
     "            return fleet_git.identity(body, self.identity_file)",
     "            return fleet_git.Identity('operator', None)")], T_DI),
    # the Science Officer
    ("S1 counts in the prose let through", [(SC,
     "        counts = plan_check.unshown_counts(prose)\n        if not counts:",
     "        counts = plan_check.unshown_counts(prose)\n        if True:")], T_SC),
    ("S2 the census table without its query", [(SC,
     '    lead = ("The census, no model: each count is `git grep -c -i -F -e <term> -- <area>` "',
     '    lead = ("The census, no model: each count is the grep "')], T_SC),
    ("S3 no mobile census", [(SC, '            row["counts"]["mobile src"] = _count(mobile, t, "src")',
                              "            pass")], T_SC),
    ("S4 an existing prompt overwritten", [(SC,
     '    if not list((clone / "docs" / "prompts").glob(f"{phase}_*.txt")):', "    if True:")], T_SC),
    # the Captain
    ("C1 the plan not checked", [(CA, "        if report.ok:\n            return calls",
                                  "        if True:\n            return calls")], T_CA),
    ("C2 a failed plan left in place", [(CA, "        if previous is None:\n            path.unlink()",
                                         "        if False:\n            path.unlink()")], T_CA),
    ("C3 a recommendation of any length", [(CA, "len(lines) == 3", "len(lines) >= 1")], T_CA),
    # the Engineer
    ("E1 a third bug fix goes on", [(EN, "MAX_BUG_FIXES = 2", "MAX_BUG_FIXES = 3")], T_EN),
    ("E2 a guard may block twice", [(EN, "if c >= 2]", "if c >= 3]")], T_EN),
    ("E3 any result accepted", [(EN, '    if r.get("outcome") != "pr-ready":\n        raise Stop',
                                 '    if False:\n        raise Stop')], T_EN),
    ("E4 the close-out not checked", [(EN,
     '    fails += [f"close-out: {f}" for f in closeout_check.check(clone, phase)]', "")], T_EN),
    ("E5 the counts not compared", [(EN, "    elif mine != theirs:", "    elif False:")], T_EN),
    ("E6 the session not bypassing permissions in the fence", [(EN,
     '"--permission-mode", "bypassPermissions",', '"--permission-mode", "default",')], T_EN),
    # the Red Team
    ("R1 the refute table not checked", [(RT, "    bad = refute_check.check(table)",
                                          "    bad = []")], T_RT),
    ("R2 a clear with factual findings", [(RT, "    if v[\"verdict\"] == CLEAR and blocking:",
                                           "    if False:")], T_RT),
    ("R3 'No refute pass ran' kept", [(RT,
     '    text = "\\n".join(ln for ln in text.splitlines() if ln.strip() != "No refute pass ran.")',
     "")], T_RT),
    ("R4 the plan's diff not given", [(RT,
     '            + f"\\n\\n=== the diff of v1.0 to v1.1 ===\\n{plan_diff}"', "")], T_RT),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude", ROOT / "scripts", ROOT / "ops"):
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
