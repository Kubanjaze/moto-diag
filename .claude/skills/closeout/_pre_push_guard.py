#!/usr/bin/env python3
"""Phase 255D push guard. Blocks `git push` when closeout is incomplete.

Since 2026-09-24 it also blocks ANY `git push` while the ROADMAP has drifted
from docs/phases/ (`roadmap_check.py`). Close-out is guarded on `master`
only because it cannot be complete mid-phase; continuity can always be true
mid-phase — a phase's row exists before its Step 0 — so a work-in-progress
push is no reason to let the ledger lie.

**This script filters itself, and that is not a stylistic choice.** Phase
255D measured that `PreToolUse` ignores the `if` field in this build, while
`PostToolUse` honours it — same field, same value, same matcher, opposite
behaviour. A guard relying on `if` fires on EVERY Bash command, which is
what happened during D1: a blocking guard meant for `git push` blocked a
`cat`, and took away the shell needed to remove itself.

So the contract here is deliberately lopsided:

* **Exit 0 as early as possible.** Anything not recognised as a `git push`
  leaves in the first few lines, before any file is read or any test is run.
  A guard that can fail while deciding whether to guard is the lockout bug
  again.
* **Exit 2 only for a real `git push` with a real failure**, because exit 2
  is what blocks the call and returns stderr to the model.
* **Exit 0 on any internal error.** If this script cannot do its job it must
  not take the shell down with it. The test in `tests/` is the guarantee;
  this hook is only the earlier feedback.

Recovery, if a guard ever does block `Bash`: edit `.claude/settings.json`
with the **Write tool**, which does not pass through a `Bash` matcher.
"""
from __future__ import annotations

import json
import pathlib
import re
import shlex
import sys

# Shell operators that begin a new command within one command line.
_SEP = re.compile(r"(?:&&|\|\||[;|&])")


def is_git_push(command: str) -> bool:
    """Whether the command line actually runs `git push`.

    Split on shell operators, then check each segment's first two words.
    `echo "git push"` is NOT a push: the words appear inside a quoted
    argument, and shlex keeps them together as one token. v1.1-3 requires
    that such a command passes, because the cost of a false block is the
    lockout and the cost of a false pass is caught by the test.
    """
    for segment in _SEP.split(command or ""):
        try:
            words = shlex.split(segment)
        except ValueError:            # unbalanced quotes — not parseable
            continue
        # Skip a leading absolute/relative path to git, and env assignments.
        while words and ("=" in words[0] and not words[0].startswith("/")):
            words = words[1:]
        if len(words) >= 2 and pathlib.Path(words[0]).name == "git":
            if words[1] == "push":
                return True
    return False


def targets_master(command: str, repo: pathlib.Path) -> bool:
    """Whether this push puts commits on `master`.

    **Why the guard is narrower than "any push".** Close-out is what must
    happen before work reaches `master`. A phase branch is pushed many times
    while the phase is still open — that is normal and is not a skipped
    close-out. A guard that blocked every push would block every
    work-in-progress push for the whole phase, and the only way to work
    would be to disable the guard, which is worse than not having one.

    So: a push is guarded when it names `master` as a refspec, or when it
    names no refspec and the checkout is on `master`.
    """
    words = []
    for segment in _SEP.split(command or ""):
        try:
            w = shlex.split(segment)
        except ValueError:
            continue
        if len(w) >= 2 and pathlib.Path(w[0]).name == "git" and w[1] == "push":
            words = w[2:]
            break
    refs = [w for w in words if not w.startswith("-")]
    if any(w == "master" or w.endswith(":master") or w.startswith("master:")
           for w in refs):
        return True
    if len(refs) > 1:            # an explicit non-master refspec was given
        return False
    head = (repo / ".git" / "HEAD")
    try:
        return head.read_text(encoding="utf-8").strip().endswith("/master")
    except OSError:
        return False


def current_phase(repo: pathlib.Path) -> str | None:
    """The phase with documents still in in_progress/, if exactly one."""
    d = repo / "docs" / "phases" / "in_progress"
    if not d.is_dir():
        return None
    phases = {m.group(1) for f in d.glob("*.md")
              if (m := re.match(r"^(\d+[A-Z]?)_", f.name))}
    return phases.pop() if len(phases) == 1 else None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0                                   # not our shape; stay out
    command = (payload.get("tool_input") or {}).get("command", "")
    if not is_git_push(command):
        return 0                                   # THE early exit

    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import roadmap_check                       # the SAME function the test calls
        drift = roadmap_check.check_tree()
    except Exception:
        drift = []                                 # never lock out the shell
    if drift:
        print("the ROADMAP has drifted from docs/phases/; push blocked.\n"
              + "\n".join("  " + f for f in drift)
              + "\n\nUpdate docs/ROADMAP.md (CLAUDE.md: a phase's row exists before "
                "its Step 0 and changes with the work), then push again. "
                "tests/test_roadmap_continuity.py is the guarantee, and it calls "
                "the same function.", file=sys.stderr)
        return 2

    try:
        repo = pathlib.Path(__file__).resolve().parents[3]
        if not targets_master(command, repo):
            return 0                               # a phase-branch push
        phase = current_phase(repo)
        if phase is None:
            return 0                               # nothing mid-flight
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from closeout_check import check           # the SAME function the test calls
        fails = check(repo, phase)
    except Exception:
        return 0                                   # never lock out the shell

    if fails:
        print(f"closeout is not complete for phase {phase}; push blocked.\n"
              + "\n".join("  " + f for f in fails)
              + "\n\nFinish the close-out, or push again once these pass. "
                "This guard is only the earlier feedback — "
                "tests/test_phase255D_closeout_contract.py is the guarantee, "
                "and it calls the same function.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
