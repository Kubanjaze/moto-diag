---
name: finding
description: File a finding (F-number) in docs/FOLLOWUPS.md — how to allocate the next number across both repositories, what an entry must contain, and the check that every cited F-number actually resolves. Use when recording a defect, gap or deferred question found during a phase, or when a phase document says something was filed.
---

# finding — recording what you found but did not fix

## Why this folder exists

Phase 255C's plan stated that a question had been **"filed on the
general-applicability ticket."** It had not. The claim was written and the
entry was never created, and it surfaced only because someone went looking
for the ticket the plan cited.

**A document saying a thing was filed is not the filing.** That is the whole
of this folder, and `finding_check.py`'s B2 is that sentence made
executable.

## Allocating a number

```
.claude/skills/finding/next_f_number.sh
```

F-numbers are **one global sequence across both repositories** — moto-diag
and moto-diag-mobile. The script reads both files, prints the highest in
each, and gives the next free number. Taking the next from one file alone is
how two findings come to share a number.

## What an entry contains

```markdown
### FNNN

**One line naming the defect, not the symptom**

What is wrong, measured. What it affects, with numbers. What would close it.
```

Closed findings stay, marked `### FNNN — CLOSED by <what closed it>`. The
file is a record; removing an entry breaks every document that cites it,
which B2 will then report.

## The two assertions

| | |
|---|---|
| B1 | The header's "highest assigned is **FNNN**" matches the highest entry actually present |
| B2 | Every F-number cited by a completed phase document resolves to an entry that exists |

## The trap in B2, and why the rule is a list of names

`\bF\d+\b` is not a finding citation in this corpus. **`F650`, `F700`,
`F750`, `F800`, `F850` and `F900` are BMW motorcycles**, and `F401` is a
flake8 code in a `# noqa:` comment. This is a motorcycle knowledge base; a
bare `F` plus digits is a model designation at least as often as a finding.

The first cut excluded them with a **ceiling** — ignore anything above the
highest assigned number — and the known-bad fixture caught why that is
wrong. A phase citing `F139` when the file stops at `F138` is *exactly* the
failure this folder exists for, and the ceiling silently skipped it. **The
rule that removed the false positives removed the true positive too.**

So exclusions are **named**, with a reason each, in `NOT_FINDINGS`. A named
list cannot hide a citation one past the end.

`KNOWN_DANGLING` pins four historical citations that do not resolve — three
proposed by Phase 192 and never filed, and `F48`, which is not a finding at
all but a **phase** whose documents cite their own name. Anything not in
that set fails. The pin may shrink, never grow silently.
