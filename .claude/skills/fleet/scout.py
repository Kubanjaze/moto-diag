"""The Science Officer: a phase's Step 0 report, from its mission issue.

Phase 389. Haiku (K42: "The Science Officer runs on Haiku through
--source-route anthropic until the 600-machine sourcing backlog is
scheduled"), two calls with no tools, and everything countable done by
script, in 257's census/candidates shape
(`.claude/skills/source-transmission/census.py`, `candidates.py`):

1. `terms`: one call reads the mission and its ROADMAP row and returns the
   nouns and verbs to search for (at most `MAX_TERMS`).
2. `census`: no model. For each term, `git grep -c -i -F` over each area
   of the clone and the mobile repository's `src/`, every count written
   beside the exact command that made it, so P3 holds by construction.
3. `candidates`: no model. At most `PER_TERM` hits per term, `CONTEXT`
   lines either side, at most `MAX_CHARS` in all: what the model may read.
4. `assess`: one call with the mission, the census, the candidates, the
   ROADMAP rows around the phase and the newest handoff, returning the
   classification and three prose sections. The prose may carry no count
   (`plan_check.unshown_counts`); one corrective call, then a stop.
5. `write`: the report, `docs/phases/in_progress/<N>_step0.md`, and the
   issue's body saved as the phase's prompt when it has none yet.

The dispatcher commits, tests, gates and pushes; this module never does.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_check  # noqa: E402
import rank_call  # noqa: E402
from rank_call import HAIKU, NO_TOOLS, Runner, Stop  # noqa: E402

AREAS = ("src", "tests", ".claude", "docs")
MAX_TERMS, PER_TERM, CONTEXT, MAX_CHARS = 12, 5, 3, 30_000
CLASSES = ("greenfield", "extension", "reshape")

TERMS_SCHEMA = {
    "type": "object",
    "properties": {"terms": {"type": "array", "items": {"type": "string"},
                             "minItems": 1, "maxItems": MAX_TERMS}},
    "required": ["terms"], "additionalProperties": False,
}
ASSESS_SCHEMA = {
    "type": "object",
    "properties": {
        "classification": {"enum": list(CLASSES)},
        "reason": {"type": "string"},
        "what_exists": {"type": "string"},
        "what_the_row_promises": {"type": "string"},
        "risks_and_stops": {"type": "string"},
    },
    "required": ["classification", "reason", "what_exists", "what_the_row_promises",
                 "risks_and_stops"],
    "additionalProperties": False,
}

TERMS_BRIEF = """\
You are the Science Officer of the MotoDiag fleet. Below is a mission (a
GitHub issue) and its ROADMAP row. Return the search terms a Step 0 needs:
the nouns the work names (files, functions, tables, columns, commands,
features) and its verbs (what a user must be able to do), each as the exact
text a grep would find in code or documents. At most twelve, no duplicates,
no generic words ("the", "phase", "test").
"""

ASSESS_BRIEF = """\
You are the Science Officer of the MotoDiag fleet, writing the judgement
half of a phase's Step 0 report. The counts are already in a table the
script wrote, each beside its command; you have them below, with excerpts
around the hits. You have no tools: work only from what is below.

Return:
- classification: "greenfield" (nothing of this exists), "extension" (it
  adds to what exists without changing what it does), or "reshape" (it
  changes what existing code does). Reshape goes to the operator.
- reason: two or three sentences, from the census and the excerpts.
- what_exists: what the excerpts show already exists, by file.
- what_the_row_promises: each verb the row or mission promises, and how a
  user reaches it, or that nothing yet reaches it.
- risks_and_stops: anything CLAUDE.md rule 1 reserves for the operator (a
  real fork, a threshold or rule's definition, a test that cannot be made
  green, a login or credential, a live-database change), or "None found."

**Write no numbers that count things** (no "3 files", "12 hits"): the
table holds the counts and their commands. Name files and functions
instead. Plain sentences.
"""


# ------------------------------------------------------------------ calls
def terms(mission: str, row: str, *, cwd: pathlib.Path, run: Runner, model: str = HAIKU
          ) -> tuple[list[str], rank_call.Call]:
    c = rank_call.call("scout", f"{TERMS_BRIEF}\n=== the ROADMAP row ===\n{row}\n\n"
                       f"=== the mission ===\n{mission}", model, TERMS_SCHEMA, cwd=cwd, run=run,
                       tools=NO_TOOLS)
    found = c.structured.get("terms")
    if not isinstance(found, list) or not all(isinstance(t, str) for t in found):
        raise Stop("the terms are not a list of strings")
    clean = list(dict.fromkeys(t.strip() for t in found if t.strip() and "\n" not in t))
    if not clean:
        raise Stop("no search terms came back")
    return clean[:MAX_TERMS], c


# ----------------------------------------------------------------- census
def _count(repo: pathlib.Path, term: str, area: str) -> int:
    r = subprocess.run(["git", "-C", str(repo), "grep", "-c", "-i", "-F", "-e", term, "--", area],
                       capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise Stop(f"git grep failed for {term!r} in {area}: {r.stderr.strip()[:200]}")
    return sum(int(ln.rsplit(":", 1)[1]) for ln in r.stdout.splitlines() if ":" in ln)


def census(clone: pathlib.Path, found: list[str], mobile: pathlib.Path | None
           ) -> list[dict]:
    """One row per term: its count in each area, and the commands."""
    rows = []
    for t in found:
        row = {"term": t, "counts": {a: _count(clone, t, a) for a in AREAS}}
        if mobile is not None and (mobile / "src").is_dir():
            row["counts"]["mobile src"] = _count(mobile, t, "src")
        rows.append(row)
    return rows


def candidates(clone: pathlib.Path, found: list[str]) -> list[dict]:
    """At most PER_TERM excerpts per term, CONTEXT lines around each hit."""
    out, used = [], 0
    for t in found:
        r = subprocess.run(["git", "-C", str(clone), "grep", "-n", "-i", "-F", "-e", t, "--",
                            *AREAS], capture_output=True, text=True)
        for hit in r.stdout.splitlines()[:PER_TERM]:
            path, line, _ = hit.split(":", 2)
            lines = (clone / path).read_text(encoding="utf-8", errors="replace").splitlines()
            n = int(line)
            text = "\n".join(lines[max(0, n - 1 - CONTEXT):n + CONTEXT])
            if used + len(text) > MAX_CHARS:
                return out
            used += len(text)
            out.append({"term": t, "where": f"{path}:{n}", "text": text})
    return out


# ----------------------------------------------------------------- assess
def assess(mission: str, row: str, table: str, excerpts: list[dict], context: str, *,
           cwd: pathlib.Path, run: Runner, model: str = HAIKU) -> tuple[dict, list[rank_call.Call]]:
    shown = "\n\n".join(f"--- {e['where']} ({e['term']})\n{e['text']}" for e in excerpts)
    prompt = (f"{ASSESS_BRIEF}\n=== the ROADMAP row ===\n{row}\n\n=== the mission ===\n{mission}\n\n"
              f"=== the census ===\n{table}\n\n=== excerpts ===\n{shown or '(no hits)'}\n\n"
              f"=== context: the ROADMAP rows around it, the newest handoff ===\n{context}")
    calls = []
    for attempt in range(2):
        c = rank_call.call("scout", prompt, model, ASSESS_SCHEMA, cwd=cwd, run=run, tools=NO_TOOLS)
        calls.append(c)
        v = c.structured
        if v.get("classification") not in CLASSES:
            raise Stop(f"no classification in {sorted(v)}")
        prose = "\n\n".join(str(v.get(k, "")) for k in ASSESS_SCHEMA["required"][1:])
        counts = plan_check.unshown_counts(prose)
        if not counts:
            return v, calls
        prompt += ("\n\n=== your last answer counted things with no command shown; write it again "
                   "with no counts ===\n" + "\n".join(counts))
    raise Stop(f"the report still counts things with no query: {counts[0]}")


# ------------------------------------------------------------------ write
def census_table(rows: list[dict]) -> str:
    areas = list(rows[0]["counts"]) if rows else list(AREAS)
    lead = ("The census, no model: each count is `git grep -c -i -F -e <term> -- <area>` "
            "summed over files, run on this branch's clone (the mobile repository's from "
            "`git -C ../moto-diag-mobile grep … -- src`).")
    head = "| term | " + " | ".join(areas) + " |\n|---|" + "---|" * len(areas)
    body = "\n".join(f"| `{r['term']}` | " + " | ".join(str(r["counts"][a]) for a in areas)
                     + " |" for r in rows)
    return f"{lead}\n\n{head}\n{body}"


def slug(title: str) -> str:
    """Words of the title after its `Phase <N>:`, as a file or branch name."""
    title = re.sub(r"^\s*Phase \w+\s*:\s*", "", title)
    s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return "_".join(s.split("_")[:6]) or "mission"


def render(phase: str, title: str, issue: int, base: str, v: dict, table: str,
           excerpts: list[dict], calls: list[rank_call.Call], today: dt.date) -> str:
    where = ", ".join(f"`{w}`" for w in sorted({e["where"] for e in excerpts})) or "none"
    return f"""# Phase {phase} — Step 0: {title}

**Written {today.isoformat()}** by the Science Officer (`scout.py`, Haiku), from
mission issue #{issue}, on this branch from `master` at `{base[:7]}`. The
counts are the script's; the judgement below them is the model's.

Classification: **{v['classification']}.** {v['reason'].strip()}

## The overlap census

{table}

The excerpts the judgement was given (`scout.candidates`): {where}.

## What exists

{v['what_exists'].strip()}

## What the row promises

{v['what_the_row_promises'].strip()}

## Risks and stops

{v['risks_and_stops'].strip()}

## The calls

""" + "\n".join(f"- {c.line()} (`claude -p … --output-format json`)" for c in calls) + "\n"


def run_scout(phase: str, title: str, issue: int, mission: str, row: str, *,
              clone: pathlib.Path, run: Runner, mobile: pathlib.Path | None,
              context: str = "", today: dt.date | None = None, model: str = HAIKU
              ) -> list[str]:
    """Write the report (and the prompt, if new) into the clone; return the
    paths written, relative to it."""
    found, c1 = terms(mission, row, cwd=clone, run=run, model=model)
    rows = census(clone, found, mobile)
    table = census_table(rows)
    excerpts = candidates(clone, found)
    v, calls = assess(mission, row, table, excerpts, context, cwd=clone, run=run, model=model)
    base = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    text = render(phase, title, issue, base, v, table, excerpts, [c1, *calls],
                  today or dt.date.today())
    left = plan_check.unshown_counts(text)
    if left:
        raise Stop(f"the report counts something with no query shown: {left[0]}")
    step0 = f"docs/phases/in_progress/{phase}_step0.md"
    (clone / step0).parent.mkdir(parents=True, exist_ok=True)
    (clone / step0).write_text(text, encoding="utf-8")
    written = [step0]
    if not list((clone / "docs" / "prompts").glob(f"{phase}_*.txt")):
        prompt = f"docs/prompts/{phase}_{slug(title)}.txt"
        (clone / prompt).parent.mkdir(parents=True, exist_ok=True)
        (clone / prompt).write_text(mission.rstrip("\n") + "\n", encoding="utf-8")
        written.append(prompt)
    return written
