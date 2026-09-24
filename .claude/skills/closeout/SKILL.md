---
name: closeout
description: Close out a moto-diag phase — the ordered sequence from "the code is green" to "merged, deployed and verifiable", and the seven artefacts that must exist when it is done. Use when a phase's build is complete, when asked to close or finish a phase, or before merging a phase branch to master.
---

# closeout — finishing a phase

A close-out is not paperwork. It is the step that makes a phase **checkable
by someone who was not there** — which, a week later, includes you.

## What "done" means

Seven artefacts. Each one is something a skipped close-out leaves undone,
and each is a file fact rather than a claim:

| | artefact |
|---|---|
| A1 | Both phase docs in `docs/phases/completed/`, neither left in `in_progress/` |
| A2 | The phase log's status line reads Complete |
| A3 | The implementation doc has a **Deviations** section |
| A4 | Bug fixes are a contiguous dated register from `#1`, each naming a commit that **resolves** (`git cat-file -e`) |
| A5 | A regression line carrying **both** a commit hash and a passed-test count |
| A6 | A ROADMAP row whose **body cell** is within 120 words |
| A7 | An `implementation.md` history row, and a version header naming the phase |

`closeout_check.py` decides all seven. The test and the push guard both call
it, so they cannot drift apart.

**"Closeout ran" is deliberately not one of them.** It is unfalsifiable from
inside a repository, and a check that cannot fail is the defect this whole
folder exists to stop shipping.

## The sequence

1. **Regression, with hash and count.** Full suite. Record both numbers in
   the phase log — A5 checks for them together, because a count without a
   commit does not say *which tree* was green.
2. **Deviations.** Write what the phase did that the plan did not say. If
   nothing deviated, say that; an empty section is a claim, not an absence.
3. **Bug-fix register.** One dated entry per fix: Issue / Root cause / Fix /
   Files / Verified / Commit. Numbering contiguous from `#1`.
4. **ROADMAP row.** Under 120 words by `roadmap_words.py`. The method is
   specified in the workspace CLAUDE.md rule; the script is the only place
   it is executed.
5. **`implementation.md`** — history row and version bump.
6. **Move both docs to `completed/`**, set the status line.
7. **Merge, then deploy with a backup** — `~/backups/motodiag/`, retain 5,
   print the before-state, dry-run on a copy first.
8. **`verify_phase.sh PHASE REG_HASH TIP`** and read all thirteen checks.

## When a step may be skipped

Any of them, if the phase genuinely did not produce that artefact — a phase
with no bug fixes writes no register. **What may not happen is skipping a
step silently.** Say which, and why, in the phase log. The check will fail
and that failure is the prompt to write the reason down, not to delete the
check.

## Files here

| file | what it is |
|---|---|
| `closeout_check.py` | the seven assertions; the single implementation |
| `roadmap_words.py` | the single implementation of the 120-word count |
| `verify_phase.sh` | the operator's terminal check, parameterised |
| `code_after_regression.py` | check 2's scope: every path is code unless positively documentation (F137) |
| `roadmap_check.py` | the ROADMAP ledger holds: R1–R5 (a reused number, documents with no row, a status that disagrees with where the documents are, a number no authority range covers, the authority copies drifting); run with every suite and on every push |
| `pre_push_guard.sh` / `_pre_push_guard.py` | the push guard: the ROADMAP check on every push, close-out on a push to `master` |
| `fixtures/bad`, `fixtures/good` | hand-written control pair |
| `fixtures/check2` | hand-written path lists for check 2 |
| `fixtures/roadmap_bad`, `fixtures/roadmap_good` | hand-written trees: every R-rule fires on the first; the second holds what each rule must not remove |
| `CHANGELOG.md` | what changed here and why |

## Two things that will bite you

**A hook takes about one turn to load.** A guard written and tested in the
same turn looks broken. Wait a turn before concluding anything.

**A blocking hook on `Bash` takes away `Bash`** — including the command that
would remove it. Recovery is to edit `.claude/settings.json` with the
**Write tool**, which does not pass through a `Bash` matcher. This is why
the guard exits 0 before doing any work unless the command really is a
`git push` to `master`.
