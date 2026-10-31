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

**An open wording defect** (Phase 392, F228). C7 asks each one to cite the
one finding open wording defects go to (K9: "after round 3, remaining
wording defects go to one finding"); this rank is read-only and cannot
file it. So the brief says so in its own words: leave such a row `open`
with no F-number. On a back before the last round the table does not ship
and the Engineer may still fix the wording, so C7 is set aside there, as
C6 is. On a clear, or a back in the last round, `review` checks the table
as it will be written (`with_finding`), and the dispatcher files the
finding (`wording_entry`, the next number over both repositories) and
writes its number into each row.
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "closeout"))
sys.path.insert(0, str(HERE.parent / "refute"))
sys.path.insert(0, str(HERE.parents[2] / "scripts"))
import closeout_check  # noqa: E402
import code_quality  # noqa: E402
import plan_order  # noqa: E402
import rank_call  # noqa: E402
import refute_check  # noqa: E402
from rank_call import OPUS, Runner, Stop  # noqa: E402

MAX_ROUNDS = 3
CLEAR, BACK = "clear", "back"

#: Phase 393 (K54): the five questions asked of the code. Each is worded so
#: that "yes" is sound and "no" a defect: "A 'no' with a file and line is a
#: factual defect under K9."
QUESTIONS = {
    1: "Is every new public function reached from the CLI or the API, or listed on the "
       "integration-gap allowlist (tests/support/integration_gaps_allowlist.py) with its "
       "reason?",
    2: "Does the diff avoid a new private money, time or constant helper where one module "
       "should own it?",
    3: "Does every new exception handler name the error it expects, rather than swallow "
       "whatever comes?",
    4: "Do the new tests check behaviour, rather than only that some text exists?",
    5: "If it touches auth/, payments/, billing/, api/uploads.py or memory/erase.py: is "
       "nothing newly reachable by a caller without the right role or tier?",
}
SENSITIVE = ("src/motodiag/auth/", "src/motodiag/payments/", "src/motodiag/billing/",
             "src/motodiag/api/uploads.py", "src/motodiag/memory/erase.py")
_HELPER = re.compile(r"^_+(?:money|now|utcnow|cents|dollars|fmt_money|format_money)\w*$")
CHECKLIST_SCHEMA = {"type": "array", "items": {
    "type": "object",
    "properties": {"question": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                   "answer": {"enum": ["yes", "no", "not-applicable"]},
                   "where": {"type": "string"}, "why": {"type": "string"}},
    "required": ["question", "answer", "where", "why"], "additionalProperties": False}}
_WHERE = re.compile(r"\S+:\d+")

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
        "code_checklist": CHECKLIST_SCHEMA,
    },
    "required": ["verdict", "findings", "refuter_pass", "code_checklist"],
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
6. The code itself (Phase 393, K54). Ask these five questions of the
   branch's diff from master, and answer each one in code_checklist:
   "yes", "no" or "not-applicable", with the file and line that shows it
   ("src/motodiag/x.py:42") and one sentence why:
{QUESTIONS}
   A "no" is a factual defect (K9): give it also as a finding of kind
   "code", and the verdict is "back". The script's scan of the added lines,
   below the diff, already answers some with "no"; each of those stands,
   whatever you find.

Return:
- verdict: "back" if any finding is factual, a citation, or code;
  "clear" if there are none, or only wording.
- findings: each with the claim, its kind, what is wrong and where.
- code_checklist: the five answers, one per question.
- refuter_pass: the phase log's refute table, exactly in this form:

## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| <the claim> | kept or killed | "<verbatim quote from the source>" | <path> p. <line> | {ROUND} · none, wording, factual or citation · kept, fixed, deleted or open |

For a repository file the page is its line number ("docs/FOLLOWUPS.md p.
3677" means line 3677). Every row has a verdict, a quote in quotation
marks, a source with a page, and the last column. A killed row's outcome
is open until the Engineer fixes it.

A wording defect you leave open is written "open" with no F-number after
it. You cannot file a finding (you are read-only), and you never write an
F-number of your own choosing. The rule the checker holds (K9): every
wording defect left open goes to one finding, whose number each such row
must cite. After your round, a script outside you files that one finding
and writes its number into each of those rows. A factual or citation
defect is never left for a finding: it is "back".
"""


def _git(clone: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True).stdout


def plan_commit(clone: pathlib.Path, phase: str, approved_at: str | None = None) -> str | None:
    """The plan of record (Phase 396, (d)): the newest commit that changed the
    phase's plan at or before `approved_at`, when `plan:approved` was last
    applied, by committer date. With no time, the commit that first added it:
    on 348 that was the Captain's draft, which the operator's commits had
    rewritten before the approval, so the callers name which one they read."""
    path = f"docs/phases/in_progress/{phase}_implementation.md"
    if approved_at is None:
        out = _git(clone, "log", "--diff-filter=A", "--format=%H", "--", path).split()
        return out[-1] if out else None
    out = _git(clone, "log", "-1", f"--before={approved_at}", "--format=%H", "--", path).split()
    return out[0] if out else None


def plan_label(pc: str | None, approved_at: str | None) -> str:
    """How a brief names the plan it hands on (Phase 396, (d))."""
    if pc is None:
        return "not found"
    if approved_at is None:
        return (f"{pc[:12]}, the plan's first commit: plan:approved was never applied on the "
                "issue")
    return f"{pc[:12]}, the plan when plan:approved was last applied, {approved_at}"


def _broad(h: ast.ExceptHandler) -> bool:
    return h.type is None or (isinstance(h.type, ast.Name)
                              and h.type.id in ("Exception", "BaseException"))


def _swallows(h: ast.ExceptHandler) -> bool:
    return all(isinstance(b, (ast.Pass, ast.Continue))
               or (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant))
               for b in h.body)


def code_scan(clone: pathlib.Path, base: str = "origin/master") -> dict:
    """What a script can answer of the five questions, over the lines the
    branch adds under src/: {"no": [{question, where, why}], "public",
    "sensitive", "tests"}. A "no" here is a factual defect whatever the
    model says (questions 2 and 3); the rest is handed to the model."""
    changed = code_quality.changed_lines(clone, base)
    no, public = [], []
    for path, lines in sorted(changed.items()):
        try:
            tree = ast.parse((clone / path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for n in ast.walk(tree):
            if (isinstance(n, ast.ExceptHandler) and n.lineno in lines and _broad(n)
                    and _swallows(n)):
                what = "a bare `except:`" if n.type is None else f"`except {n.type.id}`"
                no.append({"question": 3, "where": f"{path}:{n.lineno}",
                           "why": f"{what} whose body only passes: it swallows every error "
                                  "without naming the one it expects"})
            if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.lineno in lines
                    and _HELPER.match(n.name)):
                no.append({"question": 2, "where": f"{path}:{n.lineno}",
                           "why": f"a new private money or time helper, `{n.name}`"})
        public += [f"{path}:{n.lineno} {n.name}" for n in tree.body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.lineno in lines and not n.name.startswith("_")]
    names = _git(clone, "diff", "--name-only", f"{base}...HEAD").split()
    return {"no": no, "public": public,
            "sensitive": [p for p in names if p.startswith(SENSITIVE)],
            "tests": [p for p in names if p.startswith("tests/") and p.endswith(".py")]}


def scan_text(scan: dict) -> str:
    def block(items: list[str]) -> str:
        return "\n".join(f"- {x}" for x in items) or "- (none)"
    return ("=== the code checklist: the script's scan of the added lines ===\n"
            "Already a \"no\" (questions 2 and 3):\n"
            + block([f"question {x['question']}, {x['where']}: {x['why']}" for x in scan["no"]])
            + "\nNew public functions (question 1):\n" + block(scan["public"])
            + "\nFiles under auth/, payments/, billing/, api/uploads.py, memory/erase.py "
              "(question 5):\n" + block(scan["sensitive"])
            + "\nTest files changed (question 4):\n" + block(scan["tests"]))


def brief(rnd: int) -> str:
    return BRIEF.replace("{ROUND}", str(rnd)).replace(
        "{QUESTIONS}", "\n".join(f"   {k}. {q}" for k, q in QUESTIONS.items()))


def gather(clone: pathlib.Path, phase: str, f9_output: str, base: str = "origin/master",
           scan: dict | None = None, approved_at: str | None = None) -> str:
    """The context the model reads, all of it produced by script."""
    impl_now = next((p for p in (clone / "docs" / "phases" / d / f"{phase}_implementation.md"
                                 for d in ("completed", "in_progress")) if p.is_file()), None)
    pc = plan_commit(clone, phase, approved_at)
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
            + (f"\n\n{scan_text(scan)}" if scan is not None else "")
            + (f"\n\n=== v1.0 as approved ({plan_label(pc, approved_at)}) ===\n{v10}"
               if approved_at is not None else
               f"\n\n=== v1.0 ({plan_label(pc, approved_at)}) ===\n{v10}")
            + f"\n\n=== the diff of v1.0 to v1.1 ===\n{plan_diff}"
            + f"\n\n=== v1.1 as it stands ===\n{v11}"
            + f"\n\n{plan_order.brief_block(clone, phase)}")


def checklist_nos(v: dict, scan: dict | None) -> list[dict]:
    """The code checklist's "no" answers, the model's and the script's, as
    findings of kind "code" (Phase 393). Stops on a checklist that does not
    answer each of the five questions once, or a "no" with no file and line."""
    cl = v.get("code_checklist")
    if not isinstance(cl, list) or not all(isinstance(a, dict) for a in cl):
        raise Stop("no code checklist")
    asked = sorted(a.get("question") for a in cl if isinstance(a.get("question"), int))
    if asked != sorted(QUESTIONS):
        raise Stop(f"the code checklist answers questions {asked}, not each of 1-5 once")
    out = []
    for a in cl:
        if a.get("answer") == "no":
            if not _WHERE.search(str(a.get("where", ""))):
                raise Stop(f"a \"no\" to code question {a['question']} names no file and line")
            out.append({"claim": f"code question {a['question']}: {QUESTIONS[a['question']]}",
                        "kind": "code", "what_is_wrong": str(a.get("why", "")),
                        "where": str(a["where"])})
    for s in (scan or {}).get("no", []):
        if not any(f["where"] == s["where"] for f in out):
            out.append({"claim": f"code question {s['question']}: {QUESTIONS[s['question']]}",
                        "kind": "code", "what_is_wrong": f"{s['why']} (found by script)",
                        "where": s["where"]})
    return out


def review(phase: str, rnd: int, context: str, *, clone: pathlib.Path, run: Runner,
           model: str = OPUS, scan: dict | None = None) -> tuple[dict, rank_call.Call]:
    """One round. The verdict, its findings and a table that passes C1–C7.
    A "no" on the code checklist, the model's or the script's, makes it a
    back (Phase 393, K54: a factual defect under K9)."""
    c = rank_call.call("red-team", brief(rnd) + "\n" + context, model,
                       SCHEMA, cwd=clone, run=run, timeout=3600)
    v = c.structured
    if v.get("verdict") not in (CLEAR, BACK):
        raise Stop(f"no verdict in {sorted(v)}")
    findings = v.get("findings")
    if not isinstance(findings, list):
        raise Stop("the findings are not a list")
    nos = checklist_nos(v, scan)
    added = [f for f in nos if not any(f["where"] == g.get("where") for g in findings)]
    if added or nos:
        findings = [*findings, *added]
        v = {**v, "findings": findings, "verdict": BACK if nos else v["verdict"]}
    blocking = [f for f in findings if f.get("kind") in ("factual", "citation", "code")]
    if v["verdict"] == CLEAR and blocking:
        raise Stop(f"clear, with {len(blocking)} factual, citation or code findings")
    if v["verdict"] == BACK and not findings:
        raise Stop("back, with no findings")
    table = str(v.get("refuter_pass", ""))
    return check_table(v, table, rnd), c


def check_table(v: dict, table: str, rnd: int) -> dict:
    """The table against C1–C7, as it will stand; `v` gains `wording_open`,
    the rows the dispatcher files one finding for (F228)."""
    # C6 ("no factual or citation defect is still open: the row does not
    # ship") holds a table that ships, the one a clear commits. On a back the
    # killed rows are open by definition: the Engineer has not fixed them yet
    # (Phase 389, bug fix #2: the planted-bug proof's first round). C7 the
    # same before the last round: the wording may still be fixed (F228).
    back = v["verdict"] == BACK
    files = not back or rnd >= MAX_ROUNDS
    rows = open_wording(table) if files else []
    shown = with_finding(table, PLACEHOLDER) if rows else table
    bad = [f for f in refute_check.check(shown)
           if not (back and f.startswith("C6 ")) and not (not files and f.startswith("C7 "))]
    if bad:
        raise Stop("the refute table fails the checklist: " + "; ".join(bad)[:400])
    return {**v, "wording_open": rows}


#: Stands in for the finding's number while the table is checked; the
#: dispatcher writes the real one. Four digits, so C7's pattern reads it.
PLACEHOLDER = "F9999"


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def open_wording(table: str) -> list[dict]:
    """Each row whose outcome leaves a wording defect open with no F-number."""
    out = []
    block = table[refute_check.find_block(table).end():] if refute_check.find_block(table) else ""
    for line in block.split("\n## ", 1)[0].splitlines():
        m = refute_check._ROW.match(line)
        if not m or not m.group("rko"):
            continue
        k = refute_check._RKO.match(m.group("rko"))
        if k and k.group(2).lower() == "wording" and k.group(3).lower() == "open" and not k.group(4):
            out.append({"line": line, "claim": m.group("claim").strip(),
                        "quote": m.group("quote").strip(), "source": m.group("source").strip()})
    return out


def with_finding(table: str, fnum: str) -> str:
    """The table with `fnum` after each open wording outcome that has none."""
    out = []
    for line in table.splitlines():
        m = refute_check._ROW.match(line)
        k = refute_check._RKO.match(m.group("rko")) if m and m.group("rko") else None
        if k and k.group(2).lower() == "wording" and k.group(3).lower() == "open" and not k.group(4):
            line = line[:m.start("rko")] + m.group("rko").rstrip() + f" {fnum} " + line[m.end("rko"):]
        out.append(line)
    return "\n".join(out) + ("\n" if table.endswith("\n") else "")


def wording_entry(fnum: str, phase: str, rnd: int, rows: list[dict], where: str) -> str:
    """The finding open wording defects go to, as `docs/FOLLOWUPS.md` holds it."""
    listed = "\n".join(f"- {r['claim']}: {r['quote']} ({r['source']})" for r in rows)
    return (f"### {fnum}\n\n**Wording the Red Team left open on phase {phase}, round {rnd}**\n\n"
            f"Filed by the fleet's dispatcher, not by the Red Team, which is read-only (Phase "
            f"392, F228). K9: \"after round 3, remaining wording defects go to one finding\". "
            f"The rows, from the refute table in {where}:\n\n{listed}\n\nWhat would close it: "
            f"a later phase that touches these documents fixes the wording, deleting a sentence "
            f"rather than rewriting it where it can (K9).\n")


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
