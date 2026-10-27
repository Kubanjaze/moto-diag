#!/usr/bin/env python3
"""The Executive Officer's checklist: pure checks on a phase plan, no model.

Eight items, each with a stable id, so a failure names itself and the
known-bad fixture can require that each one fires on its own case:

  P1  the phase has a ROADMAP row and it is 🚧
  P2  <N>_step0.md exists
  P3  every count in the step-0 report shows the query that produced it
  P4  the step-0 classification is greenfield or extension (reshape fails,
      and so does no classification)
  P5  the plan names no path under data/, no seed data, no split and no
      eval protocol (its Non-goals section is not read: a plan may say what
      it leaves alone)
  P6  every section of implementation.md is filled, with no stub; Goal and
      Logic are present
  P7  the plan cites the three newest CLAUDE.md change-log entries, each
      with the check it became
  P8  the plan lists the rule-1 stops it anticipates
  P9  the plan names a plan-of-record entry or a K-id that puts the phase
      in order (Phase 392, K44): a K-id whose `docs/decisions.md` row names
      the phase, a dated entry under "Changes to the order" that names it
      (cited by its date), or the K-id of the phase's "Next, in order" row
  P10 a fleet-only phase names the first-shop phase it unblocks (K43): a
      line saying "unblocks" with a Wave 1 phase whose row is not ✅.
      Fleet-only is the "Next, in order" row's kind; a phase not listed is
      fleet-only when its plan names `.claude/skills/fleet/` and, outside
      Non-goals, nothing under `src/`

**Reused, not copied (Phase 387 Step 0, S0-4).** P1 reads the ROADMAP with
`roadmap_check.rows()` and `ACTIVE`; P5's knowledge-content path is
`wholetree.CONTENT_PATHS`, the one the push guard already treats as content.
Nothing else the checklist needs existed.

**Before the record (Phase 392).** P9 and P10 read the plan of record and
`docs/decisions.md` through `plan_order.py`. The v1.0 plans the tests read
at their commits were written before either item: `BEFORE_THE_RECORD`
pins each to exactly the items it fails, equality-tested like the pin
below.

**Written before (the operator, 2026-10-22: "Pin them (Recommended)").**
384's and 386's v1.0 were written before P4, P7 and P8 existed. Those items
are not applied to them, and the report says so. `WRITTEN_BEFORE` is held to
equality by `tests/test_phase387_fleet_contract.py`: without the pin, each
plan fails on exactly its pinned items.

Run:
    plan_check.py <phase> [--repo PATH] [--rev COMMIT] [--no-pin]

`--rev` reads every file as it was in that commit, which is how a plan is
checked as it was approved. Exit 0 pass, 1 fail (each failed item printed by
id), 2 cannot read the ROADMAP, CLAUDE.md or the plan.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "closeout"))
from roadmap_check import ACTIVE, DONE, rows  # noqa: E402
from wholetree import CONTENT_PATHS  # noqa: E402

sys.path.insert(0, str(HERE))
import plan_order  # noqa: E402

ITEM_IDS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10")

#: The plans written before P4, P7 and P8 existed, and the items each one
#: predates. The operator's pick, 2026-10-22. Equality-tested.
WRITTEN_BEFORE: dict[str, frozenset[str]] = {
    "384": frozenset({"P4", "P7", "P8"}),
    "386": frozenset({"P7", "P8"}),
}
#: The plans the tests read at their v1.0 commits, written before P9 and
#: P10 existed (Phase 392), and the items each fails. Equality-tested.
BEFORE_THE_RECORD: dict[str, frozenset[str]] = {
    "384": frozenset({"P9"}),
    "386": frozenset({"P9"}),
    "387": frozenset({"P9", "P10"}),
}


# ------------------------------------------------------------------ reading
class Source:
    """The repository's files, from the working tree or from one commit."""

    def __init__(self, root: pathlib.Path, rev: str | None = None):
        self.root, self.rev = pathlib.Path(root), rev

    def read(self, rel: str) -> str | None:
        if self.rev is None:
            p = self.root / rel
            try:
                return p.read_text(encoding="utf-8")
            except OSError:
                return None
        r = subprocess.run(["git", "-C", str(self.root), "show", f"{self.rev}:{rel}"],
                           capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None

    def exists(self, rel: str) -> bool:
        rel = rel.rstrip("/")
        if self.rev is None:
            return (self.root / rel).exists()
        return subprocess.run(["git", "-C", str(self.root), "cat-file", "-e", f"{self.rev}:{rel}"],
                              capture_output=True).returncode == 0


def plan_paths(phase: str) -> tuple[str, str]:
    d = "docs/phases/in_progress"
    return f"{d}/{phase}_implementation.md", f"{d}/{phase}_step0.md"


# ------------------------------------------------------------------- blocks
@dataclass
class Block:
    """A paragraph, a bullet item with its continuation lines, or one table
    row with its table's lead paragraph (`lead`)."""
    kind: str
    text: str
    lead: str = ""


def blocks(text: str) -> list[Block]:
    out: list[Block] = []
    cur: list[str] = []
    kind: str | None = None
    para = ""                  # the block just before a table: its lead
    fenced = False

    def flush() -> None:
        nonlocal cur, kind, para
        if cur and kind in ("para", "bullet"):
            para = "\n".join(cur)
            out.append(Block(kind, para))
        cur, kind = [], None

    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("```"):
            flush()
            fenced = not fenced
            continue
        if fenced:
            continue
        if not s or s.startswith("#") or s == "---":
            flush()
            if s.startswith("#"):
                para = ""
            continue
        if s.startswith("|"):
            flush()
            if not re.fullmatch(r"\|[\s:|-]+\|?", s):
                out.append(Block("row", ln, para))
            continue
        if re.match(r"(?:[-*+]|\d+\.)\s", s):
            flush()
            kind = "bullet"
            cur.append(ln)
            continue
        if kind is None:
            kind = "para"
        cur.append(ln)
    flush()
    return out


def sections(text: str) -> list[tuple[int, str, list[str]]]:
    """(level, heading, the lines under it up to the next heading at its
    level or above), for every heading outside a code fence."""
    lines = text.splitlines()
    heads, fenced = [], False
    for i, ln in enumerate(lines):
        if ln.strip().startswith("```"):
            fenced = not fenced
        m = None if fenced else re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    out = []
    for k, (i, lvl, title) in enumerate(heads):
        end = next((j for j, l2, _ in heads[k + 1:] if l2 <= lvl), len(lines))
        out.append((lvl, title, lines[i + 1:end]))
    return out


def without_sections(text: str, title: re.Pattern) -> str:
    """The text with every section whose heading matches `title` removed."""
    lines = text.splitlines()
    drop: set[int] = set()
    heads = [(i, len(m.group(1)), m.group(2)) for i, ln in enumerate(lines)
             if (m := re.match(r"^(#{1,6})\s+(.*)$", ln))]
    for k, (i, lvl, t) in enumerate(heads):
        if title.search(t):
            end = next((j for j, l2, _ in heads[k + 1:] if l2 <= lvl), len(lines))
            drop.update(range(i, end))
    return "\n".join(ln for i, ln in enumerate(lines) if i not in drop)


# ----------------------------------------------------------------- P3 counts
#: A count: a number, then within two words a counted noun. The words between
#: may not be a preposition, an article or a verb: "384 on three items" names
#: a phase, it does not count one.
_BETWEEN = (r"(?!(?:on|in|at|of|for|from|to|by|with|and|or|the|a|an|is|was|are|were|has|had|"
            r"says|said|ran|runs)\b)[\w'()-]+")
COUNT = re.compile(rf"(?<![\w.$/#-])(\d[\d,]*)(?:\*\*)?\s+(?:{_BETWEEN}\s+){{0,2}}?"
                   r"(?P<noun>[a-z][a-z-]*s|passed|failed|skipped)\b")
#: Units and words that end in s but count nothing.
NOT_COUNTED = frozenset({
    "seconds", "minutes", "hours", "days", "weeks", "months", "years", "ms", "s", "bytes",
    "times", "cents", "dollars", "its", "is", "was", "has", "does", "goes", "plus", "as",
    "this", "us", "yes", "less", "across", "says", "ships", "falls", "reads", "holds",
    "runs", "passes", "fails", "means", "keeps", "takes", "needs", "gives", "makes"})
#: A number that names a thing rather than counting: "step 8", "phase 386".
_NAMING = re.compile(r"(?:\b(?:step|item|phase|phases|row|line|lines|port|schema|migration|version|"
                     r"rule|check|gate|question|fix|item|section|page|chapter|option|round)\s+|[#FK])$",
                     re.I)
_ARITH = re.compile(r"[×*+=/÷−]\s*$|^\s*[×*+=/÷−]")
_YEAR = re.compile(r"^(?:19|20)\d\d$")
#: What shows a query: a backticked command, script or SQL.
QUERY = re.compile(
    r"`[^`]*(?:\b(?:grep|git|sed|wc|find|ls|sqlite3|select|SELECT|python3?|pytest|gh|curl|jq|"
    r"claude|cat|head|tail|rg|awk|shasum|sha256sum|nc|launchctl|tailscale|Tailscale|GET|ssh|"
    r"stat|du|sort|uniq|diff|systemctl|env|len)\b|\.py\b|\.sh\b)[^`]*`")


def counts_in(text: str) -> list[str]:
    plain = re.sub(r"`[^`]*`", "", text)
    found = []
    for m in COUNT.finditer(plain):
        num, before, after = m.group(1), plain[:m.start()], plain[m.end(1):m.end(1) + 3]
        if (m.group("noun") in NOT_COUNTED or _YEAR.match(num) or _NAMING.search(before)
                or _ARITH.search(before[-3:]) or _ARITH.search(after)):
            continue
        found.append(m.group(0).replace("\n", " "))
    return found


def unshown_counts(step0: str) -> list[str]:
    """Each count whose block (or, for a table row, its table's lead
    paragraph) shows no query."""
    bad = []
    for b in blocks(step0):
        found = counts_in(b.text)
        if found and not QUERY.search(b.text) and not (b.kind == "row" and QUERY.search(b.lead)):
            bad.append(f"{found[0]!r} in {b.text.strip()[:90]!r}")
    return bad


# --------------------------------------------------------- P5 content kinds
_DATA_PATH = re.compile(r"(?<![\w./~-])(?:\./)?data/")
_SEED_PHRASE = re.compile(r"\bseed[- ](?:data|files?|json|entr(?:y|ies)|rows?|content)\b", re.I)
_SPLIT = re.compile(r"\b(?:train(?:ing)?[/ -](?:test|val(?:idation)?)|test|validation|holdout|"
                    r"scaffold|random|temporal|data)[ -]splits?\b|\bsplit (?:logic|protocol)\b", re.I)
_EVAL = re.compile(r"\beval(?:uation)? (?:protocol|harness|set)s?\b", re.I)
_NON_GOALS = re.compile(r"non[- ]goals?", re.I)


def content_named(plan: str) -> list[str]:
    body = without_sections(plan, _NON_GOALS)
    seed_paths = [p for p in CONTENT_PATHS if "seed" in p]
    hits = []
    for label, found in (("a path under data/", _DATA_PATH.search(body)),
                         ("the knowledge content path", next((p for p in seed_paths if p in body), None)),
                         ("seed data", _SEED_PHRASE.search(body)),
                         ("a split", _SPLIT.search(body)),
                         ("an eval protocol", _EVAL.search(body))):
        if found:
            shown = found if isinstance(found, str) else found.group(0)
            hits.append(f"{label} ({shown!r})")
    return hits


# ---------------------------------------------------------------- P6 stubs
#: A line that is a stub: it starts with one of these, after any list marker
#: or emphasis. Matching anywhere in a line would fail the plan that names
#: the stub words to describe this check.
_STUB = re.compile(r"^(?:[-*+]\s+|\d+\.\s+|\[[ x]\]\s+)*[*_]*(?:TBD|TODO|to be written|"
                   r"placeholder|fill(?:ed)? in later|coming soon|\(empty\)|…|\.\.\.)(?:\W|$)",
                   re.I)
REQUIRED_SECTIONS = ("Goal", "Logic")


def classification(step0: str) -> str | None:
    """P4's word: the step-0 report's `Classification:`, lower-cased."""
    m = re.search(r"^\W*Classification\W*\s*(\w+)", step0, re.M | re.I)
    return m.group(1).lower() if m else None


def unfilled(plan: str) -> list[str]:
    bad = []
    secs = sections(plan)
    for lvl, title, body in secs:
        if lvl == 1:
            continue
        content = [ln for ln in body if ln.strip() and ln.strip() != "---"
                   and not re.match(r"^#{1,6}\s", ln)]
        if not content:
            bad.append(f"section {title!r} is empty")
        for ln in body:
            if _STUB.match(ln.strip()):
                bad.append(f"section {title!r} has a stub: {ln.strip()[:60]!r}")
    present = {t for lvl, t, _ in secs if lvl == 2}
    bad += [f"no '## {r}' section" for r in REQUIRED_SECTIONS
            if not any(t == r or t.startswith(r + " ") for t in present)]
    return list(dict.fromkeys(bad))


# ----------------------------------------------------------- P7 change log
_ENTRY = re.compile(r"^### (\d{4}-\d{2}-\d{2}) — (.+)$")
_TEXT_ONLY = re.compile(r"text only|no check", re.I)
_NO_CHECK = re.compile(r"\bno check\b", re.I)


def changelog(claude_md: str) -> list[tuple[str, str, str]]:
    """(date, title, body) for each entry under '## Change log', newest first."""
    lines = claude_md.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"^## Change log\s*$", ln)), None)
    if start is None:
        return []
    entries, cur = [], None
    for ln in lines[start + 1:]:
        if re.match(r"^## ", ln):
            break
        m = _ENTRY.match(ln)
        if m:
            cur = [m.group(1), m.group(2).strip(), []]
            entries.append(cur)
        elif cur is not None:
            cur[2].append(ln)
    out = [(d, t, "\n".join(b)) for d, t, b in entries]
    return sorted(out, key=lambda e: e[0], reverse=True)


def _paths(text: str) -> list[str]:
    toks = []
    for span in re.findall(r"`([^`\s]+)`", text):
        span = span.split("::")[0].rstrip(":,.")
        if "/" in span or re.search(r"\.\w{1,4}$", span):
            toks.append(span)
    return toks


def changelog_gaps(plan: str, claude_md: str, src: Source) -> list[str]:
    newest = changelog(claude_md)[:3]
    if len(newest) < 3:
        return [f"CLAUDE.md's change log has {len(newest)} entries, not three"]
    bad = []
    plan_blocks = blocks(plan)
    for date, title, body in newest:
        citing = [b for b in plan_blocks if date in b.text]
        if not citing:
            bad.append(f"the change-log entry {date} ({title[:50]}) is not cited")
            continue
        ok = any(any(src.exists(p) for p in _paths(b.text)) for b in citing) or (
            _TEXT_ONLY.search(body) and any(_NO_CHECK.search(b.text) for b in citing))
        if not ok:
            bad.append(f"the change-log entry {date} is cited without the check it became: no "
                       "backticked path that exists, and 'no check' only for an entry that says "
                       "it is text only")
    return bad


# ----------------------------------------------------------------- P8 stops
_STOPS = re.compile(r"\bstops?\b", re.I)
_KINDS = {
    "a real fork": re.compile(r"\bfork\b|two plans", re.I),
    "a threshold or a rule's definition": re.compile(r"threshold|rule'?s definition|definition", re.I),
    "a test it cannot make green": re.compile(r"\btests?\b.*\b(?:green|red)\b", re.I | re.S),
    "a login or a credential": re.compile(r"log-?in|credential|password|sign[- ]in|account", re.I),
    "a live-database change": re.compile(r"live[- ]database|live db|live rows?|on live|migration", re.I),
    "none expected": re.compile(r"^\W*none\b", re.I),
}


def stop_gaps(plan: str) -> list[str]:
    secs = [(t, body) for lvl, t, body in sections(plan) if lvl >= 2 and _STOPS.search(t)]
    if not secs:
        return ["no section listing the rule-1 stops the plan anticipates"]
    bullets = [b.text for _, body in secs for b in blocks("\n".join(body)) if b.kind == "bullet"]
    if not bullets:
        return [f"the section {secs[0][0]!r} lists no stops"]
    return [f"a stop that is none of rule 1's five kinds: {b.strip()[:80]!r}"
            for b in bullets if not any(k.search(re.sub(r"^\s*[-*+]\s+|^\s*\d+\.\s+", "", b))
                                        for k in _KINDS.values())]


_KID = re.compile(r"\bK(\d{1,3})\b")
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def record_gaps(phase: str, plan: str, src: Source) -> list[str]:
    """P9: what in the plan puts the phase in order, by the record's own
    words; [] when something does."""
    por, dec = src.read(plan_order.PLAN), src.read(plan_order.DECISIONS)
    if por is None or dec is None:
        return [f"cannot read {plan_order.PLAN if por is None else plan_order.DECISIONS}"]
    kids = {f"K{n}" for n in _KID.findall(plan)}
    days = set(_DATE.findall(plan))
    entry = next((e for e in plan_order.parse_order(por).entries if e.phase == phase), None)
    if (any(d.kid in kids and plan_order.names(f"{d.words} {d.check}", phase)
            for d in plan_order.decisions(dec))
            or any(day[:10] in days and plan_order.names(body, phase)
                   for day, _, body in plan_order.changes(por))
            or (entry is not None and kids & set(entry.kids))):
        return []
    return [f"the plan names no plan-of-record entry or K-id that puts phase {phase} in order: "
            f"cite a K-id from {plan_order.DECISIONS} whose row names it, the date of an entry "
            f"under 'Changes to the order' that names it, or its 'Next, in order' row's K-id"]


def unblocks_gaps(phase: str, plan: str, src: Source, status: dict[str, str]) -> list[str]:
    """P10: a fleet-only phase names the first-shop phase it unblocks (K43)."""
    por = src.read(plan_order.PLAN) or ""
    entry = next((e for e in plan_order.parse_order(por).entries if e.phase == phase), None)
    fleet_only = (entry.kind == "fleet" if entry is not None else
                  ".claude/skills/fleet/" in plan
                  and "src/" not in without_sections(plan, _NON_GOALS))
    if not fleet_only:
        return []
    shop = [p for p in plan_order.first_shop(por) if status.get(p) != DONE]
    said = [ln for ln in plan.splitlines() if re.search(r"\bunblock", ln, re.I)]
    if any(plan_order.names(ln, p) for ln in said for p in shop):
        return []
    return [f"a fleet-only phase names no first-shop phase it unblocks (K43): a line saying "
            f"'Unblocks' with one of {', '.join(shop) or '(none open)'}"]


# ------------------------------------------------------------------ the run
@dataclass
class Report:
    phase: str
    failed: dict[str, list[str]] = field(default_factory=dict)
    skipped: dict[str, str] = field(default_factory=dict)
    unreadable: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed and not self.unreadable

    def lines(self) -> list[str]:
        out = [f"CANNOT READ {u}" for u in self.unreadable]
        for i in ITEM_IDS:
            if i in self.failed:
                out += [f"{i} FAIL {why}" for why in self.failed[i]]
            elif i in self.skipped:
                out.append(f"{i} skipped: {self.skipped[i]}")
            elif not self.unreadable:
                out.append(f"{i} pass")
        return out


def check(phase: str, root: pathlib.Path = ROOT, rev: str | None = None,
          pin: bool = True) -> Report:
    src = Source(root, rev)
    rep = Report(phase)
    impl_path, step0_path = plan_paths(phase)
    roadmap, claude_md, plan = (src.read("docs/ROADMAP.md"), src.read("CLAUDE.md"),
                                src.read(impl_path))
    for name, txt in (("docs/ROADMAP.md", roadmap), ("CLAUDE.md", claude_md), (impl_path, plan)):
        if txt is None:
            rep.unreadable.append(name + (f" at {rev}" if rev else ""))
    if rep.unreadable:
        return rep
    step0 = src.read(step0_path)
    pinned = (WRITTEN_BEFORE.get(phase, frozenset()) | BEFORE_THE_RECORD.get(phase, frozenset())
              if pin else frozenset())

    def fail(item: str, whys: list[str]) -> None:
        if not whys:
            return
        if item in pinned:
            rep.skipped[item] = "written before plan_check (pinned); would fail: " + "; ".join(whys)
        else:
            rep.failed[item] = whys

    status = {n: s for n, s in reversed(rows(roadmap))}
    if phase not in status:
        fail("P1", [f"no ROADMAP row for phase {phase}"])
    elif status[phase] != ACTIVE:
        fail("P1", [f"row {phase} is {status[phase]!r}, not {ACTIVE}"])

    if step0 is None:
        fail("P2", [f"no {step0_path}"])
        rep.skipped.setdefault("P3", "no step-0 report to read")
        rep.skipped.setdefault("P4", "no step-0 report to read")
    else:
        fail("P3", [f"a count with no query shown: {c}" for c in unshown_counts(step0)])
        word = classification(step0)
        if word is None:
            fail("P4", ["the step-0 report has no 'Classification:' line"])
        elif word == "reshape":
            fail("P4", ["the step-0 classification is reshape, which goes to the Admiral"])
        elif word not in ("greenfield", "extension"):
            fail("P4", [f"the step-0 classification is {word!r}, not greenfield or extension"])

    fail("P5", [f"the plan names {h}" for h in content_named(plan)])
    fail("P6", unfilled(plan))
    fail("P7", changelog_gaps(plan, claude_md, src))
    fail("P8", stop_gaps(plan))
    fail("P9", record_gaps(phase, plan, src))
    fail("P10", unblocks_gaps(phase, plan, src, status))
    if pin:
        for item in pinned - set(rep.skipped):
            rep.skipped[item] = "written before plan_check (pinned); passes anyway"
    return rep


GOOD = HERE / "fixtures" / "good"
CASES = HERE / "fixtures" / "bad" / "cases.json"
FIXTURE_PHASE = "900"


def bad_cases() -> list[dict]:
    return json.loads(CASES.read_text(encoding="utf-8"))["cases"]


def apply_case(case: dict, dest: pathlib.Path) -> pathlib.Path:
    """The good tree copied to `dest` with the case's one edit made.
    Raises unless `old` occurs exactly once, so no case can do nothing."""
    shutil.copytree(GOOD, dest)
    target = dest / case["file"]
    if case["new"] is None:
        target.unlink()
        return dest
    text = target.read_text(encoding="utf-8")
    if text.count(case["old"]) != 1:
        raise ValueError(f"case {case['id']}: its old text occurs {text.count(case['old'])} "
                         f"times in {case['file']}, not once")
    target.write_text(text.replace(case["old"], case["new"]), encoding="utf-8")
    return dest


def self_test() -> int:
    """The good tree passes, and each known-bad case fails on its own item
    and on no other."""
    ok = check(FIXTURE_PHASE, GOOD).ok
    print(f"  the good tree passes: {ok}")
    with tempfile.TemporaryDirectory() as tmp:
        for case in bad_cases():
            rep = check(FIXTURE_PHASE, apply_case(case, pathlib.Path(tmp) / case["id"]))
            right = set(rep.failed) == {case["item"]} and not rep.unreadable
            ok &= right
            print(f"  {case['id']}: fails {sorted(rep.failed) or 'nothing'}"
                  f"{'' if right else '  <-- expected only ' + case['item']}")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("phase")
    ap.add_argument("--repo", type=pathlib.Path, default=ROOT)
    ap.add_argument("--rev")
    ap.add_argument("--no-pin", action="store_true", help="apply every item, even to a pinned plan")
    a = ap.parse_args(argv)
    rep = check(a.phase, a.repo, a.rev, pin=not a.no_pin)
    for ln in rep.lines():
        print(ln)
    if rep.unreadable:
        print(f"plan_check {a.phase}: CANNOT READ")
        return 2
    print(f"plan_check {a.phase}: " + ("PASS" if rep.ok else
                                       f"FAIL ({', '.join(sorted(rep.failed))})"))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
