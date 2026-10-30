"""The Quartermaster: the last check before a merge, in shadow.

Phase 391, step 8 of the fleet proposal. On `merge:needs-review`, after the
Captain's recommendation, a fleet-built pull request is checked the way the
operator checks one before merging, and gets a verdict: **merge**, or
**refuse** naming each check that failed. **It never merges and sets no
label**: the operator merges by hand, and the digest sets the two verdicts
side by side.

Scripts run the checks; the model does not. The dispatcher runs, in the
fence with no model and no token, `wholetree.sh --full` and `regression.sh`
on the head, then `verify_phase.sh`. This module reads them, and checks
what those fourteen miss for a fleet-built PR (391 Step 0, S0-1):

  Q1 scope: extension or greenfield; no content or data path; a migration
     or a deploy only through the database step (Phase 395: its three files
     committed, the live diff clean, and verify-live, run by the dispatcher
     outside the fence, exiting 0). A failure is the verdict, with no run
     and no model call.
  Q2 the Captain's newest recommendation is merge
  Q3 the Red Team's newest verdict is clear, after the Engineer's newest
     pull request
  Q4 the full run on the head passed, counting what the regression of
     record counts
  Q5 verify_phase.sh, read check by check (V1-V14), never by its exit code
  Q6 the phase's commit claims are each in the head's history (S0-3)
  Q7 no stub in v1.1
  Q8 the handoff, and roadmap_check (R1-R8) on the branch
  Q9 the clone is clean and the head merges onto master with no conflict
  Q10 lint and types: no src/ file the PR touches has more ruff findings or
      mypy errors on the head than on master (Phase 393, K54)
  Q11 coverage: the lines the PR adds or changes in src/ are at least 85%
      covered by the full run on the head
  Q12 size: no new or changed function over McCabe 20; no src/ file grows
      past 100 KB, and none already over it grows

Q10 and Q12 are `scripts/code_quality.py pr`, run by the dispatcher in the
fence with no model and no network, with the base's copy of the script when
the base has one; Q11 reads the full run's coverage JSON.

Then one fresh, read-only Opus call reads the results and judges what no
script can: check 4's hits (a stub, or prose that uses the word) and the
v1.0 to v1.1 diff. **The script composes the verdict**: a scripted failure
refuses, whatever the model says; the model may add a refusal, naming a
check from the list, and nothing else.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "closeout"))
sys.path.insert(0, str(HERE.parents[2] / "scripts"))
import closeout_check  # noqa: E402
import code_quality  # noqa: E402
import engineer  # noqa: E402
import plan_check  # noqa: E402
import plan_order  # noqa: E402
import rank_call  # noqa: E402
import red_team  # noqa: E402
import roadmap_check  # noqa: E402
from rank_call import OPUS, Runner, Stop  # noqa: E402
from wholetree import CONTENT_PATHS  # noqa: E402

MERGE, REFUSE = "merge", "refuse"
VERIFY = ".claude/skills/closeout/verify_phase.sh"
MIGRATIONS = "src/motodiag/core/migrations.py"

CHECKS = {
    "Q1": "the phase is in scope",
    "Q2": "the Captain recommends merge",
    "Q3": "the Red Team's clear",
    "Q4": "the full run on the head",
    "Q5": "verify_phase.sh's fourteen",
    "Q6": "the claimed commits",
    "Q7": "no stub in v1.1",
    "Q8": "the handoff",
    "Q9": "it merges onto master",
    "Q10": "lint and types, per touched file",
    "Q11": "changed-line coverage",
    "Q12": "complexity and file size",
    "V1": "master pushed, tree clean", "V2": "no code after the regression hash",
    "V3": "docs in completed", "V4": "stubs", "V5": "deviations and the bug-fix register",
    "V6": "the row's words", "V7": "the findings header", "V8": "schema and live",
    "V9": "backup", "V10": "targeted tests", "V11": "the close-out contract",
    "V12": "the refuter checklist", "V13": "findings resolve",
    "V14": "the regression line names its command",
}
#: verify_phase.sh's checks the Quartermaster does not read before a merge, and why.
NOT_READ = {
    "V1": "it reads origin/master, which a pull request is not on yet; Q9 instead",
    "V7": "it prints a line and no verdict; V13 holds the header",
    "V8": "no live in the fence; Q1 runs verify-live outside it for a phase with a "
          "database step, and refuses any other migration or deploy",
    "V9": "as V8",
}

_CAPTAIN = re.compile(r"^<!-- fleet-captain: recommendation=(\w+)")
_RED = re.compile(r"^<!-- fleet-red-team: verdict=(\w+) round=(\d+)")
_PR_READY = re.compile(r"^<!-- fleet-engineer: pr-ready")
_SECTION = re.compile(r"^=== (\d+)\. .*===$", re.M)
_SUMMARY = re.compile(r"^=+ .* in [\d.]+s(?: \([\d:]+\))? =+$", re.M)
_RED_COUNT = re.compile(r"\b\d+ (?:failed|errors?)\b")
_HEX = re.compile(r"`([0-9a-f]{7,40})`")
#: The phase's own commit claims (S0-3): v1.0's commit in v1.1's header,
#: each Commit line, and the regression of record's commit.
CLAIMS = (re.compile(r"\(v1\.0 `([0-9a-f]{7,40})`"),
          re.compile(r"^\s*(?:[-*]\s*)?\*\*Commit[.:]\*\*:?\s*`([0-9a-f]{7,40})`", re.M),
          re.compile(r"^\s*(?:[-*]\s*)?Commit:\s*`([0-9a-f]{7,40})`", re.M),
          re.compile(rf"^{re.escape(closeout_check.PREFIX)} .*? at `([0-9a-f]{{7,40}})`", re.M))
_BOX = re.compile(r"^\s*[-*] \[ \]", re.M)


@dataclass
class Finding:
    """One check's result: ok True or False, or None for one not read."""
    check: str
    ok: bool | None
    why: str = ""

    def line(self) -> str:
        mark = {True: "pass", False: "FAIL", None: "not read"}[self.ok]
        return f"{self.check} {CHECKS[self.check]}: {mark}" + (f": {self.why}" if self.why else "")


def _git(clone: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True)


def doc(clone: pathlib.Path, phase: str, kind: str) -> pathlib.Path | None:
    """docs/phases/{completed,in_progress}/<phase>_<kind>.md, completed first."""
    return next((p for p in (clone / "docs" / "phases" / d / f"{phase}_{kind}.md"
                             for d in ("completed", "in_progress")) if p.is_file()), None)


def _text(p: pathlib.Path | None) -> str:
    return p.read_text(encoding="utf-8") if p is not None and p.is_file() else ""


# ----------------------------------------------------------------- Q1
def changed(clone: pathlib.Path, base: str) -> list[str]:
    return _git(clone, "diff", "--name-only", f"{base}...HEAD").stdout.split()


def database_step(clone: pathlib.Path, phase: str,
                  live_check: Callable[[], tuple[int, str]] | None) -> list[str]:
    """Why a migration did not go through the database step (Phase 395):
    the dry-run diff, the operator's answer and the live diff committed,
    the live diff with no scope problem and equal to the approved diff, and
    `verify-live`, run by the dispatcher outside the fence, exiting 0. With
    no `live_check` (in the fence, where live is not) it cannot pass."""
    why = []
    for kind in ("dryrun_diff", "deploy_answer", "live_diff"):
        p = doc(clone, phase, kind)
        if p is None or _git(clone, "cat-file", "-e",
                             f"HEAD:{p.relative_to(clone)}").returncode != 0:
            why.append(f"no committed {phase}_{kind}.md")
    live = _text(doc(clone, phase, "live_diff"))
    if live and ("**Scope problems:** `none`" not in live
                 or "**Equals the approved exact diff:** `yes`" not in live):
        why.append(f"{phase}_live_diff.md records a scope problem or a live database that is not "
                   "the approved diff")
    if live_check is None:
        why.append("verify-live was not run: no live in the fence")
    elif not why:
        rc, said = live_check()
        if rc != 0:
            why.append(f"verify-live exits {rc}: {said.strip().splitlines()[-1:] or ''}")
    return why


def scope(clone: pathlib.Path, phase: str, base: str = "master",
          live_check: Callable[[], tuple[int, str]] | None = None) -> Finding:
    why = []
    word = plan_check.classification(_text(doc(clone, phase, "step0")))
    if word not in ("extension", "greenfield"):
        why.append(f"the Step 0 classification is {word or 'missing'}, not extension or greenfield")
    paths = changed(clone, base)
    deploys = MIGRATIONS in paths or any(p.endswith("_dryrun_diff.md") for p in paths)
    step = database_step(clone, phase, live_check) if deploys else []
    why += [f"it changes {p}, a migration with no database step ({'; '.join(step)})"
            for p in paths if p == MIGRATIONS and step]
    why += [f"it changes {p}, content" for p in paths
            if p != MIGRATIONS and p.startswith(CONTENT_PATHS)]
    why += [f"it changes {p}, under data/" for p in paths if p.startswith("data/")]
    why += [f"it carries {p}, a live apply with no database step ({'; '.join(step)})"
            for p in paths if p.endswith("_dryrun_diff.md") and step]
    return Finding("Q1", not why, "; ".join(why))


# ------------------------------------------------------------- Q2, Q3
def _newest(comments: list[dict], pattern: re.Pattern) -> tuple[dt.datetime, re.Match, str] | None:
    found = [(dt.datetime.fromisoformat(c["createdAt"].replace("Z", "+00:00")), m, c["body"])
             for c in comments if (m := pattern.match(c.get("body", "").lstrip()))]
    return max(found, key=lambda x: x[0]) if found else None


def issue_checks(comments: list[dict]) -> tuple[list[Finding], dict[str, str]]:
    """Q2 and Q3 from the mission issue's comments, and the texts the model reads."""
    cap, red, ready = (_newest(comments, p) for p in (_CAPTAIN, _RED, _PR_READY))
    q2 = (Finding("Q2", False, "the issue carries no Captain's recommendation") if cap is None
          else Finding("Q2", cap[1].group(1) == MERGE,
                       "" if cap[1].group(1) == MERGE else f"the Captain recommends {cap[1].group(1)}"))
    if red is None:
        q3 = Finding("Q3", False, "the issue carries no Red Team verdict")
    elif red[1].group(1) != "clear":
        q3 = Finding("Q3", False, f"the Red Team's newest verdict is {red[1].group(1)} "
                                  f"(round {red[1].group(2)})")
    elif ready is not None and ready[0] > red[0]:
        q3 = Finding("Q3", False, "the Engineer's newest pull request came after the Red Team's clear")
    else:
        q3 = Finding("Q3", True)
    texts = {"captain": cap[2] if cap else "(none)", "red_team": red[2] if red else "(none)"}
    return [q2, q3], texts


# ----------------------------------------------------------------- Q4
def regression_hash(clone: pathlib.Path, phase: str) -> str | None:
    record = closeout_check.regression_line(_text(doc(clone, phase, "phase_log")), phase)
    return record[1] if record else None


def full_run(ok: bool, line: str | None, why: str, log_text: str) -> Finding:
    if not ok:
        return Finding("Q4", False, f"the full run did not pass: {line or why}"[:300])
    of_record = [ln for ln in log_text.splitlines() if closeout_check.PREFIX in ln]
    mine, theirs = engineer.counts(of_record[-1] if of_record else ""), engineer.counts(line or "")
    if mine is None:
        return Finding("Q4", False, "the phase log has no regression of record to compare")
    if mine != theirs:
        return Finding("Q4", False, f"the phase log's regression counts {mine} (passed, failed, "
                                    f"skipped); the full run on the head counts {theirs}")
    return Finding("Q4", True, line or "")


# ----------------------------------------------------------------- Q5
def verify_sections(text: str) -> dict[int, str]:
    marks = list(_SECTION.finditer(text))
    return {int(m.group(1)): text[m.end():(marks[i + 1].start() if i + 1 < len(marks)
                                           else len(text))].strip("\n")
            for i, m in enumerate(marks)}


def read_verify(text: str, phase: str) -> list[Finding]:
    """V1-V14 by S0-1's table: each section read by its own rule."""
    secs = verify_sections(text)
    out = []

    def rule(n: int, ok: bool, why: str = "") -> None:
        out.append(Finding(f"V{n}", ok, "" if ok else why))

    for n in range(1, 15):
        key = f"V{n}"
        if key in NOT_READ:
            out.append(Finding(key, None, NOT_READ[key]))
            continue
        s = secs.get(n)
        if s is None:
            out.append(Finding(key, False, "verify_phase.sh printed no such section"))
            continue
        if n == 2:
            rule(n, "none (docs only)" in s, s.strip()[:200])
        elif n == 3:
            listed, _, left = s.partition("--- in_progress (empty) ---")
            have = [ln for ln in listed.splitlines() if ln.startswith(f"{phase}_")]
            rule(n, bool(have) and not left.strip(),
                 "documents left in in_progress/" if left.strip() else "none in completed/")
        elif n == 4:
            out.append(Finding(key, True if s.strip() == "none" else None,
                               "" if s.strip() == "none" else "hits for the model to judge: "
                               + "; ".join(s.splitlines())[:300]))
        elif n == 5:
            rule(n, bool(re.search(r"^\d+:## .*[Dd]eviation", s, re.M)) and "A4 ok" in s,
                 "no Deviations heading, or the bug-fix register fails A4")
        elif n == 6:
            rule(n, "within cap" in s, s.strip()[:200])
        elif n == 10:
            rule(n, bool(_SUMMARY.search(s)) and not _RED_COUNT.search(s),
                 s.strip().splitlines()[-1][:200] if s.strip() else "no output")
        elif n == 11:
            rule(n, "closeout complete" in s, s.strip()[:300])
        elif n == 12:
            rule(n, "every row has a verdict, a quote and a page" in s,
                 "no refuter block that passes C1-C7: a fleet build's Red Team clear commits one")
        elif n == 13:
            rule(n, "every cited F-number resolves" in s, s.strip()[:200])
        elif n == 14:
            rule(n, "python -m pytest" in s and "no regression line names" not in s,
                 "no regression line names its command")
    return out


# ----------------------------------------------------------------- Q6
def claims(clone: pathlib.Path, phase: str, tip: str) -> tuple[Finding, list[str]]:
    """Q6, and every other hash cited, with whether it resolves (for the model)."""
    texts = [_text(doc(clone, phase, "implementation")), _text(doc(clone, phase, "phase_log"))]
    claimed = sorted({h for t in texts for c in CLAIMS for h in c.findall(t)})
    missing = [h for h in claimed if _git(clone, "merge-base", "--is-ancestor", h, tip).returncode]
    cited = sorted({h for t in texts for h in _HEX.findall(t)} - set(claimed))
    other = [f"{h}: {'a commit' if _git(clone, 'cat-file', '-e', h + '^{commit}').returncode == 0 else 'not found'}"
             for h in cited]
    if not claimed:
        return Finding("Q6", False, "v1.1 and the log claim no commit"), other
    return (Finding("Q6", not missing,
                    "not in the head's history: " + ", ".join(missing) if missing else ""),
            other)


# ----------------------------------------------------------------- Q7
def stubs(v11: str) -> Finding:
    why = list(plan_check.unfilled(v11)) if v11 else ["no v1.1"]
    secs = {t: "\n".join(b).strip() for lvl, t, b in plan_check.sections(v11) if lvl == 2}
    for need in ("Deviations", "Results"):
        body = next((b for t, b in secs.items() if t == need or t.startswith(need + " ")), None)
        if body is None:
            why.append(f"no '## {need}' section")
    if _BOX.search(v11):
        why.append(f"{len(_BOX.findall(v11))} unticked box(es)")
    return Finding("Q7", not why, "; ".join(dict.fromkeys(why))[:400])


# ----------------------------------------------------------------- Q8
_HANDOFF = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2,3}[A-Z]?)_closed\.md$")


def handoff(clone: pathlib.Path, phase: str, sibling: pathlib.Path | None = None) -> Finding:
    road = _text(clone / "docs" / "ROADMAP.md")
    closed = roadmap_check.closes(road, _text(clone / "implementation.md")).get(phase)
    found = sorted(p for p in (clone / "docs" / "handoffs").glob(f"*_{phase}_closed.md")
                   if (m := _HANDOFF.match(p.name)) and m.group(2) == phase)
    why = []
    if not found:
        why.append(f"no docs/handoffs/<date>_{phase}_closed.md")
    else:
        newest = found[-1]
        text = _text(newest)
        why += [f"{newest.name} has no '## {s}'" for s in ("What is open", "What is next")
                if not re.search(rf"^## {s}\b", text, re.M)]
    if closed is None:
        why.append(f"row {phase} is not closed on the branch")
    sib = sibling if sibling is not None and sibling.is_dir() else None
    why += roadmap_check.check_tree(clone, sib)
    return Finding("Q8", not why, "; ".join(why)[:500])


# ----------------------------------------------------------------- Q9
def mergeable(clone: pathlib.Path, base: str = "master") -> Finding:
    dirty = _git(clone, "status", "--porcelain").stdout.strip()
    if dirty:
        return Finding("Q9", False, f"the clone is not clean: {dirty.splitlines()[0]}")
    r = _git(clone, "merge-tree", "--write-tree", "--name-only", base, "HEAD")
    if r.returncode != 0:
        conflicts = [ln for ln in r.stdout.splitlines()[1:] if ln.strip()][:5]
        return Finding("Q9", False, "it does not merge onto master cleanly: "
                                    + (", ".join(conflicts) or r.stderr.strip()[:200]))
    return Finding("Q9", True)


# ------------------------------------------------------ Q10-Q12 (Phase 393)
CODE_SCRIPT = "scripts/code_quality.py"


def code_command(base: str) -> list[str]:
    """The fenced, model-free command for Q10 and Q12 on the head: the base's
    `scripts/code_quality.py` when the base has one, so a pull request does
    not bring its own judge, else the head's."""
    return ["/bin/sh", "-c",
            f"if git cat-file -e {base}:{CODE_SCRIPT} 2>/dev/null; then "
            f"git show {base}:{CODE_SCRIPT} > /fleet/run/code_quality.py; "
            f"else cp {CODE_SCRIPT} /fleet/run/code_quality.py; fi && "
            f".venv/bin/python /fleet/run/code_quality.py pr --base {base} --root ."]


def code_result(out: str) -> dict | None:
    """The `pr` JSON from the fenced run's output: its last line that parses."""
    for line in reversed(out.strip().splitlines()):
        try:
            got = json.loads(line)
        except ValueError:
            continue
        if isinstance(got, dict) and {"Q10", "Q12"} <= set(got):
            return got
    return None


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def code_checks(pr: dict | None, cov: dict, why: str = "") -> list[Finding]:
    """Q10, Q11 and Q12 from the scripts' results. Each failure names the
    file and the number (K54)."""
    if pr is None:
        none = f"the fenced code check gave no result: {why}"[:300]
        q10, q12 = Finding("Q10", False, none), Finding("Q12", False, none)
    else:
        names = {"ruff": "ruff finding", "mypy": "mypy error"}
        q10 = Finding("Q10", not pr["Q10"], "; ".join(
            f"{e['file']}: {_plural(e['head'], names[e['tool']])} on the head, "
            f"{e['base']} on master" for e in pr["Q10"])[:500])
        parts = []
        for e in pr["Q12"]:
            if "function" in e:
                parts.append(f"{e['file']}:{e['line']} `{e['function']}` is McCabe "
                             f"{e['complexity']}, over {e['limit']}, and the pull request "
                             f"changes it")
            else:
                parts.append(f"{e['file']} is {e['bytes']} bytes ({e['base_bytes']} on "
                             f"master), over the limit of {e['limit']}")
        q12 = Finding("Q12", not pr["Q12"], "; ".join(parts)[:500])
    if cov.get("ok"):
        q11 = Finding("Q11", True, "" if cov.get("percent") is None else
                      f"{cov['percent']}% of {cov['measured']} changed lines")
    elif cov.get("why"):
        q11 = Finding("Q11", False, cov["why"])
    else:
        worst = "; ".join(f"{w['file']}: {w['covered']} of {w['measured']}"
                          for w in cov["worst"])
        q11 = Finding("Q11", False, f"{cov['percent']}% of the {cov['measured']} changed lines "
                                    f"in src/ are covered ({cov['covered']}), under "
                                    f"{code_quality.CHANGED_COVERAGE:g}%: {worst}"[:500])
    return [q10, q11, q12]


# ------------------------------------------------------------- together
def scripted(clone: pathlib.Path, phase: str, tip: str, comments: list[dict], *,
             full_ok: bool, full_line: str | None, full_why: str, verify_text: str,
             base: str = "master", sibling: pathlib.Path | None = None
             ) -> tuple[list[Finding], dict[str, object]]:
    """Q2-Q9 (Q1 is the caller's, before any run), and what the model reads."""
    log = _text(doc(clone, phase, "phase_log"))
    v11 = _text(doc(clone, phase, "implementation"))
    on_issue, texts = issue_checks(comments)
    vs = read_verify(verify_text, phase)
    q5 = [v for v in vs if v.ok is False]
    q6, cited = claims(clone, phase, tip)
    found = [*on_issue, full_run(full_ok, full_line, full_why, log),
             Finding("Q5", not q5, "; ".join(f"{v.check} {v.why}" for v in q5)[:500]),
             q6, stubs(v11), handoff(clone, phase, sibling), mergeable(clone, base)]
    return found, {**texts, "verify": vs, "cited": cited}


BRIEF = """\
You are the Quartermaster of the MotoDiag fleet, in shadow: the last check
before phase {N}'s pull request is merged to master. You did not build it,
and you merge nothing: the operator merges by hand and compares your
verdict with theirs. You are read-only: you may Read, Grep and Glob the
repository (the pull request's head) to check what you are told.

Scripts, not you, ran the checks below: the full test run, the whole-tree
run, verify_phase.sh's fourteen, and Q1-Q12. A check marked FAIL already
refuses this merge; you cannot overturn it. Judge only what a script cannot:
1. V4 (stubs): each hit is a stub (unfinished text) or a sentence that only
   uses the word. A stub refuses, under V4.
2. The diff of v1.0 to v1.1: v1.1 must say what was built. A section that
   is a stub, a Results or Deviations section that says nothing measured,
   or a claim in v1.1 the phase log contradicts, refuses, under Q7. A
   section left unchanged is not a stub by itself: some sections stay true.
3. The Captain's and the Red Team's words, as given: a reason they give to
   hold that the checks did not catch refuses, under Q2 or Q3.
4. The plan of record's and docs/decisions.md's words on this phase, at the
   end (Phase 392): a pull request that ships what no entry puts in order,
   or what a K-id reserves for the operator, refuses, under Q1. Cite the
   dated entry or the K-id in "why".

Name each refusal by one of these ids, exactly, and no other:
{IDS}

Return:
- verdict: "refuse" if any check below failed or you found a reason above;
  otherwise "merge".
- failed: one entry per reason, "check" being the id alone (for example
  "V4") and "why" one plain sentence. Empty when the verdict is merge.
- summary: one plain-English sentence for the operator, no internal labels.
"""
SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"enum": [MERGE, REFUSE]},
        "failed": {"type": "array", "items": {
            "type": "object", "properties": {"check": {"type": "string"},
                                             "why": {"type": "string"}},
            "required": ["check", "why"], "additionalProperties": False}},
        "summary": {"type": "string"},
    },
    "required": ["verdict", "failed", "summary"], "additionalProperties": False,
}


def brief(phase: str) -> str:
    return BRIEF.replace("{N}", phase).replace(
        "{IDS}", "\n".join(f"  {k}: {v}" for k, v in CHECKS.items()))


def gather(clone: pathlib.Path, phase: str, found: list[Finding], extra: dict[str, object],
           verify_text: str, pr_body: str) -> str:
    """Everything the model reads, all of it produced by script."""
    pc = red_team.plan_commit(clone, phase)
    plan_diff = (_git(clone, "diff", pc, "HEAD", "-M", "--",
                      f"docs/phases/in_progress/{phase}_implementation.md",
                      f"docs/phases/completed/{phase}_implementation.md").stdout
                 if pc else "(no v1.0 commit found)")
    return ("=== the checks, as the scripts found them ===\n"
            + "\n".join(f.line() for f in [*found, *extra["verify"]])
            + "\n\n=== other commits cited (not claims), and whether each resolves ===\n"
            + ("\n".join(extra["cited"]) or "(none)")
            + f"\n\n=== verify_phase.sh, as it printed ===\n{verify_text.strip()}"
            + f"\n\n=== the Captain's newest recommendation ===\n{extra['captain']}"
            + f"\n\n=== the Red Team's newest verdict ===\n{extra['red_team']}"
            + f"\n\n=== the pull request's body ===\n{pr_body.strip()}"
            + f"\n\n=== the diff of v1.0 ({(pc or 'not found')[:12]}) to v1.1 ===\n{plan_diff}"
            + f"\n\n{plan_order.brief_block(clone, phase)}")


def judge(phase: str, context: str, *, clone: pathlib.Path, run: Runner, model: str = OPUS
          ) -> tuple[dict, rank_call.Call]:
    """One fresh read-only call; its answer checked before it is used."""
    c = rank_call.call("quartermaster", brief(phase) + "\n" + context, model, SCHEMA,
                       cwd=clone, run=run, timeout=3600)
    v = c.structured
    if v.get("verdict") not in (MERGE, REFUSE):
        raise Stop(f"no verdict in {sorted(v)}")
    failed = v.get("failed")
    if not isinstance(failed, list) or not all(isinstance(f, dict) for f in failed):
        raise Stop("the failed checks are not a list")
    unknown = [str(f.get("check")) for f in failed if f.get("check") not in CHECKS]
    if unknown:
        raise Stop(f"the model named checks that do not exist: {', '.join(unknown)[:200]}")
    if v["verdict"] == REFUSE and not failed:
        raise Stop("refuse, naming no check")
    if v["verdict"] == MERGE and failed:
        raise Stop(f"merge, with {len(failed)} failed checks named")
    if not str(v.get("summary", "")).strip():
        raise Stop("no summary")
    return v, c


def compose(found: list[Finding], judged: dict | None) -> tuple[str, list[tuple[str, str]], str]:
    """(verdict, [(check, why)], note): scripted failures first, then the model's."""
    failed = [(f.check, f.why) for f in found if f.ok is False]
    named = {c for c, _ in failed}
    if judged:
        failed += [(f["check"], f["why"]) for f in judged.get("failed", [])
                   if (f["check"], f["why"]) not in failed]
    note = ""
    if judged and judged["verdict"] == MERGE and named:
        note = "The model's own reading was merge; the scripted checks above refuse."
    return (REFUSE if failed else MERGE), failed, note


def verdict_text(phase: str, verdict: str, failed: list[tuple[str, str]], summary: str,
                 note: str = "", call_line: str = "", cite: str = "") -> str:
    lines = [f"**The Quartermaster, phase {phase} (shadow): {verdict}**", "",
             summary.strip() or ("Every check passed." if verdict == MERGE else ""), ""]
    if failed:
        lines += ["Refused on:"] + [f"- {c} ({CHECKS[c]}): {w}" for c, w in failed] + [""]
    if note:
        lines += [note, ""]
    lines.append("In shadow: nothing is merged and no label is moved. The operator merges.")
    if cite:
        lines += ["", cite]
    if call_line:
        lines += ["", call_line]
    return "\n".join(lines)
