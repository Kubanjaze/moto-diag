"""The Red Team: a fresh refute of a phase's pull request.

Phase 389. Opus, a fresh `claude -p` that did not build the phase, with
387's read-only tools so it can open every source it refutes against. The
script gathers what no model should be trusted to produce:

- `closeout_check.check` on the branch (A1–A8);
- the F9 lint, `scripts/check_f9_patterns.py --all`, run model-free in the
  fence by the caller (it imports the clone's code);
- the plan as approved (at its plan commit) and as it stands, and their
  diff: v1.1's Deviations are checked against what changed;
- the branch's diff from `master`, by file;
- what the plan of record and `docs/decisions.md` say on the phase
  (`plan_order.brief_block`, Phase 392).

The model returns `clear` or `back`, its findings, and a `## Refuter pass`
table, which must pass `refute_check.check` (C1–C7) or the stage stops.
**For a repository file the page is its line number**
(`docs/FOLLOWUPS.md p. 3677` is line 3677): C4 asks every row for a page,
and a text file has none (decided in Phase 389's log).
Three rounds at most (K9); the caller counts them.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "closeout"))
sys.path.insert(0, str(HERE.parent / "refute"))
import closeout_check  # noqa: E402
import plan_order  # noqa: E402
import rank_call  # noqa: E402
import refute_check  # noqa: E402
from rank_call import OPUS, Runner, Stop  # noqa: E402

MAX_ROUNDS = 3
CLEAR, BACK = "clear", "back"
SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"enum": [CLEAR, BACK]},
        "findings": {"type": "array", "items": {
            "type": "object",
            "properties": {"claim": {"type": "string"},
                           "kind": {"enum": ["wording", "factual", "citation", "code"]},
                           "what_is_wrong": {"type": "string"},
                           "where": {"type": "string"}},
            "required": ["claim", "kind", "what_is_wrong", "where"],
            "additionalProperties": False}},
        "refuter_pass": {"type": "string"},
    },
    "required": ["verdict", "findings", "refuter_pass"],
    "additionalProperties": False,
}

BRIEF = """\
You are the Red Team of the MotoDiag fleet: a fresh reviewer who did not
build this phase. Your job is refutation, not review: for each claim the
pull request makes, look for the sentence or the line that makes it false.
When you find nothing, the claim is kept, not confirmed. You are read-only:
Read, Grep and Glob the repository to open every source you check against.
Every citation is opened, not remembered.

Refute, in this order:
1. Every factual claim in v1.1 (Results, Deviations), the phase log's
   entries since the plan, and the handoff: counts, file paths, line
   numbers, F-numbers, K-ids, commands and what they printed. A cited
   F-number must say what the claim says it says (docs/FOLLOWUPS.md).
2. v1.1's Deviations against the diff of v1.0 to v1.1 and the branch's
   diff from master (below): anything the diff did that neither the plan
   nor Deviations says is a finding.
3. The F9 checks: the lint's output below, and the subspecies in
   docs/patterns/f9-mock-vs-runtime-drift.md against the tests the phase
   added (a mock or a fixture that cannot drift from what runs).
4. A1–A8: the close-out check's output below; anything it reports.
5. The plan of record's and docs/decisions.md's words on this phase, at
   the end: a claim that contradicts them, a K-id or dated entry cited for
   what it does not say, or work no entry puts in order, is a finding.

Return:
- verdict: "back" if any finding is factual, a citation, or code;
  "clear" if there are none, or only wording.
- findings: each with the claim, its kind, what is wrong and where.
- refuter_pass: the phase log's refute table, exactly in this form:

## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| <the claim> | kept or killed | "<verbatim quote from the source>" | <path> p. <line> | {ROUND} · none, wording, factual or citation · kept, fixed, deleted or open |

For a repository file the page is its line number ("docs/FOLLOWUPS.md p.
3677" means line 3677). Every row has a verdict, a quote in quotation
marks, a source with a page, and the last column. A killed row's outcome
is open until the Engineer fixes it.
"""


def _git(clone: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True).stdout


def plan_commit(clone: pathlib.Path, phase: str) -> str | None:
    """The commit that first added the phase's plan: the Captain's v1.0."""
    out = _git(clone, "log", "--diff-filter=A", "--format=%H", "--",
               f"docs/phases/in_progress/{phase}_implementation.md").split()
    return out[-1] if out else None


def gather(clone: pathlib.Path, phase: str, f9_output: str, base: str = "origin/master") -> str:
    """The context the model reads, all of it produced by script."""
    impl_now = next((p for p in (clone / "docs" / "phases" / d / f"{phase}_implementation.md"
                                 for d in ("completed", "in_progress")) if p.is_file()), None)
    pc = plan_commit(clone, phase)
    v10 = _git(clone, "show", f"{pc}:docs/phases/in_progress/{phase}_implementation.md") if pc else ""
    v11 = impl_now.read_text(encoding="utf-8") if impl_now else ""
    a = closeout_check.check(clone, phase)
    diff_names = _git(clone, "diff", "--stat", f"{base}...HEAD")
    plan_diff = "(no plan commit found)"
    if pc and impl_now:
        plan_diff = subprocess.run(
            ["git", "-C", str(clone), "diff", f"{pc}", "HEAD", "-M", "--",
             f"docs/phases/in_progress/{phase}_implementation.md",
             f"docs/phases/completed/{phase}_implementation.md"],
            capture_output=True, text=True).stdout
    return (f"=== closeout_check.py . {phase} (A1–A8) ===\n" + ("\n".join(a) or "(nothing: complete)")
            + f"\n\n=== scripts/check_f9_patterns.py --all ===\n{f9_output.strip()}"
            + f"\n\n=== the branch's diff from master, by file ===\n{diff_names.strip()}"
            + f"\n\n=== v1.0 as approved ({(pc or 'not found')[:12]}) ===\n{v10}"
            + f"\n\n=== the diff of v1.0 to v1.1 ===\n{plan_diff}"
            + f"\n\n=== v1.1 as it stands ===\n{v11}"
            + f"\n\n{plan_order.brief_block(clone, phase)}")


def review(phase: str, rnd: int, context: str, *, clone: pathlib.Path, run: Runner,
           model: str = OPUS) -> tuple[dict, rank_call.Call]:
    """One round. The verdict, its findings and a table that passes C1–C7."""
    c = rank_call.call("red-team", BRIEF.replace("{ROUND}", str(rnd)) + "\n" + context, model,
                       SCHEMA, cwd=clone, run=run, timeout=3600)
    v = c.structured
    if v.get("verdict") not in (CLEAR, BACK):
        raise Stop(f"no verdict in {sorted(v)}")
    findings = v.get("findings")
    if not isinstance(findings, list):
        raise Stop("the findings are not a list")
    blocking = [f for f in findings if f.get("kind") in ("factual", "citation", "code")]
    if v["verdict"] == CLEAR and blocking:
        raise Stop(f"clear, with {len(blocking)} factual, citation or code findings")
    if v["verdict"] == BACK and not findings:
        raise Stop("back, with no findings")
    table = str(v.get("refuter_pass", ""))
    # C6 ("no factual or citation defect is still open: the row does not
    # ship") holds a table that ships, the one a clear commits. On a back the
    # killed rows are open by definition: the Engineer has not fixed them yet
    # (Phase 389, bug fix #2: the planted-bug proof's first round).
    bad = [f for f in refute_check.check(table)
           if not (v["verdict"] == BACK and f.startswith("C6 "))]
    if bad:
        raise Stop("the refute table fails the checklist: " + "; ".join(bad)[:400])
    return v, c


def findings_text(v: dict) -> str:
    return "\n".join(f"- [{f['kind']}] {f['claim']}: {f['what_is_wrong']} ({f['where']})"
                     for f in v.get("findings", [])) or "- none"


def record_in_log(clone: pathlib.Path, phase: str, table: str) -> str:
    """The cleared table into the branch's phase log (A8), replacing a
    'No refute pass ran' line or an earlier table. Returns the log's path."""
    for d in ("completed", "in_progress"):
        log = clone / "docs" / "phases" / d / f"{phase}_phase_log.md"
        if log.is_file():
            break
    else:
        raise Stop(f"no phase log for {phase} to record the refute in")
    text = log.read_text(encoding="utf-8")
    head = refute_check.find_block(text)
    if head is not None:
        rest = text[head.start():]
        nxt = rest.find("\n## ", len("## Refuter pass"))
        text = text[:head.start()] + (rest[nxt + 1:] if nxt != -1 else "")
    text = "\n".join(ln for ln in text.splitlines() if ln.strip() != "No refute pass ran.")
    log.write_text(text.rstrip("\n") + "\n\n" + table.strip() + "\n", encoding="utf-8")
    return str(log.relative_to(clone))
