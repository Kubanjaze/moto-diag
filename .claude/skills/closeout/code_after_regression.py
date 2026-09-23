#!/usr/bin/env python3
"""verify_phase.sh check 2: was any CODE changed after the regression hash?

ONE implementation. `verify_phase.sh` calls it and the contract test calls
it, so the scope cannot drift between them.

**Why this exists (F137).** Check 2 was `git diff REG..TIP -- src/ tests/`.
Phase 255D's bug fixes #5 and #6 changed `closeout_check.py` and
`finding_check.py` after the closing regression, and check 2 printed only a
floor-test bump: `.claude/` is executable code the scope could not see. The
path list was an exclusion nobody had written down as one — everything
outside two directories was treated as documentation.

**So the rule is inverted.** A path is code unless it is positively
documentation: anything under `docs/` (the record, including its evidence
JSON), a `.md` file outside the code directories, or one of a few named
non-executable files. Everything else — `.claude/` (skill scripts, hooks,
settings, fixtures), `scripts/`, `data/`, `main.py`, `pyproject.toml`, the
Docker files — is code. A new directory is code until someone says why not.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

#: Always code, whatever the suffix. A SKILL.md or a fixture `.md` under
#: `.claude/` is read by a check or a session; changing it changes behaviour.
CODE_DIRS = ("src/", "tests/", "scripts/", ".claude/", "data/")

#: Named non-code files outside `docs/`. Each is here for a reason: the
#: licence text, and git's own bookkeeping files, which no build reads.
NOT_CODE_NAMES = frozenset({"LICENSE", ".gitignore", ".gitkeep"})


def is_code(path: str) -> bool:
    if path.startswith(CODE_DIRS):
        return True
    if path.startswith("docs/"):
        return False
    name = path.rsplit("/", 1)[-1]
    if name in NOT_CODE_NAMES or name.endswith(".md"):
        return False
    return True


def code_paths(paths) -> list[str]:
    return [p for p in paths if p and is_code(p)]


def changed_since(repo: pathlib.Path, reg: str, tip: str) -> list[str]:
    r = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", f"{reg}..{tip}"],
        capture_output=True, text=True, check=True)
    return code_paths(r.stdout.splitlines())


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: code_after_regression.py <repo> <REG_HASH> <TIP>",
              file=sys.stderr)
        return 2
    hits = changed_since(pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3])
    for p in hits:
        print(f"  CODE after regression: {p}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
