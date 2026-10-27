#!/usr/bin/env python3
"""The plan of record, read exactly: the order, what bears on a phase, and
the stops the record answers (Phase 392).

    plan_order.py check              what is wrong with the list (exit 1 if anything)
    plan_order.py next               the next entry, as the dispatcher reads it
    plan_order.py bearing <phase>    what a rank's brief gets for the phase

**The order** is the "Next, in order" table at the top of
`docs/reports/2026-10-12_plan_of_record.md` (the operator, 2026-10-27, K48:
"add a short "Next, in order" list at its top that the fleet reads exactly;
it changes only by a dated entry with a K-id, written on my word"). One row
per phase:

    | # | phase | kind | built by | needs the operator | entry |

`kind` is `shop` or `fleet`; `built by` is `fleet` or `builder` (a builder
session, which the fleet waits for); `needs the operator` is `nothing`, or
one of `NEEDS` followed by a colon and what, in plain English; `entry` is
where in the plan it comes from and its K-id. Above the table, one line
"As of <date>, <K-id>.": the date of a dated entry under "Changes to the
order", and a K-id that resolves.

**What bears on a phase** (`bearing`): its order entry, each dated change
that names it, and each `docs/decisions.md` row that names it. Every rank
that plans or judges gets it in its brief (`brief_block`) and ends what it
writes with it (`cite_line`).

**A stop the record answers** (`answer`), the operator's K50: "only when one
K-id's own words cover the same kind of stop and the same subject; the
answer quotes it verbatim and cites the K-id; never a rule-1 stop … give
each K-id a "covers" line so matching is a lookup". The `Covers` column of
`docs/decisions.md` is `no stop` or `stop=<kind> subject=<phase>[,<phase>]`;
only `ANSWERABLE` kinds may appear, and one match exactly answers.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from dataclasses import dataclass, field

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "closeout"))
from roadmap_check import DONE  # noqa: E402

ROOT = HERE.parents[2]
PLAN = "docs/reports/2026-10-12_plan_of_record.md"
DECISIONS = "docs/decisions.md"
TRIAGE_REPORTS = ("docs/reports/2026-09-27_process_kinks_triage.md",
                  "docs/reports/2026-10-07_process_kinks_triage.md")
ORDER_HEADING = "## Next, in order"
CHANGES_HEADING = "## Changes to the order"
KINDS = ("shop", "fleet")
BUILT_BY = ("fleet", "builder")
#: What an entry may need from the operator, and the label the fleet asks with.
NEEDS = {"an outside account": "needs-hands", "an outside person": "needs-hands",
         "a credential": "needs-hands", "a fork": "needs-admiral",
         "a live change": "needs-admiral",
         # A threshold or a rule's definition (rule 1; K52: F210's rule before 330).
         "a rule change": "needs-admiral"}
#: CLAUDE.md rule 1's five kinds, as the Engineer names them: never answered (K50).
RULE1_KINDS = ("fork", "threshold-or-rule", "test-cannot-be-green", "login-or-credential",
               "live-database-change")
#: The Engineer's other stop kinds: the only ones the record may answer.
ANSWERABLE = ("third-bug-fix", "guard-blocked-twice")
NO_STOP = "no stop"

_HEADER = re.compile(r"^\| *# *\| *phase *\| *kind *\| *built by *\| *needs the operator *\|"
                     r" *entry *\| *$")
_AS_OF = re.compile(r"^As of (\d{4}-\d{2}-\d{2}), (K\d+)\.\s*$", re.M)
_CELLS = re.compile(r"(?<!\\)\|")
_DATED = re.compile(r"^- \*\*(\d{4}-\d{2}-\d{2}[^:*]*):? ?(.*?)\*\*", re.M)
_ROW = re.compile(r"^\| (\d{2,3}[A-Z]?) \| ([^|]*) \| ([^|]*) \|", re.M)
_KID = re.compile(r"\bK(\d{1,3})\b")
_KID_DEF = re.compile(r"^(?:#{2,4} K(\d+)\b|- \*\*K(\d+)\b)", re.M)
_COVERS = re.compile(r"^stop=([a-z-]+) subject=([0-9A-Z]+(?:,[0-9A-Z]+)*)$")
_PHASE = re.compile(r"^\d{2,3}[A-Z]?$")


def names(text: str, phase: str) -> bool:
    """Whether `text` names `phase` as a number of its own (not 3030, not K303,
    not 391_step0)."""
    return re.search(rf"(?<![\w.]){re.escape(phase)}(?!\w)", text) is not None


def _read(root: pathlib.Path, rel: str) -> str:
    p = root / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _cells(line: str) -> list[str]:
    return [c.strip().replace("\\|", "|") for c in _CELLS.split(line.strip())[1:-1]]


def _section(text: str, heading: str) -> str:
    i = text.find("\n" + heading + "\n")
    if i < 0:
        return ""
    rest = text[i + len(heading) + 2:]
    j = rest.find("\n## ")
    return rest if j < 0 else rest[:j]


# ------------------------------------------------------------------- the order
@dataclass
class Entry:
    n: int
    phase: str
    kind: str
    built_by: str
    needs: str                 # "nothing" or the full cell
    entry: str

    @property
    def need(self) -> str | None:
        """The kind of need (a NEEDS key), or None for nothing."""
        return next((k for k in NEEDS if self.needs.startswith(k + ":")), None)

    @property
    def kids(self) -> list[str]:
        return [f"K{n}" for n in _KID.findall(self.entry)]

    def line(self) -> str:
        return (f"{self.n}. {self.phase} ({self.kind}, built by {self.built_by}); needs the "
                f"operator: {self.needs}; from: {self.entry}")


@dataclass
class Order:
    as_of: tuple[str, str] | None
    entries: list[Entry] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def parse_order(plan: str) -> Order:
    body = _section(plan, ORDER_HEADING)
    if not body:
        return Order(None, problems=[f"the plan of record has no '{ORDER_HEADING}' section"])
    m = _AS_OF.search(body)
    order = Order((m.group(1), m.group(2)) if m else None)
    if m is None:
        order.problems.append("the list has no 'As of <date>, <K-id>.' line")
    lines = [ln for ln in body.splitlines() if ln.startswith("|")]
    if not lines or not _HEADER.match(lines[0]):
        order.problems.append("the list's header is not | # | phase | kind | built by | "
                              "needs the operator | entry |")
        return order
    for ln in lines[2:]:
        c = _cells(ln)
        if len(c) != 6:
            order.problems.append(f"a row without six cells: {ln[:80]!r}")
            continue
        n, phase, kind, built, needs, entry = c
        why = []
        if not n.isdigit():
            why.append(f"its number {n!r}")
        if not _PHASE.match(phase):
            why.append(f"its phase {phase!r}")
        if kind not in KINDS:
            why.append(f"its kind {kind!r} (shop or fleet)")
        if built not in BUILT_BY:
            why.append(f"its builder {built!r} (fleet or builder)")
        if needs != "nothing" and not any(needs.startswith(k + ": ") and len(needs) > len(k) + 3
                                          for k in NEEDS):
            why.append(f"its need {needs[:40]!r} (nothing, or one of {', '.join(NEEDS)}, "
                       "a colon, and what)")
        if not _KID.search(entry):
            why.append("its entry cites no K-id")
        if why:
            order.problems.append(f"row {ln[:40]!r}: " + "; ".join(why))
            continue
        order.entries.append(Entry(int(n), phase, kind, built, needs, entry))
    if [e.n for e in order.entries] != list(range(1, len(order.entries) + 1)):
        order.problems.append("the rows are not numbered 1, 2, 3, … in order")
    seen: set[str] = set()
    for e in order.entries:
        if e.phase in seen:
            order.problems.append(f"phase {e.phase} is listed twice")
        seen.add(e.phase)
    return order


def changes(plan: str) -> list[tuple[str, str, str]]:
    """(its date as written, heading, the whole bullet) for each dated entry
    under "Changes to the order". The date as written may run on: "2026-10-26,
    later"; its first ten characters are the day."""
    body = _section(plan, CHANGES_HEADING)
    out: list[tuple[str, str, str]] = []
    for chunk in re.split(r"\n(?=- \*\*)", "\n" + body):
        m = _DATED.match(chunk.strip("\n"))
        if m:
            out.append((m.group(1), m.group(2).strip(), chunk.strip("\n")))
    return out


def rows_of(roadmap: str) -> dict[str, tuple[str, str]]:
    """{phase: (status, title)}, the last row winning (387)."""
    return {n: (s.strip(), title.strip()) for n, title, s in reversed(_ROW.findall(roadmap))}


# ------------------------------------------------------------------- decisions
@dataclass
class Decision:
    kid: str
    date: str
    words: str
    check: str
    covers: str

    @property
    def stop(self) -> tuple[str, tuple[str, ...]] | None:
        m = _COVERS.match(self.covers)
        return (m.group(1), tuple(m.group(2).split(","))) if m else None

    def quoted(self) -> str:
        return f"{self.kid} ({self.date}): {self.words}"


def decisions(text: str) -> list[Decision]:
    out = []
    for ln in text.splitlines():
        if not re.match(r"^\| K\d+ \|", ln):
            continue
        c = _cells(ln)
        c += [""] * (5 - len(c))
        out.append(Decision(c[0], c[1], c[2], c[3], c[4]))
    return out


def covers_problem(covers: str) -> str | None:
    """Why a Covers cell is not a lookup the record may use, or None."""
    if covers == NO_STOP:
        return None
    m = _COVERS.match(covers)
    if not m:
        return (f"Covers {covers!r} is not '{NO_STOP}' or "
                "'stop=<kind> subject=<phase>[,<phase>]'")
    if m.group(1) in RULE1_KINDS:
        return f"Covers names {m.group(1)}, a rule-1 stop, which the record never answers (K50)"
    if m.group(1) not in ANSWERABLE:
        return f"Covers names {m.group(1)!r}, not one of {', '.join(ANSWERABLE)}"
    return None


#: Every file the record is read from, by its path in the repository.
FILES = (PLAN, DECISIONS, "docs/ROADMAP.md", *TRIAGE_REPORTS)


def texts_of(root: pathlib.Path) -> dict[str, str]:
    return {rel: _read(root, rel) for rel in FILES}


def defined_kids(texts: dict[str, str]) -> set[str]:
    found = {f"K{a or b}" for rel in TRIAGE_REPORTS
             for a, b in _KID_DEF.findall(texts.get(rel, ""))}
    return found | {d.kid for d in decisions(texts.get(DECISIONS, ""))}


# ------------------------------------------------------------------- checks
def check(root: pathlib.Path = ROOT) -> list[str]:
    """Everything wrong with the list and the Covers column; [] when the
    fleet may read them."""
    return check_texts(texts_of(root))


def check_texts(texts: dict[str, str]) -> list[str]:
    """`check` on the files' texts: how the dispatcher reads master's copy
    from its mirror."""
    plan, roadmap = texts.get(PLAN, ""), texts.get("docs/ROADMAP.md", "")
    if not plan:
        return [f"{PLAN} cannot be read"]
    order = parse_order(plan)
    fails = list(order.problems)
    rows = rows_of(roadmap)
    kids = defined_kids(texts)
    fails += [f"phase {e.phase} has no ROADMAP row" for e in order.entries if e.phase not in rows]
    fails += [f"phase {e.phase}'s entry cites {k}, which does not resolve"
              for e in order.entries for k in e.kids if k not in kids]
    if order.as_of:
        day, kid = order.as_of
        if day not in {d[:10] for d, _, _ in changes(plan)}:
            fails.append(f"the list is as of {day}, and no entry under '{CHANGES_HEADING}' "
                         "has that date")
        if kid not in kids:
            fails.append(f"the list is as of {kid}, which does not resolve")
        elif not any(d[:10] == day and kid in body for d, _, body in changes(plan)):
            fails.append(f"the dated entry of {day} does not cite {kid}")
    for d in decisions(texts.get(DECISIONS, "")):
        why = covers_problem(d.covers)
        if why:
            fails.append(f"{d.kid}: {why}")
    return fails


def next_entry(order: Order, rows: dict[str, tuple[str, str]]) -> Entry | None:
    """The first entry whose ROADMAP row is not ✅."""
    return next((e for e in order.entries if rows.get(e.phase, ("",))[0] != DONE), None)


def first_shop(plan: str) -> list[str]:
    """The phases the plan's Wave 1 names, in its order."""
    body = next((_section(plan, h) for h in re.findall(r"^(## Wave 1\b.*)$", plan, re.M)), "")
    out: list[str] = []
    for p in re.findall(r"(?<![\w.-])(\d{3})(?!\w)", body):
        if p not in out:
            out.append(p)
    return out


# ------------------------------------------------------------------- bearing
@dataclass
class Bearing:
    phase: str
    entry: Entry | None
    changes: list[tuple[str, str, str]]
    decisions: list[Decision]

    def cites(self) -> list[str]:
        """Each dated entry and K-id that bears on the phase, once, in order."""
        listed = [f"the plan of record's 'Next, in order' #{self.entry.n}"] if self.entry else []
        out: list[str] = []
        for c in [*listed, *(f"the plan of record, {d}" for d, _, _ in self.changes),
                  *(self.entry.kids if self.entry else []), *(d.kid for d in self.decisions)]:
            if c not in out:
                out.append(c)
        return out


def bearing(root: pathlib.Path, phase: str) -> Bearing:
    plan = _read(root, PLAN)
    order = parse_order(plan)
    entry = next((e for e in order.entries if e.phase == phase), None)
    return Bearing(phase, entry, [c for c in changes(plan) if names(c[2], phase)],
                   [d for d in decisions(_read(root, DECISIONS))
                    if names(f"{d.words} {d.check}", phase)])


def brief_block(root: pathlib.Path, phase: str) -> str:
    """What a rank's prompt gets: the record's words on this phase, verbatim."""
    b = bearing(root, phase)
    parts = [f"=== the plan of record and docs/decisions.md, on phase {phase} ===",
             f"Read {PLAN} and {DECISIONS} yourself as well. What bears on this phase, "
             "verbatim (cite the dated entry or the K-id that puts it in order):"]
    if b.entry:
        parts.append("- 'Next, in order': " + b.entry.line())
    parts += [f"- the plan of record, {d}:\n{body}" for d, _, body in b.changes]
    parts += [f"- {d.kid} ({d.date}): the operator's words {d.words}; the check it became: "
              f"{d.check}" for d in b.decisions]
    if len(parts) == 2:
        parts.append("- nothing names this phase: no entry puts it in order.")
    return "\n".join(parts)


def cite_line(root: pathlib.Path, phase: str) -> str:
    """The line a rank's comment ends with."""
    c = bearing(root, phase).cites()
    return ("The plan of record on this phase: " + "; ".join(c) + "." if c else
            "The plan of record names this phase nowhere: no entry puts it in order.")


# ------------------------------------------------------------------- answers
def answer(root: pathlib.Path, kind: str, phase: str) -> Decision | None:
    """The one K-id whose Covers names this stop kind and this phase; None for
    a rule-1 kind, for no match, and for two (the operator then decides)."""
    if kind not in ANSWERABLE:
        return None
    found = [d for d in decisions(_read(root, DECISIONS))
             if covers_problem(d.covers) is None and d.stop
             and d.stop[0] == kind and phase in d.stop[1]]
    return found[0] if len(found) == 1 else None


# ------------------------------------------------------------------- the CLI
def main(argv: list[str]) -> int:
    root = ROOT
    if argv[:1] == ["check"]:
        fails = check(root)
        for f in fails:
            print(f"FAIL {f}")
        print("plan_order: " + ("the list and the Covers column read exactly" if not fails
                                else f"{len(fails)} problem(s)"))
        return 1 if fails else 0
    if argv[:1] == ["next"]:
        rows = rows_of(_read(root, "docs/ROADMAP.md"))
        e = next_entry(parse_order(_read(root, PLAN)), rows)
        print(json.dumps(None if e is None else {**e.__dict__, "need": e.need,
                                                 "status": rows.get(e.phase, ("",))[0]},
                         ensure_ascii=False))
        return 0
    if argv[:1] == ["bearing"] and len(argv) == 2:
        print(brief_block(root, argv[1]))
        print(cite_line(root, argv[1]))
        return 0
    print(__doc__.split("\n\n")[1])
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
