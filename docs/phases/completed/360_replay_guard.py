"""Phase 360: replay past sessions' Bash commands through the edit guard.

Reads the N newest session transcripts of this repo under
~/.claude/projects/-Users-lilquant-Projects-moto-diag/, runs every Bash
command through `_edit_guard.check` with the cwd the session recorded, and
prints the count per class and the slowest check. This produced the census
in the closeout CHANGELOG's 2026-09-28 entry and the phase log.

    .venv/bin/python -B docs/phases/completed/360_replay_guard.py [N=8]

The transcripts live outside the repo and grow, so a later run over "the
eight newest" reads a different set: the census is of the set named by its
date range, which the script prints.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / ".claude" / "skills" / "closeout"))
import _edit_guard as guard  # noqa: E402

TRANSCRIPTS = pathlib.Path.home() / ".claude" / "projects" / "-Users-lilquant-Projects-moto-diag"


def commands(paths: list[pathlib.Path]):
    for path in paths:
        for line in path.open(encoding="utf-8", errors="replace"):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message")
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Bash":
                    yield (rec.get("timestamp", ""), rec.get("cwd") or str(REPO),
                           c.get("input", {}).get("command", ""))


def kind(why: str | None) -> str:
    if not why:
        return "allowed"
    if why.startswith("a Python script body writes to a path") or "cannot tell" in why:
        return "blocked: fails closed (unresolved target)"
    if "cannot parse" in why or "not valid Python" in why:
        return "blocked: malformed"
    if "in place" in why:
        return "blocked: sed -i / perl -i"
    if why.startswith("a Python script body writes"):
        return "blocked: Python body writes src/ or tests/"
    if "the redirect" in why:
        return "blocked: redirect into src/ or tests/"
    return "blocked: tee, cp, mv, patch or another body into src/ or tests/"


def main(n: int) -> None:
    paths = sorted(TRANSCRIPTS.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)[-n:]
    counts, worst, stamps = collections.Counter(), 0.0, []
    for stamp, cwd, command in commands(paths):
        start = time.monotonic()
        why = guard.check(command, cwd)
        worst = max(worst, time.monotonic() - start)
        counts[kind(why)] += 1
        if stamp:
            stamps.append(stamp)
    print(f"{len(paths)} transcripts, {sum(counts.values())} Bash commands, "
          f"{min(stamps, default='?')[:10]} to {max(stamps, default='?')[:10]}")
    for k, v in sorted(counts.items()):
        print(f"  {v:5d}  {k}")
    print(f"  slowest check: {worst * 1000:.1f} ms")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
