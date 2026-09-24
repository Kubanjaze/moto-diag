#!/usr/bin/env python3
"""ROADMAP continuity: the phase ledger stays true while phases are worked.

Five rules, each a claim about what the two repos hold:

  R1  no two rows in docs/ROADMAP.md share a phase number
  R2  every phase with documents under docs/phases/ has a row in the ROADMAP
      that owns its status: this repo's, or the mobile repo's for the range
      ROADMAP_AUTHORITY.md gives the mobile repo (185-204)
  R3  that row agrees with where the documents are: in_progress/ -> 🚧,
      completed/ -> ✅, or ⏸️ for a paused phase whose record was archived
  R4  every row this ROADMAP carries is in a range ROADMAP_AUTHORITY.md gives
      this repo; a mobile-owned row here is drift the contract forbids
  R5  the two copies of ROADMAP_AUTHORITY.md are identical

**Why this exists (2026-09-24).** Phase 257's successor was about to start
from a handoff note with no ROADMAP row. Looking for its row found two more
things nobody had noticed: two rows numbered 256 (the retrieval chokepoint
took the number and the planned row kept it), and row 353 outside every
range of the authority contract. Each was a claim the ledger made that no
check tested.

Run:
    python3 .claude/skills/closeout/roadmap_check.py              # check
    python3 .claude/skills/closeout/roadmap_check.py --self-test  # plant, watch each rule fire

Called by `tests/test_roadmap_continuity.py` (the guarantee) and by the push
guard, which refuses a `git push` while this fails.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SIBLING = ROOT.parent / "moto-diag-mobile"

DONE, PAUSED, ACTIVE = "✅", "⏸️", "🚧"
ROW = re.compile(r"^\| (\d{2,3}[A-Z]?) \| [^|]* \| ([^|]*) \|", re.M)
DOC = re.compile(r"^(\d{2,3}[A-Z]?)_")
#: "| 01–184 | A–H | **Backend repo** |" and "| 205+ | … | **Backend repo** |"
RANGE = re.compile(r"^\|\s*(\d+)\s*(?:[–-]\s*(\d+)|(\+))\s*\|[^|]*\|\s*\**\s*(Backend|Mobile)", re.M)


def _number(phase: str) -> int:
    return int(re.match(r"\d+", phase).group())


def rows(roadmap: str) -> list[tuple[str, str]]:
    """(phase, status) for every table row whose first cell is a phase number."""
    return [(n, s.strip()) for n, s in ROW.findall(roadmap)]


def ranges(authority: str) -> list[tuple[int, int, str]]:
    return [(int(lo), int(hi) if hi else 10**6, who.lower())
            for lo, hi, _plus, who in RANGE.findall(authority)]


def owner(phase: str, rngs: list[tuple[int, int, str]]) -> str | None:
    n = _number(phase)
    return next((who for lo, hi, who in rngs if lo <= n <= hi), None)


def phase_docs(phases_dir: pathlib.Path) -> dict[str, set[str]]:
    """{phase: {"in_progress", "completed"}} from the .md files' names."""
    found: dict[str, set[str]] = {}
    for sub in ("in_progress", "completed"):
        d = phases_dir / sub
        for p in sorted(d.glob("*.md")) if d.is_dir() else []:
            m = DOC.match(p.name)
            if m:
                found.setdefault(m.group(1), set()).add(sub)
    return found


def check(roadmap: str, authority: str, docs: dict[str, set[str]],
          mobile_roadmap: str | None = None, authority_copy: str | None = None) -> list[str]:
    """The five rules over already-read inputs. None for a mobile input means
    the mobile repo is not present: its half of R2 and R3, and R5, are not run."""
    fails: list[str] = []
    rngs = ranges(authority)
    own = rows(roadmap)
    counts: dict[str, int] = {}
    for n, _ in own:
        counts[n] = counts.get(n, 0) + 1
    fails += [f"R1 phase {n} has {c} rows in docs/ROADMAP.md" for n, c in counts.items() if c > 1]
    status = {n: s for n, s in reversed(own)}          # first row wins
    mobile = {n: s for n, s in reversed(rows(mobile_roadmap))} if mobile_roadmap is not None else None

    for n, where in sorted(docs.items()):
        if owner(n, rngs) == "mobile":
            if mobile is None:
                continue
            ledger, name = mobile, "the mobile repo's docs/ROADMAP.md"
        else:
            ledger, name = status, "docs/ROADMAP.md"
        if n not in ledger:
            fails.append(f"R2 phase {n} has documents under docs/phases/ but no row in {name}")
            continue
        s = ledger[n]
        if "in_progress" in where and s != ACTIVE:
            fails.append(f"R3 phase {n} has documents in in_progress/ but its row in {name} is {s!r}, not {ACTIVE}")
        elif "in_progress" not in where and s not in (DONE, PAUSED):
            fails.append(f"R3 phase {n} has documents in completed/ but its row in {name} is {s!r}, "
                         f"not {DONE} (or {PAUSED} if paused)")

    for n in counts:
        who = owner(n, rngs)
        if who is None:
            fails.append(f"R4 phase {n} is in no range of ROADMAP_AUTHORITY.md")
        elif who == "mobile":
            fails.append(f"R4 phase {n} is mobile-owned; docs/ROADMAP.md must not carry its row")
    if authority_copy is not None and authority_copy != authority:
        fails.append("R5 the two copies of ROADMAP_AUTHORITY.md differ")
    return fails


def check_tree(root: pathlib.Path = ROOT, sibling: pathlib.Path | None = SIBLING) -> list[str]:
    """The five rules over a repo on disk and, if present, its mobile sibling."""
    def read(p: pathlib.Path) -> str | None:
        return p.read_text(encoding="utf-8") if p.is_file() else None

    roadmap, authority = read(root / "docs" / "ROADMAP.md"), read(root / "ROADMAP_AUTHORITY.md")
    if roadmap is None or authority is None:
        return [f"R0 {root} has no docs/ROADMAP.md or ROADMAP_AUTHORITY.md"]
    sib = sibling if sibling is not None and sibling.is_dir() else None
    return check(roadmap, authority, phase_docs(root / "docs" / "phases"),
                 read(sib / "docs" / "ROADMAP.md") if sib else None,
                 read(sib / "ROADMAP_AUTHORITY.md") if sib else None)


def self_test() -> int:
    """Every rule must be seen to fire on the known-bad tree, and the good
    tree (Track I via the mobile ledger, a paused phase, one in progress)
    must pass — the controls for R2's redirect and R3's ⏸️."""
    real = check_tree()
    if real:
        print("self-test: the real repos do not pass; fix that first:\n  " + "\n  ".join(real))
        return 1
    bad = check_tree(HERE / "fixtures" / "roadmap_bad", HERE / "fixtures" / "roadmap_bad" / "sibling")
    ok = True
    for rule in ("R1", "R2", "R3", "R4", "R5"):
        fired = any(f.startswith(rule) for f in bad)
        ok &= fired
        print(f"  {rule} fires on the known-bad tree: {fired}")
    good = check_tree(HERE / "fixtures" / "roadmap_good", HERE / "fixtures" / "roadmap_good" / "sibling")
    print(f"  the good tree passes: {good == []}" + ("" if good == [] else "  " + "; ".join(good)))
    ok &= good == []
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    fails = check_tree()
    for f in fails:
        print(f)
    note = "" if SIBLING.is_dir() else f"  (mobile repo not at {SIBLING}: its half of R2/R3 and R5 not run)"
    verdict = f"FAIL: {len(fails)} broken" if fails else "ok: the ROADMAP, docs/phases/ and ROADMAP_AUTHORITY.md agree"
    print(verdict + note)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
