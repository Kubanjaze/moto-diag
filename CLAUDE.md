# moto-diag — project rules

Cross-project rules live in the workspace `CLAUDE.md`. This file holds what
is true of **moto-diag specifically**, and is loaded when a session starts
here.

@../workspace-docs/claude/working-rules.md

## Start sessions at this repository root

Skills and hooks under `.claude/` are discovered **from the directory the
session was started in, at the moment it starts.** A session opened in the
parent directory does not see them, and a skill added part-way through a
session is not available until the next one. Measured in Phase 255D, at
both candidate roots, before this rule was written.

No symlinks and no `.claude/` at the parent: both work, and both hide where
the mechanism is actually reading from.

## Every session starts from the plan, and the ROADMAP moves with the work

**Before acting, read what the last session left.** This file and the
working-rules index load by themselves; then read:

- `docs/ROADMAP.md`: the current phase's row and the rows around it (the
  status key is in its header)
- `ROADMAP_AUTHORITY.md`: which repo's ROADMAP owns a phase (185–204 are the
  mobile repo's; every other number is this repo's)
- the newest file in `docs/handoffs/`
- `docs/FOLLOWUPS.md`: open findings that touch the work
- the phase's own documents in `docs/phases/in_progress/`, and the previous
  phase's `implementation.md` (what it locked)
- for work that touches the app, `../moto-diag-mobile/docs/ROADMAP.md` too

**The ROADMAP is the ledger, and it is updated as the work happens, not at
the end:**

- A phase gets its row **before its Step 0**: the next free number (or a
  letter for a follow-on, like 255B), a title, and 🚧.
- The row changes with the work (v1.0 committed, a batch written, a pause as
  ⏸️ with the reason) and closes as ✅ with the regression line at close-out.
- A number is never reused. A displaced row moves to the next free number and
  says what it was ("Was 256; …").
- Work that is not a phase, such as a rule change like this one, goes in
  this file's change log and the skill's `CHANGELOG.md`, not in the ROADMAP.

`.claude/skills/closeout/roadmap_check.py` holds the ledger to this: a reused
number, a phase with documents but no row, a row whose status disagrees with
where its documents are, a number no authority range covers, and the two
copies of the authority contract drifting apart.
`tests/test_roadmap_continuity.py` runs it with every suite, and the push
guard refuses any `git push` while it fails.

## Procedure folders

Recurring procedures are skills in `.claude/skills/`, each with its own
dated changelog, a script for anything that is "run this and check that",
and a hand-written known-bad fixture its assertion must fail on.

| folder | what it covers |
|---|---|
| `closeout` | finishing a phase; the seven artefacts; `verify_phase.sh` |
| `finding` | filing an F-number; every cited number must resolve |
| `refute` | an adversarial pass, and the checklist it must emit |

The enforcement is a test, never the skill's own text: a skill is a prompt
and can be talked out of; `tests/test_phase255D_*_contract.py` cannot.

---

## MotoDiag-Specific Context

**Repo:** `Kubanjaze/moto-diag` | **Local:** `~/Projects/moto-diag`

> The local path was corrected when this file was created: the line carried a
> Windows path (`C:\Users\Kerwyn\PycharmProjects\...`) that has not been true of
> this machine for some time. Everything else below is moved verbatim.

### MotoDiag track summary (198 phases, 11 tracks)

> Historical: the original plan, kept verbatim. The live plan is
> `docs/ROADMAP.md` (Tracks A–T, phases 01–354 plus letter follow-ons), and
> Track I is 185–204 per `ROADMAP_AUTHORITY.md`, not 173–192 as below.

- A (01-12): Core Infrastructure
- B (13-78): Vehicle Knowledge Base (Harley, Honda, Yamaha, Kawasaki, Suzuki, cross-platform)
- C (79-95): AI Diagnostic Engine
- C2 (96-108): Media Diagnostic Intelligence (video/audio analysis)
- D (109-121): CLI + User Experience
- E (122-135): Hardware OBD Interface
- F (136-147): Advanced Diagnostics
- G (148-162): Shop Management + Optimization
- H (163-172): API + Web Layer
- I (173-192): Mobile App (iOS App Store + Google Play Store, React Native, universal device support)
- J (193-198): Ship + Scale

---


---

## Change log

### 2026-09-24 — the ROADMAP moves with the work, and a check holds it there

The phase after 257 was about to start from a handoff note, with no ROADMAP
row. Looking for where its row should go found two older gaps nobody had
seen: two rows numbered 256 (the retrieval chokepoint took the number on
2026-09-21 and the planned "Scooter electrical" row kept it), and row 353
outside every range of `ROADMAP_AUTHORITY.md`. Each was something the ledger
claimed that no check tested.

Changed: the section "Every session starts from the plan" above;
`roadmap_check.py` (R1–R5, a known-bad and a good fixture tree,
`--self-test`) and `tests/test_roadmap_continuity.py`; the push guard runs it
on every push; "Scooter electrical" moved from the second 256 to 354; the
ROADMAP header gained a status key (🚧 is new); and `ROADMAP_AUTHORITY.md`'s
backend range became open-ended (205+) in both repos. The contract asks for
an amendment to be recorded in both repos' phase logs. No phase was open, so
it is recorded in the contract's own dated line and in both commits, and the
next phase's log cites it.

Proven: on the ROADMAP as it stood on `master`, the check reports exactly R1
(256) and R4 (353). Breaking R1, or the guard's refusal, turns the tests red.
An operator request made between Phase 257 and the next; not a phase.

### 2026-09-23 — the working-rules index is imported (Phase 257)

Nothing loaded the workspace rules in this repo: a session started here saw
this file and nothing else. Phase 257 then committed an exclusion with no
positive control (bug fix #1, `6639490`) — a rule the index states in one
line. The `@../workspace-docs/claude/working-rules.md` line under the
opening paragraph imports the lean index (9 KB) into every session started
at this root. The first session after this change asks once to approve the
external import.

Proven 2026-09-23: before approval a headless `claude -p` at this root, all
tools disabled, answered NOT LOADED; the operator approved the import in an
interactive session, which quoted the first Evidence rule without opening a
file; a headless session afterwards, tools disabled, quoted it verbatim.

### 2026-09-22 — created (Phase 255D)

moto-diag had no `CLAUDE.md` of its own. Its rules sat in the workspace
file in front of every session for every project. Created here with the
MotoDiag-specific context moved verbatim, plus the two rules Phase 255D
measured: repo-rooted sessions, and where the procedure folders live.
