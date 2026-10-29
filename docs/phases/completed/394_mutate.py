"""Phase 394's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/394_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 392's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`B` the brief on stdin, `L` a launch that fails, `E` the Engineer's
session, `J` the journal's key, `S` "started" once per stage run.

No mutation makes a real model call or reaches GitHub: the `claude` the
tests run is a stand-in on PATH. Run it only when no fleet model-free run
is in progress on this machine (F220).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

F = ".claude/skills/fleet/"
RC, DI, EN, JO = F + "rank_call.py", F + "dispatcher.py", F + "engineer.py", F + "journal.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T = pytest("tests/test_phase394_brief_on_stdin.py")
T_RESUME = pytest("tests/test_phase390_resume.py")

MUTATIONS = [
    # the brief on stdin (rank_call.py, the fence)
    ("B1 the brief goes back into argv",
     [(RC, "r = run(command(model, schema, tools), input=prompt,",
       "r = run([*command(model, schema, tools)[:2], prompt, *command(model, schema, tools)[2:]],"
       " input=prompt,")], T),
    ("B2 the brief is not handed to stdin",
     [(RC, "r = run(command(model, schema, tools), input=prompt, capture_output=True,",
       "r = run(command(model, schema, tools), capture_output=True,")], T),
    ("B3 the fence keeps /dev/null as stdin",
     [(DI, "        if input is not None:\n            del kw[\"stdin\"]",
       "        if False:\n            del kw[\"stdin\"]")], T),
    ("B4 the fenced runner drops the brief",
     [(DI, 'r = self.fenced(cmd, timeout=kw.get("timeout", 1800), input=kw.get("input"))',
       'r = self.fenced(cmd, timeout=kw.get("timeout", 1800))')], T),
    # a launch that fails stops once
    ("L1 a rank's launch OSError is not a stop",
     [(RC, "    except OSError as e:\n        raise LaunchFailed(e) from e",
       "    except LookupError as e:\n        raise LaunchFailed(e) from e")], T),
    ("L2 the stop does not say why",
     [(RC, 'super().__init__(f"the model call could not start: {e}")',
       'super().__init__("stopped")')], T),
    # the Engineer's session
    ("E1 the session's stdin is not its brief",
     [(DI, '                kw["stdin"] = i\n', "")], T),
    ("E2 a resumed session gets its first brief, not CONTINUE",
     [(DI, 'cmd, brief = [cmd[0], "--resume", session, *cmd[1:]], engineer.CONTINUE',
       'cmd = [cmd[0], "--resume", session, *cmd[1:]]')], T_RESUME),
    ("E3 the session's launch OSError is not a stop",
     [(DI, "        except OSError as e:\n            raise LaunchFailed(e) from e",
       "        except LookupError as e:\n            raise LaunchFailed(e) from e")], T),
    ("E4 the brief stays in the Engineer's argv",
     [(EN, 'return ["claude", "-p", "--model", model,',
       'return ["claude", "-p", "x" * 140000, "--model", model,')], T),
    # the journal's key
    ("J1 call_key drops the flag after -p",
     [(JO, 'del plain[k:k + 1 if flag == "-p" and after.startswith("--") else k + 2]',
       "del plain[k:k + 2]")], T),
    ("J2 call_key keeps the old brief",
     [(JO, 'del plain[k:k + 1 if flag == "-p" and after.startswith("--") else k + 2]',
       "del plain[k:k + 1]")], T),
    # "started" once per stage run
    ("S1 a retry says started again",
     [(DI, "            if failed is not None:\n                j.mark(\"started\"",
       "            if False:\n                j.mark(\"started\"")], T),
    ("S2 any run's started stands, failed or not",
     [(DI, 'return found[1] if outcome.startswith("failed") else None', "return found[1]")], T),
    ("S3 another rank's started stands",
     [(DI, "if found is None or found[0] != rank or found[1] is None:",
       "if found is None or found[1] is None:")], T),
]


def clear_caches() -> None:
    for d in (ROOT / ".claude" / "skills").rglob("__pycache__"):
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
