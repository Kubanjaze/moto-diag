#!/usr/bin/env python3
"""The Yeoman: the decisions file and the daily digest.

    yeoman.py decide --words "…" --check "…" [--date YYYY-MM-DD] [--kid K40]
    yeoman.py digest [--date YYYY-MM-DD]

**decide** appends one row to `docs/decisions.md`: the next K-id, the date,
the operator's words verbatim, and the check they became. It refuses a
`--kid` that is not the next one, any K-id cited in the words or the check
that does not resolve, and a backticked path in the check that does not
exist. No model: the words are the operator's, and a model in that path
could only change them.

A K-id resolves when it is defined in one of three places (Phase 387 Step 0,
S0-8): a `### K<n>.` heading or `- **K<n>` bullet in the two process-kinks
triage reports (K1-K31), or a `| K<n> |` row of `docs/decisions.md` (K32 on).
Never a repo-wide grep: K75 and K100 are BMW motorcycles.

**digest** writes `docs/fleet/digests/<date>.md` for one local day, by time
window, from four inputs and nothing else: the ROADMAP rows that changed and
the rows in progress; the newest handoff's open and next sections; the open
findings, and those filed or closed that day; the open GitHub issues
labelled needs-admiral or needs-hands. The facts are the script's. One
Haiku call, read-only, writes a plain-English summary from them, under its
own heading; a call with no usage, or the wrong model, is a stop and no file
is written. Mobile's FOLLOWUPS.md is not read in v1: its headings do not
mark closure (S0-7). The Mac's activity log is a later phase's input.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "closeout"))
import rank_call  # noqa: E402
from plan_check import sections  # noqa: E402
from rank_call import HAIKU, Runner, Stop, gh  # noqa: E402
from roadmap_check import ACTIVE, ROW_REST  # noqa: E402

ROOT = HERE.parents[2]
DECISIONS = "docs/decisions.md"
TRIAGE_REPORTS = ("docs/reports/2026-09-27_process_kinks_triage.md",
                  "docs/reports/2026-10-07_process_kinks_triage.md")
DIGESTS = "docs/fleet/digests"
ESCALATIONS = ("needs-admiral", "needs-hands")

_KID_DEF = re.compile(r"^(?:#{2,4} K(\d+)\b|- \*\*K(\d+)\b)", re.M)
_KID_ROW = re.compile(r"^\| K(\d+) \|", re.M)
_KID_CITED = re.compile(r"\bK(\d{1,3})\b")


# ------------------------------------------------------------------- decide
def defined_kids(root: pathlib.Path = ROOT) -> set[int]:
    found: set[int] = set()
    for rel in TRIAGE_REPORTS:
        p = root / rel
        if p.is_file():
            found |= {int(a or b) for a, b in _KID_DEF.findall(p.read_text(encoding="utf-8"))}
    p = root / DECISIONS
    if p.is_file():
        found |= {int(n) for n in _KID_ROW.findall(p.read_text(encoding="utf-8"))}
    return found


def decide(words: str, check: str, *, root: pathlib.Path = ROOT, date: str | None = None,
           kid: str | None = None, out=print) -> int:
    path = root / DECISIONS
    if not path.is_file():
        out(f"REFUSED: {DECISIONS} does not exist")
        return 1
    known = defined_kids(root)
    nxt = max(known, default=0) + 1
    why = []
    if kid is not None and kid != f"K{nxt}":
        why.append(f"{kid} is not the next K-id; the next is K{nxt}")
    if "\n" in words or "\n" in check:
        why.append("a decision is one line: the words or the check hold a newline")
    if not words.strip() or not check.strip():
        why.append("both the words and the check they became are needed")
    unresolved = sorted({int(n) for n in _KID_CITED.findall(words + " " + check)} - known)
    if unresolved:
        why.append("cited K-ids that do not resolve: " + ", ".join(f"K{n}" for n in unresolved))
    missing = [p for p in re.findall(r"`([^`\s]+)`", check)
               if ("/" in p or re.search(r"\.\w{1,4}$", p)) and not (root / p.split("::")[0]).exists()]
    if missing:
        why.append("the check names paths that do not exist: " + ", ".join(missing))
    day = date or dt.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        why.append(f"the date {day!r} is not YYYY-MM-DD")
    if why:
        for w in why:
            out(f"REFUSED: {w}")
        return 1
    cell = lambda s: s.replace("|", "\\|")  # noqa: E731
    row = f'| K{nxt} | {day} | "{cell(words)}" | {cell(check)} |'
    text = path.read_text(encoding="utf-8")
    path.write_text(text.rstrip("\n") + "\n" + row + "\n", encoding="utf-8")
    out(row)
    return 0


# ------------------------------------------------------------------- digest
def git(root: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def rev_before(root: pathlib.Path, when: dt.datetime) -> str | None:
    """The last commit on HEAD before `when`, by commit time."""
    return git(root, "rev-list", "-1", f"--before={when.isoformat()}", "HEAD").strip() or None


def at(root: pathlib.Path, rev: str | None, rel: str) -> str:
    return git(root, "show", f"{rev}:{rel}") if rev else ""


def roadmap_rows(text: str) -> dict[str, tuple[str, str]]:
    return {n: (s.strip(), rest.strip()) for n, s, rest in reversed(ROW_REST.findall(text))}


_FINDING = re.compile(r"^#{2,3} *(F\d+)\b(.*)$", re.M)
_CLOSED = re.compile(r"closed|folded into", re.I)


def open_findings(text: str) -> dict[str, str]:
    """{F-number: its title} for every entry whose heading is not closed. The
    title is the heading's own text, or else the first line under it."""
    found = {}
    for m in _FINDING.finditer(text):
        f, rest = m.group(1), m.group(2)
        if _CLOSED.search(rest):
            continue
        title = rest.strip(" —-")
        if not title:
            after = (ln.strip() for ln in text[m.end():].splitlines())
            title = next((ln for ln in after if ln), "").strip("*")
        found[f] = title
    return found


def issues(run: Runner, start: dt.datetime, end: dt.datetime) -> tuple[list[dict], list[str]]:
    """(the escalation issues to show, problems reading them)."""
    shown, problems = {}, []
    for label in ESCALATIONS:
        r = gh(["issue", "list", "--label", label, "--state", "all", "--limit", "200",
                "--json", "number,title,url,state,updatedAt,labels"], run=run)
        if r.returncode != 0:
            problems.append(f"gh could not list {label}: {r.stderr.strip()[:120]}")
            continue
        for i in json.loads(r.stdout):
            upd = dt.datetime.fromisoformat(i["updatedAt"].replace("Z", "+00:00"))
            if i["state"] == "OPEN" or start <= upd < end:
                i["labels"] = sorted(lab["name"] for lab in i.get("labels", []))
                shown[i["number"]] = i
    return [shown[n] for n in sorted(shown)], problems


def section(text: str, title: str) -> str:
    for lvl, t, body in sections(text):
        if lvl == 2 and t.lower().startswith(title.lower()):
            return "\n".join(body).strip()
    return ""


def shadow(verdicts: list[dict], run: Runner) -> list[str]:
    """The Quartermaster's verdicts beside what became of each PR (Phase 391):
    in shadow the operator still merges, so the two can disagree."""
    out = ["## The Quartermaster (shadow)", "", f"Verdicts in the window: {len(verdicts)}."]
    for v in verdicts:
        r = gh(["pr", "view", str(v["pr"]), "--json", "state"], run=run)
        try:
            state = str(json.loads(r.stdout).get("state")).lower() if r.returncode == 0 else ""
        except (ValueError, AttributeError):
            state = ""                                 # gh's answer unreadable: said so below
        now = {"merged": "merged", "closed": "closed unmerged", "open": "open"}.get(state, "unknown")
        agree = ("not yet" if now == "open" else "unknown" if now not in ("merged", "closed unmerged")
                 else "yes" if (v["verdict"] == "merge") == (now == "merged") else "NO")
        named = ", ".join(v.get("failed") or []) or "none"
        out.append(f"- PR #{v['pr']} (phase {v['phase']}, head `{v['head'][:7]}`): "
                   f"{v['verdict']}, checks named: {named}. The PR now: {now}. "
                   f"Agrees with the operator: {agree}.")
    return out + [""]


def facts(root: pathlib.Path, day: dt.date, run: Runner,
          verdicts: list[dict] | None = None) -> str:
    tz = dt.datetime.now().astimezone().tzinfo
    start = dt.datetime.combine(day, dt.time(), tz)
    end = start + dt.timedelta(days=1)
    r0, r1 = rev_before(root, start), rev_before(root, end)
    out = [f"Window: {start:%Y-%m-%d %H:%M %Z} to {end:%Y-%m-%d %H:%M %Z}, commits "
           f"`{(r0 or 'none')[:7]}` to `{(r1 or 'none')[:7]}`.", ""]

    before, after = roadmap_rows(at(root, r0, "docs/ROADMAP.md")), \
        roadmap_rows(at(root, r1, "docs/ROADMAP.md"))
    changed = [(n, before.get(n), after[n]) for n in after if before.get(n) != after[n]]
    out += ["## The ROADMAP", "", f"Rows added or changed in the window: {len(changed)}."]
    for n, old, new in changed:
        was = "new" if old is None else (f"{old[0]} → {new[0]}" if old[0] != new[0] else "text changed")
        out.append(f"- **{n}** {new[0]} ({was}): {new[1][:200]}")
    active = [n for n, (s, _) in after.items() if s == ACTIVE]
    out += ["", f"Rows in progress at the window's end: {', '.join(active) or 'none'}.", ""]

    handoff = git(root, "log", "-1", f"--before={end.isoformat()}", "--name-only", "--format=",
                  "--", "docs/handoffs/").strip()
    out += ["## The newest handoff", ""]
    if handoff:
        text = at(root, r1, handoff)
        out += [f"`{handoff}`", ""]
        for t in ("What is open", "What is next"):
            body = section(text, t)
            out += [f"### {t}", "", body or "(no such section)", ""]
    else:
        out += ["None by the window's end.", ""]

    f0, f1 = open_findings(at(root, r0, "docs/FOLLOWUPS.md")), \
        open_findings(at(root, r1, "docs/FOLLOWUPS.md"))
    all1 = {f for f, _ in _FINDING.findall(at(root, r1, "docs/FOLLOWUPS.md"))}
    all0 = {f for f, _ in _FINDING.findall(at(root, r0, "docs/FOLLOWUPS.md"))}
    filed, closed = sorted(all1 - all0, key=lambda f: int(f[1:])), \
        sorted(set(f0) - set(f1), key=lambda f: int(f[1:]))
    out += ["## Findings (this repository's `docs/FOLLOWUPS.md`)", "",
            f"Open at the window's end: {len(f1)}. Filed in the window: "
            f"{', '.join(filed) or 'none'}. Closed in the window: {', '.join(closed) or 'none'}.",
            ""]
    out += [f"- {f}: {f1[f][:120] or '(no title on the heading line)'}"
            for f in filed if f in f1]
    out += ["", "## Escalations on GitHub (needs-admiral, needs-hands)", ""]
    shown, problems = issues(run, start, end)
    out += [f"- #{i['number']} [{i['state'].lower()}] {i['title']} ({', '.join(i['labels'])}) "
            f"{i['url']}" for i in shown] or ["None open, and none updated in the window."]
    out += [f"- PROBLEM: {p}" for p in problems]
    if verdicts is not None:
        out += [""] + shadow(verdicts, run)
    return "\n".join(out).rstrip() + "\n"


SUMMARY_SCHEMA = {"type": "object", "properties": {"summary": {"type": "string"}},
                  "required": ["summary"], "additionalProperties": False}
SUMMARY_BRIEF = """\
You are the Yeoman of the MotoDiag fleet. Below are the facts of one day,
gathered by a script. Write a summary for the operator in plain English, at
most 120 words: what moved, and what is waiting on the operator. Use only
these facts; do not open files or guess. Say what a finding or a phase is
about rather than only its number. If nothing waits on the operator, say so.
"""


#: What a summary may only repeat, never invent: a date, an F- or K-id, any
#: number of two digits or more. Bug fix #2: the first real digest said
#: "Phase 386 closed on 2022-10-22"; the facts said 2026.
_CHECKED = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b[FK]\d+\b|\b\d{2,}[A-Z]?\b")


def unsupported(summary: str, facts_text: str) -> list[str]:
    """The tokens in the summary that the facts do not contain. A bare number
    may be any run of digits in the facts: "October 23" restates 2026-10-23."""
    have = set(_CHECKED.findall(facts_text)) | set(re.findall(r"\d+", facts_text))
    return sorted({t for t in _CHECKED.findall(summary) if t not in have})


def digest(day: dt.date, *, root: pathlib.Path = ROOT, run: Runner = subprocess.run,
           out=print, verdicts: list[dict] | None = None) -> int:
    body = facts(root, day, run, verdicts)
    try:
        call = rank_call.call("yeoman", f"{SUMMARY_BRIEF}\n=== the facts ===\n{body}", HAIKU,
                              SUMMARY_SCHEMA, cwd=root, run=run)
    except Stop as e:
        out(f"STOP: {e}. No digest written.")
        return 3
    summary = str(call.structured.get("summary", "")).strip()
    if not summary:
        out("STOP: the summary is empty. No digest written.")
        return 3
    words = len(summary.split())
    invented = unsupported(summary, body)
    if invented:
        out(f"the summary named {', '.join(invented)}, which the facts do not hold: set aside")
        summary = (f"(The model's summary was set aside: it named {', '.join(invented)}, which "
                   "the facts below do not hold. Read the facts.)")
    page = (f"# Digest, {day.isoformat()}\n\n## In plain English (written by {HAIKU})\n\n"
            f"{summary}\n" + ("" if words <= 120 or invented
                              else f"\n({words} words, over the 120 asked for.)\n")
            + f"\n---\n\nThe facts below are the script's, not the model's.\n\n{body}\n---\n\n"
            f"{call.line()}\n")
    path = root / DIGESTS / f"{day.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    out(f"wrote {path.relative_to(root)}")
    out(call.line())
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--words", required=True)
    d.add_argument("--check", required=True)
    d.add_argument("--date")
    d.add_argument("--kid")
    g = sub.add_parser("digest")
    g.add_argument("--date", type=dt.date.fromisoformat, default=dt.date.today())
    a = ap.parse_args(argv)
    if a.cmd == "decide":
        return decide(a.words, a.check, date=a.date, kid=a.kid)
    return digest(a.date)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
