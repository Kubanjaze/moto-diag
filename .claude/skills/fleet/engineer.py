"""The Chief Engineer: one approved plan, built in a fenced clone, to a PR.

Phase 389. Opus, one long `claude -p` session per round in the fence, with
the default tools and `--permission-mode bypassPermissions`: the fence and
the repository's own hooks are the boundary (Step 0, S0-4, measured the
edit guard firing inside the fence in that mode). It pushes nothing and
opens nothing: the dispatcher does, after the checks here.

- `session_argv`: the command, with the brief (the plan, the rules, the
  traps, the stops) and, on a fix round, the Red Team's findings.
- `watch`: run every 30 seconds while the session lives, outside the
  model. A phase log reaching `### Bug fix #3`, or two guard blocks with
  the same guard and reason in the session's transcript, ends the session
  (the fleet proposal: "more than two bugs means a common root cause, not
  a third patch"; the 389 prompt: "when a guard blocks twice for the same
  reason").
- `read_result`: `/fleet/run/engineer.json`, schema-checked: `pr-ready`
  with a summary and the regression line, or `stop` with its kind and a
  question for the operator.
- `verify`: every claim of a `pr-ready` checked against the clone:
  committed and clean, `closeout_check.check` empty (A1–A8), and the
  model-free run's counts equal to the Engineer's line.
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
from rank_call import OPUS, Stop  # noqa: E402

SESSION_TIMEOUT_S = 6 * 3600
WATCH_EVERY_S = 30
MAX_BUG_FIXES = 2            # the third stops
RESULT = "engineer.json"     # in the run directory, /fleet/run inside the fence
STOP_KINDS = ("third-bug-fix", "guard-blocked-twice", "fork", "threshold-or-rule",
              "test-cannot-be-green", "login-or-credential", "live-database-change")
#: The prompt a cut session is resumed with (389 for a usage limit; 390 for a restart too).
CONTINUE = ("You were stopped part-way, by a usage limit or a restart of the machine. Continue "
            "the work from where you were, and finish as the brief says.")
_BUG = re.compile(r"^### Bug fix #(\d+)\b", re.M)
_HOOK = "PreToolUse:Bash hook error:"
_COUNTS = re.compile(r"(\d[\d,]*) passed, (\d[\d,]*) failed, (\d[\d,]*) skipped")

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
3. Change files under src/ and tests/ only with the Edit and Write tools:
   the edit guard blocks sed -i and shell redirects there.
4. When you add tests, raise COLLECTED_TEST_FLOOR in
   tests/test_phase255B_collected_test_floor.py by a diff of collected ids,
   with the reason in the comment and the commit message.
5. Each bug fix: a dated entry in the phase log,
   "### Bug fix #N — YYYY-MM-DD — <what was wrong>", with Issue, Root cause,
   Fix, Files, Verified and Commit, and its own commit. Keep the phase log
   (docs/phases/in_progress/{N}_phase_log.md) as dated entries as you go.
6. The regression of record: .claude/skills/closeout/wholetree.sh --full,
   then .claude/skills/closeout/regression.sh, on a clean tree. Copy the
   lines it prints into the phase log exactly as printed.
7. Close out before you finish, as .claude/skills/closeout/SKILL.md sets
   out: v1.1 (every section updated, Deviations, Results with the
   regression line); the phase log's status Complete; the phase's files
   moved to docs/phases/completed/ with git mv; the ROADMAP row ✅ with
   **CLOSED YYYY-MM-DD.** and the regression line, at most 120 words by
   .claude/skills/closeout/roadmap_words.py; implementation.md's version
   and history row; the root phase_log.md's pointer; the handoff,
   docs/handoffs/YYYY-MM-DD_{N}_closed.md (what shipped, what is open,
   what is next; whoever merges adds the merge's outcome). Then run
   .claude/skills/closeout/closeout_check.py . {N} until it prints nothing.
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
Then write /fleet/run/engineer.json as above. ===
{FINDINGS}
"""


def session_argv(phase: str, issue: int, *, findings: str | None = None, rnd: int = 0,
                 model: str = OPUS) -> list[str]:
    prompt = BRIEF.format(N=phase, ISSUE=issue, KINDS=", ".join(STOP_KINDS))
    if findings:
        prompt += FIX_ROUND.format(ROUND=rnd, FINDINGS=findings)
    return ["claude", "-p", prompt, "--model", model, "--permission-mode", "bypassPermissions",
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
    if r.get("outcome") != "pr-ready":
        raise Stop(f"{RESULT} has no outcome of pr-ready or stop")
    if not str(r.get("summary", "")).strip():
        raise Stop(f"{RESULT} says pr-ready with no summary")
    if not str(r.get("regression_line", "")).startswith(closeout_check.PREFIX):
        raise Stop(f"{RESULT} says pr-ready and gives no regression of record")
    return r


def counts(line: str) -> tuple[int, int, int] | None:
    m = _COUNTS.search(line or "")
    return tuple(int(x.replace(",", "")) for x in m.groups()) if m else None


def verify(clone: pathlib.Path, phase: str, result: dict, model_free_line: str | None
           ) -> list[str]:
    """Every claim of a pr-ready, checked; [] when the PR may open."""
    fails = []
    dirty = subprocess.run(["git", "-C", str(clone), "status", "--porcelain"], capture_output=True,
                           text=True).stdout.strip()
    if dirty:
        fails.append(f"uncommitted changes in the clone: {dirty.splitlines()[0]}")
    fails += [f"close-out: {f}" for f in closeout_check.check(clone, phase)]
    mine, theirs = counts(result.get("regression_line", "")), counts(model_free_line or "")
    if model_free_line is None:
        fails.append("the model-free run produced no regression of record")
    elif mine != theirs:
        fails.append(f"the Engineer's regression line counts {mine} (passed, failed, skipped); "
                     f"the model-free run counts {theirs}")
    return fails
