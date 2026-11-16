"""The Chief Engineer: one approved plan, built in a fenced clone, to a PR.

Phase 389. Opus, one long `claude -p` session per round in the fence, with
the default tools and `--permission-mode bypassPermissions`: the fence and
the repository's own hooks are the boundary (Step 0, S0-4, measured the
edit guard firing inside the fence in that mode). It pushes nothing and
opens nothing: the dispatcher does, after the checks here.

- `session_argv`: the command; `session_brief`: the brief (the plan, the
  rules, the traps, the stops) and, on a fix round, the Red Team's
  findings, which goes on the session's stdin, never in argv (Phase 394).
- `watch`: run every 30 seconds while the session lives, outside the
  model. A phase log reaching `### Bug fix #3`, or two guard blocks with
  the same guard and reason in the session's transcript, ends the session
  (the fleet proposal: "more than two bugs means a common root cause, not
  a third patch"; the 389 prompt: "when a guard blocks twice for the same
  reason").
- `read_result`: `/fleet/run/engineer.json`, schema-checked: `pr-ready`
  with a summary and the regression line, `deploy` (Phase 395) with those
  and the change to live in a sentence, or `stop` with its kind and a
  question for the operator.
- `verify`: every claim of a `pr-ready` checked against the clone:
  committed and clean, `closeout_check.check` empty (A1–A8), and the
  model-free run's counts equal to the Engineer's line.

**The database step** (Phase 395, K58, F232). A plan with a migration names
it in a section `## The database step`. The Engineer then stops after the
regression of record with the outcome `deploy`, never closing out: the
fence never sees live, so the dry run, the operator's yes, the apply and
the check are the operator's paste block (`deploy/through_fleet.py`).
`verify_deploy` believes a `deploy` only as `verify` believes a `pr-ready`;
after the apply, `CLOSEOUT` is the round's brief and `verify_after_apply`
holds it to documents only.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "closeout"))
import closeout_check  # noqa: E402
import code_after_regression  # noqa: E402
from rank_call import OPUS, Stop  # noqa: E402

SESSION_TIMEOUT_S = 6 * 3600
WATCH_EVERY_S = 30
MAX_BUG_FIXES = 2            # the third stops
RESULT = "engineer.json"     # in the run directory, /fleet/run inside the fence
STOP_KINDS = ("third-bug-fix", "guard-blocked-twice", "fork", "threshold-or-rule",
              "test-cannot-be-green", "login-or-credential", "live-database-change")
#: The result that asks for the phone app's copy (Phase 403, F276).
APP_COPY = "app-copy"
#: The prompt a cut session is resumed with (389 for a usage limit; 390 for a restart too).
CONTINUE = ("You were stopped part-way, by a usage limit or a restart of the machine. Continue "
            "the work from where you were, and finish as the brief says.")
_BUG = re.compile(r"^### Bug fix #(\d+)\b", re.M)
_HOOK = "PreToolUse:Bash hook error:"
_COUNTS = re.compile(r"(\d[\d,]*) passed, (\d[\d,]*) failed, (\d[\d,]*) skipped")
MIGRATIONS = "src/motodiag/core/migrations.py"
#: The plan's section that puts a migration in scope (Phase 395).
DATABASE_STEP = "## The database step"
_ANSWER = re.compile(r"^> (.*)$", re.M)

BRIEF = """\
You are the Chief Engineer of the MotoDiag fleet. You build phase {N} in a
fresh clone of its branch, inside a sandbox: you can write only this clone
and /fleet/run, there is no network but the model's, and you cannot push.
Do not try to push or open a pull request: a script does both after you
finish, once it has checked your work and run the full suite again itself.

The plan is docs/phases/in_progress/{N}_implementation.md, version 1.0,
approved by the Executive Officer on issue #{ISSUE}. CLAUDE.md and the
workspace rules it imports are loaded; follow them. In particular:

1. Build what the plan says, nothing more. Anything you do that it does not
   say goes in v1.1's Deviations, with the reason.
2. Small commits. Before each one, run .claude/skills/closeout/wholetree.sh
   on its own and read its exit code; never through a pipe. Commit
   messages through a quoted heredoc (<<'MSGEOF'), ending with the line
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
3. Change files under src/ and tests/ only with the Edit and Write tools.
   The edit guard refuses sed -i wherever it points: under src/, tests/,
   docs/ or anywhere else. It refuses any shell write (a redirect >, >> or
   >|, tee, cp, mv) whose target is not a literal path it can read: a
   variable, a substitution or a glob is refused wherever it would land.
   Write scratch files to a literal directory, /fleet/run/ (for example
   > /fleet/run/scratch.txt), and edit documents with the Edit tool. The
   same refusal twice ends your session.
4. When you add tests, raise COLLECTED_TEST_FLOOR in
   tests/test_phase255B_collected_test_floor.py by a diff of collected ids,
   with the reason in the comment and the commit message.
5. Each bug fix: a dated entry in the phase log,
   "### Bug fix #N — YYYY-MM-DD — <what was wrong>", with Issue, Root cause,
   Fix, Files, Verified and Commit, and its own commit. Keep the phase log
   (docs/phases/in_progress/{N}_phase_log.md) as dated entries as you go.
6. The regression of record: .claude/skills/closeout/wholetree.sh --full,
   then .claude/skills/closeout/regression.sh, on a clean tree. The phase
   log carries regression.sh's whole record exactly as it printed it: the
   "Regression of record:" line, every "Skipped in the regression of
   record:" line right under it, and the coverage line after them. Before
   you end your turn, read your own log back with
   .venv/bin/python .claude/skills/fleet/engineer.py record {N}
   which prints the record it finds, or why it finds none; fix the log
   until it finds one.
7. Unless the plan has the database step (below), close out before you
   finish, as .claude/skills/closeout/SKILL.md sets
   out: v1.1 (every section updated, Deviations, Results with the
   regression line); the phase log's status Complete; the phase's files
   moved to docs/phases/completed/ with git mv; the ROADMAP row ✅ with
   **CLOSED YYYY-MM-DD.** and the regression line, at most 120 words by
   .claude/skills/closeout/roadmap_words.py; implementation.md's version
   and history row; the root phase_log.md's pointer; the handoff,
   docs/handoffs/YYYY-MM-DD_{N}_closed.md (what shipped, what is open,
   what is next; whoever merges adds the merge's outcome). Then run
   .claude/skills/closeout/closeout_check.py . {N} until it prints nothing.
   This phase goes to the Red Team after your close-out. Write no sentence
   saying a refute pass did or did not run, in v1.1, the phase log or the
   handoff, and leave the word "refute" out of the phase log: the
   dispatcher commits the Red Team's "## Refuter pass" table to the phase
   log, and that table is the record (A8). A line saying no refute pass
   ran is false once the Red Team runs, and closeout_check refuses it.
8. Traps that cost earlier builders full regressions: the venv at .venv is
   read-only and already installs this clone's src (never pip install);
   never pin the schema head as a literal (F124); no test reads the live
   database (244H); an allowlist's size can be pinned in more than one
   test file, so grep before changing one; inserting a migration keeps its
   predecessor's rollback; a test that spawns pytest never adds -n.
9. Never change CLAUDE.md, .claude/settings.json, the closeout guards or
   anything under .claude/skills/fleet/, and never change or remove
   another phase's ROADMAP row: the push is refused if you do. Never write
   a credential anywhere.

**The database step.** When the plan has a section "## The database step",
its migration is in scope: write it in src/motodiag/core/migrations.py,
the deploy skill's scope file
(docs/phases/in_progress/{N}_deploy_scope.json, every table and schema
object it adds, as .claude/skills/deploy/SKILL.md step 1 sets out), and
tests that run it on fresh databases (never live). Run the regression of
record (rule 6), put its whole record in the phase log and read it back as
rule 6 says (the live apply reads it the same way), and commit it.
Then do NOT close out: you cannot reach the
live database, and the operator applies the change between your
regression and your close-out. Leave every phase document in
docs/phases/in_progress/, change nothing under .claude/skills/deploy/ or
.claude/skills/closeout/, and write /fleet/run/engineer.json as
{{"outcome": "deploy", "summary": "<three to six sentences: what the phase
 ships>", "regression_line": "<the Regression of record: line exactly as
 printed>", "live_change": "<one plain sentence for the operator: what the
 change does to the live database>"}}
and end your turn. A migration the plan does not name in that section, or
one that changes or deletes existing live rows, is a stop
(live-database-change), never a deploy.

**The phone app's copy of the API's description.** Gate 11
(tests/test_phase205_gate11.py) compares the server's description with
../moto-diag-mobile/api-schema/openapi.json, which you can read and cannot
write. When this phase changes the description, Gate 11 goes red. If
Gate 11 is the only thing red (.claude/skills/closeout/wholetree.sh
passes), commit everything, write /fleet/run/engineer.json as
{{"outcome": "app-copy", "summary": "<one plain sentence: what this phase
 changed in the API's description>"}}
and end your turn. A script with no model then regenerates the app's copy
from your last commit, on the app's branch named as this phase's branch
(never main), checks Gate 11 against it, and starts you again in this
same clone. Never ask the operator, in a stop, a log or a handoff, to
refresh the app's copy or to move the desktop's copy of the app: the
fleet does both.

**Stop instead of finishing** when any of these happens: a third bug fix;
a CLAUDE.md rule-1 condition (a real fork, a threshold or a rule's
definition, a test you cannot make green, a login or credential, a
live-database change that alters or deletes rows); a guard blocking the
same thing twice for the same reason. To stop: commit what is safe, then
write /fleet/run/engineer.json as
{{"outcome": "stop", "kind": "<one of: {KINDS}>",
 "question": "<plain English for the operator: what happened, and the
 decision you need, with no internal labels>"}}
and end your turn.

**When the work is done and closeout_check prints nothing**, write
/fleet/run/engineer.json as
{{"outcome": "pr-ready", "summary": "<three to six sentences: what the phase
 ships>", "regression_line": "<the Regression of record: line exactly as
 printed>"}}
and end your turn.
"""

FIX_ROUND = """
=== This is fix round {ROUND}. The Red Team, a fresh reviewer, sent the
pull request back with these findings. Address each one. Where a fix can
delete a sentence rather than rewrite it, delete it (K9). A finding that
changes code is a bug fix (rule 5 above); a wording or factual fix to a
document is a dated phase-log entry. If code changed, run the regression
of record again and update the close-out documents with the new line.
The database step is done if docs/phases/completed/{N}_live_diff.md
exists: the migration is then on the live database, and a finding that
would change src/motodiag/core/migrations.py is a stop (live-database-change),
never a fix. Then write /fleet/run/engineer.json as above. ===
{FINDINGS}
"""


#: The round after the operator applied the change (Phase 395).
CLOSEOUT = """
=== The database step is done. The operator ran the dry run on a copy,
typed their answer, applied the change to the live database and checked
it; the dispatcher checked it again with verify-live. Three files are now
committed in docs/phases/in_progress/: {N}_dryrun_diff.md (the approved
change), {N}_deploy_answer.md (the operator's words) and {N}_live_diff.md
(live after the apply). This round is the close-out only: change no code,
and nothing under src/, tests/, scripts/ or .claude/.
1. Quote the operator's answer in the phase log, in a dated entry, as the
   line that starts "> " in {N}_deploy_answer.md, character for character,
   with the dry-run diff's sha256 it names.
2. The live outcome in v1.1's Results and in the handoff: what the live
   diff says (its scope problems and whether it equals the approved diff).
3. Close out as rule 7 sets out; git mv the three files and the scope file
   to docs/phases/completed/ with the phase documents. Run
   .claude/skills/closeout/closeout_check.py . {N} until it prints nothing.
Then write /fleet/run/engineer.json with the outcome pr-ready, as above,
and the regression line already in the phase log. ===
"""


#: Said when the record answered the Engineer's stop (Phase 392, K50): the
#: K-id's words verbatim, as the dispatcher's comment carries them.
ANSWERED = """
=== Your last session stopped. The operator's record answers that stop, so
it did not go to the operator; the dispatcher's comment, with the K-id's
words verbatim, is below. Apply those words literally and to nothing
beyond them (CLAUDE.md rule 1: a pre-approval is the operator's scoped
wording, applied literally). Carry on from where the clone is. If the same
thing stops you again, stop again: that time it goes to the operator. ===
{ANSWER}
"""


#: Said when the operator answered the Engineer's stop on the issue (Phase
#: 403, F231): the dispatcher quoted the answer into the phase log.
CARRIED = """
=== Your last session on this phase stopped, and the operator has answered.
The answer is in the phase log, {LOG}, in the entry headed
"{HEADING}": the operator's own comments on issue #{ISSUE}, quoted
verbatim by the dispatcher and committed in this clone. Read it first and
apply it literally, to nothing beyond it (CLAUDE.md rule 1). {FROM} ===
"""

#: Said when the dispatcher refreshed the app's copy (Phase 403, F276).
APP_COPIED = """
=== The phone app's copy of the API's description is refreshed: the
dispatcher regenerated api-schema/openapi.json from {COMMIT} on
moto-diag-mobile's branch {BRANCH} ({APP}), and Gate 11 passes against it.
This is the clone you ended in, with your commits. Carry on from where you
were and finish as the brief says. ===
"""


def session_brief(phase: str, issue: int, *, findings: str | None = None, rnd: int = 0,
                  answer: str | None = None, closeout: bool = False,
                  carried: dict | None = None, app: dict | None = None) -> str:
    prompt = BRIEF.format(N=phase, ISSUE=issue, KINDS=", ".join(STOP_KINDS))
    if findings:
        prompt += FIX_ROUND.format(ROUND=rnd, FINDINGS=findings, N=phase)
    if answer:
        prompt += ANSWERED.format(ANSWER=answer)
    if carried:
        prompt += CARRIED.format(ISSUE=issue, **carried)
    if app:
        prompt += APP_COPIED.format(**app)
    if closeout:
        prompt += CLOSEOUT.format(N=phase)
    return prompt


def session_argv(model: str = OPUS) -> list[str]:
    return ["claude", "-p", "--model", model, "--permission-mode", "bypassPermissions",
            "--disallowedTools", "WebFetch,WebSearch", "--strict-mcp-config",
            "--output-format", "json"]


# --------------------------------------------------------------- watchers
def bug_fixes(clone: pathlib.Path, phase: str) -> int:
    n = 0
    for folder in ("in_progress", "completed"):
        log = clone / "docs" / "phases" / folder / f"{phase}_phase_log.md"
        if log.is_file():
            n = max([n, *(int(m) for m in _BUG.findall(log.read_text(encoding="utf-8")))])
    return n


def guard_blocks(run_dir: pathlib.Path) -> collections.Counter:
    """Each guard block in the session's transcripts, keyed by the guard and
    the first sentence of its reason."""
    seen: collections.Counter = collections.Counter()
    for f in sorted((run_dir / "claude" / "projects").glob("*/*.jsonl")):
        for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                content = (json.loads(ln).get("message") or {}).get("content")
            except ValueError:
                continue
            for part in content if isinstance(content, list) else []:
                if not (isinstance(part, dict) and part.get("type") == "tool_result"
                        and part.get("is_error")):
                    continue
                text = part.get("content")
                text = text if isinstance(text, str) else json.dumps(text)
                if text.startswith(_HOOK):
                    seen[re.split(r"(?<=[.!?])\s", text[len(_HOOK):].strip(), maxsplit=1)[0]] += 1
    return seen


def watch(clone: pathlib.Path, run_dir: pathlib.Path, phase: str) -> str | None:
    """Why the session must end now, or None."""
    n = bug_fixes(clone, phase)
    if n > MAX_BUG_FIXES:
        return (f"third-bug-fix: the phase log reached Bug fix #{n}. More than two bug fixes "
                "in one build means a shared root cause to find, not another patch.")
    twice = [k for k, c in guard_blocks(run_dir).items() if c >= 2]
    if twice:
        return f"guard-blocked-twice: a guard blocked the same thing twice: {twice[0][:200]}"
    return None


# ----------------------------------------------------------------- result
def read_result(run_dir: pathlib.Path) -> dict:
    p = run_dir / RESULT
    if not p.is_file():
        raise Stop(f"the session ended without writing {RESULT}")
    try:
        r = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        raise Stop(f"{RESULT} is not JSON") from None
    if r.get("outcome") == "stop":
        if r.get("kind") not in STOP_KINDS or not str(r.get("question", "")).strip():
            raise Stop(f"{RESULT} says stop with no known kind or no question")
        return r
    outcome = r.get("outcome")
    if outcome == APP_COPY:
        if not str(r.get("summary", "")).strip():
            raise Stop(f"{RESULT} says {APP_COPY} and does not say what changed in the "
                       "API's description")
        return r
    if outcome not in ("pr-ready", "deploy"):
        raise Stop(f"{RESULT} has no outcome of pr-ready, deploy, {APP_COPY} or stop")
    if not str(r.get("summary", "")).strip():
        raise Stop(f"{RESULT} says {outcome} with no summary")
    if not str(r.get("regression_line", "")).startswith(closeout_check.PREFIX):
        raise Stop(f"{RESULT} says {outcome} and gives no regression of record")
    if outcome == "deploy" and not str(r.get("live_change", "")).strip():
        raise Stop(f"{RESULT} says deploy and does not say what the change does to live")
    return r


def counts(line: str) -> tuple[int, int, int] | None:
    m = _COUNTS.search(line or "")
    return tuple(int(x.replace(",", "")) for x in m.groups()) if m else None


def _git(clone: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True,
                          text=True).stdout.strip()


def _same_run(result: dict, model_free_line: str | None) -> list[str]:
    mine, theirs = counts(result.get("regression_line", "")), counts(model_free_line or "")
    if model_free_line is None:
        return ["the model-free run produced no regression of record"]
    if mine != theirs:
        return [f"the Engineer's regression line counts {mine} (passed, failed, skipped); "
                f"the model-free run counts {theirs}"]
    return []


def _dirty(clone: pathlib.Path) -> list[str]:
    dirty = _git(clone, "status", "--porcelain")
    return [f"uncommitted changes in the clone: {dirty.splitlines()[0]}"] if dirty else []


def _doc(clone: pathlib.Path, phase: str, kind: str) -> pathlib.Path | None:
    for folder in ("completed", "in_progress"):
        p = clone / "docs" / "phases" / folder / f"{phase}_{kind}.md"
        if p.is_file():
            return p
    return None


def applied_at(clone: pathlib.Path, phase: str) -> str | None:
    """The commit that added the phase's live diff: the change is on live
    from there on. None before the database step."""
    for folder in ("in_progress", "completed"):
        c = _git(clone, "log", "-1", "--format=%H", "--diff-filter=A", "--",
                 f"docs/phases/{folder}/{phase}_live_diff.md")
        if c:
            return c
    return None


def migration_changes(clone: pathlib.Path, phase: str, base: str = "master") -> list[str]:
    """Why a pull request's migration may not open (Phase 395): a migration
    that skipped the database step, or one changed after it was applied."""
    if MIGRATIONS not in _git(clone, "diff", "--name-only", f"{base}...HEAD").split():
        return []
    at = applied_at(clone, phase)
    if at is None:
        return [f"it changes {MIGRATIONS} and the database step has not run: a migration "
                "ends with the outcome deploy, before the close-out"]
    if MIGRATIONS in _git(clone, "diff", "--name-only", f"{at}..HEAD").split():
        return [f"{MIGRATIONS} changed after it was applied to the live database "
                f"({at[:12]}): that is the operator's decision, not a fix"]
    return []


def verify(clone: pathlib.Path, phase: str, result: dict, model_free_line: str | None
           ) -> list[str]:
    """Every claim of a pr-ready, checked; [] when the PR may open."""
    fails = _dirty(clone)
    fails += [f"close-out: {f}" for f in closeout_check.check(clone, phase)]
    fails += migration_changes(clone, phase)
    return fails + _same_run(result, model_free_line)


def verify_deploy(clone: pathlib.Path, phase: str, result: dict, model_free_line: str | None,
                  base: str = "master") -> list[str]:
    """Every claim of a `deploy`, checked; [] when the operator may be asked
    (Phase 395): the clone clean, the plan naming the database step, a
    migration and its scope file committed, the regression of record in
    the phase log, master's deploy and close-out tools, nothing of the
    database step or the close-out done yet, and the model-free run
    counting what the Engineer's line counts."""
    fails = _dirty(clone)
    inp = clone / "docs" / "phases" / "in_progress"
    plan, log = inp / f"{phase}_implementation.md", inp / f"{phase}_phase_log.md"
    if not plan.is_file() or not log.is_file():
        fails.append("the phase documents are not in docs/phases/in_progress/: the database "
                     "step comes before the close-out")
    elif DATABASE_STEP not in plan.read_text(encoding="utf-8"):
        fails.append(f"the plan has no section '{DATABASE_STEP}': its migration is not in scope")
    scope = f"docs/phases/in_progress/{phase}_deploy_scope.json"
    if not (clone / scope).is_file() or not _git(clone, "ls-files", scope):
        fails.append(f"no committed scope file {scope}: nothing says what the change may touch")
    paths = _git(clone, "diff", "--name-only", f"{base}...HEAD").split()
    if MIGRATIONS not in paths:
        fails.append(f"the branch does not change {MIGRATIONS}: there is no migration to apply")
    tools = [p for p in paths
             if p.startswith((".claude/skills/deploy/", ".claude/skills/closeout/"))]
    if tools:
        fails.append(f"it changes {tools[0]}: the database step runs only master's tools")
    done = [k for k in ("dryrun_diff", "deploy_answer", "live_diff") if _doc(clone, phase, k)]
    if done:
        fails.append(f"the branch already carries {phase}_{done[0]}.md: only the operator's "
                     "block writes the database step's files")
    if log.is_file() and closeout_check.regression_record(log.read_text(encoding="utf-8"),
                                                          phase)[0] is None:
        fails.append("the phase log carries no regression of record the live apply can read")
    return fails + _same_run(result, model_free_line)


def verify_after_apply(clone: pathlib.Path, phase: str, applied: str) -> list[str]:
    """The close-out round after the apply changed documents only, and
    quoted the operator's answer in the phase log (Phase 395)."""
    fails = []
    code = code_after_regression.code_paths(_git(clone, "diff", "--name-only",
                                                 f"{applied}..HEAD").split())
    if code:
        fails.append(f"code changed after the live apply at {applied[:12]}: {code[:5]}")
    answer, log = _doc(clone, phase, "deploy_answer"), _doc(clone, phase, "phase_log")
    said = _ANSWER.findall(answer.read_text(encoding="utf-8")) if answer else []
    if not said:
        fails.append(f"no {phase}_deploy_answer.md with the operator's words")
    elif log is None or f"> {said[-1]}" not in log.read_text(encoding="utf-8"):
        fails.append("the phase log does not quote the operator's answer as it was typed")
    return fails


def record_said(root: pathlib.Path, phase: str) -> tuple[int, str]:
    """What rule 6's read-back prints (Phase 403, F264): the record
    `regression_record` finds in the phase's log, or why it finds none."""
    log = _doc(root, phase, "phase_log")
    if log is None:
        return 1, f"no {phase}_phase_log.md under docs/phases/"
    rec, why = closeout_check.regression_record(log.read_text(encoding="utf-8"), phase)
    if rec is None:
        return 1, f"no regression of record in {log.relative_to(root)}: {why}"
    return 0, (f"the regression of record in {log.relative_to(root)}: {rec[0]} passed at "
               f"`{rec[1]}`, by `{rec[2]}`")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "record":
        print("usage: engineer.py record <phase>", file=sys.stderr)
        return 2
    rc, said = record_said(pathlib.Path.cwd(), argv[1])
    print(said)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
