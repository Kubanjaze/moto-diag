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
- the newest handoff in `docs/handoffs/`. Two can share a date, so let git
  name it: `git log -1 --name-only --format= -- docs/handoffs/`
- `docs/FOLLOWUPS.md`: open findings that touch the work
- the phase's own documents in `docs/phases/in_progress/`, and the previous
  phase's `implementation.md` (what it locked)
- for work that touches the app, `../moto-diag-mobile/docs/ROADMAP.md` too

**The ROADMAP is the ledger, and it is updated as the work happens, not at
the end:**

- A phase gets its row **before its Step 0**: the next free number (or a
  letter for a follow-on, like 255B), a title, and 🚧.
- The row changes with the work (v1.0 committed, a batch written, a pause as
  ⏸️ with the reason) and closes as ✅ at close-out, with
  `**CLOSED YYYY-MM-DD.**` and the regression line.
- A number is never reused. A displaced row moves to the next free number and
  says what it was ("Was 256; …").
- Work that is not a phase, such as a rule change like this one, goes in
  this file's change log and the skill's `CHANGELOG.md`, not in the ROADMAP.

`.claude/skills/closeout/roadmap_check.py` holds the ledger to this: a reused
number, a phase with documents but no row, a row whose status disagrees with
where its documents are, a number no authority range covers, the two
copies of the authority contract drifting apart, and a phase closed with no
handoff (R6).
`tests/test_roadmap_continuity.py` runs it with every suite, and the push
guard refuses any `git push` while it fails.

## How a phase runs: five standing rules

Standing since 2026-09-24. The operator had to give each of these more than
once.

1. **A phase runs to its finish line.** It stops for the operator only for:
   - a real fork, meaning two plans that would ship different things
     (present the options; the operator picks);
   - a change to a threshold or to a rule's definition;
   - a test it cannot make green;
   - a login or a credential;
   - a live-database change that alters or deletes existing rows.

   Loading new rows after a backup is not a stop. Anything else it decides,
   and it writes the decision and the reason in the phase log.

   **Only the operator grants a stop's approval, in their own words.** An
   agent never grants it to itself, to another session, or to a later step
   of its own plan. A prompt can carry a pre-approval only as the
   operator's scoped wording, and the agent applies that scope literally.
   Take 068's live row as the example: "apply live only if the dry run on
   a copy changes exactly the named row plus the phase's own new rows; show
   the diff; anything else changes, stop and ask."
2. **Bulk reading goes through Subconscious (GLM-5.3); judgment stays on
   Opus.**
   - GLM does census, acquisition, extraction and first-pass classification,
     through `subc claude` or the orchestrator's `--source-route subconscious`.
   - Opus does refute, writing entries and merging.
   - While Subconscious is down, `--source-route anthropic` is the fallback,
     and every entry records its `source_route`.
   - An unattended GLM run must be technically unable to write outside its
     own worktree, proven by a planted write that fails. An instruction to
     stay inside is not a boundary.
3. **Four whole-tree checks run before every commit**, whatever the commit
   touches:
   - `tests/test_phase191c_f9_lint.py`
   - `tests/test_phase244G_guard_shapes.py`
   - `tests/test_roadmap_continuity.py`
   - `python3 .claude/skills/finding/finding_check.py`

   B2 reads only `completed/`. Before the regression of record, also run
   `finding_check.check(Path("."), phase_docs="docs/phases/in_progress")`.
   A suite chosen by subject misses these checks. In 257 the F9 lint went
   red only at the full regression, and B2 only once the documents had moved
   to `completed/`, which cost a second 45-minute regression.

   **The regression of record runs in parallel** (Phase 355):
   `.claude/skills/closeout/regression.sh` runs
   `python -m pytest -n auto --dist load` on a clean tree and prints the
   line the phase log records, with the counts, the hash, the wall time and
   the command. `regression.sh --serial` is the fallback, for a machine
   without pytest-xdist or for bisecting a failure seen only in parallel.
   A test that fails only in parallel is a bug to fix, never a reason to
   record the serial run. Never put `-n` in `addopts`: the gate tests spawn
   pytest, and each spawned run would start its own worker pool.
4. **Every close-out writes a handoff:**
   `docs/handoffs/YYYY-MM-DD_<phase>_closed.md`, saying what shipped, what
   is open and what is next. It goes in the close-out commit, before the
   merge; the deploy's outcome is added after it runs. `roadmap_check.py`
   R6 refuses any push while a phase closed since 2026-09-24 has none.
5. **One writing session at a time on this checkout.** Any other session
   only reads: no commits, branch switches or edits while a builder works.
   A second writer gets its own worktree.

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

### 2026-09-25 — the regression of record runs in parallel (Phase 355)

Rule 3 gained a paragraph. The regression of record is
`.claude/skills/closeout/regression.sh`, which runs
`python -m pytest -n auto --dist load` and prints the line to record,
with its command. `--serial` is the fallback. Never put `-n` in
`addopts`. The reason is the gate tests that spawn pytest: each spawned
run would start a worker pool inside a worker. Held by
`tests/test_phase355_parallel_suite.py`, which went red on a planted
`-n auto`. Proven in Phase 355: the parallel run's passed IDs equal the
serial run's. Serial took 30:33 and parallel 13:28 on comparable
conditions.

### 2026-09-25 — only the operator grants a rule-1 approval

On 2026-09-25 the advisor session asked the operator to pre-approve
migration 068's rewrite of one live row, and phrased the question as
"approving it now lets the builder run straight through". The operator
answered with a scoped approval and a rule: "an agent never grants itself
a CLAUDE.md rule-1 approval — you nearly did … asking was right; record
that it has to stay that way." Rule 1 now says so, and says that a
pre-approval travels only as the operator's scoped wording, applied
literally. Text only; there is no check an agent could run on itself for
this.

### 2026-09-24 — five standing rules, and R6: every close-out leaves its handoff

The operator had given each of these rules in session prompts, some of them
several times, and none was in a file a new session loads. They are now in
"How a phase runs" above. What else changed:
- The read list names the newest handoff with a git command, because
  `2026-09-24_353_closed.md` and `2026-09-24_354_closed.md` share a date.
- The ledger bullet asks for `**CLOSED YYYY-MM-DD.**`.
- `roadmap_check.py` gained R6.

R6 was proposed as "the newest handoff is at least as new as the newest
close", and measured before it was written. Four phases closed on
2026-09-24; two wrote a close-out handoff, and 257 and 257B, which predate
the rule, are exempt by name. A date-only rule passes that day, and would
still pass it with 353's handoff deleted, because 354's has the same date.
So R6 is per phase: every close needs its own `_closed` handoff, dated no
earlier than the close. It sees a close through the ✅ row's date or
through `implementation.md`'s history row.

The push guard now refuses a close-out push that has no handoff, so the
handoff is written before the merge, not after the deploy as 353 and 354
did.

Proven:
- R6 fires on exactly the five planted cases in `fixtures/roadmap_bad`.
- `fixtures/roadmap_good` passes; it holds the exemption's control and a
  second close on one day with its own handoff.
- On the real ledger, deleting 353's handoff is caught.
- Five deliberate breaks each turned `tests/test_roadmap_continuity.py` red,
  and all five were reverted: ignoring the date, the date-only rule, dropping
  the history source, accepting a mid-phase handoff, and removing 257 from
  the exemption.

Rules 1, 2, 3 and 5 are text. Rule 4 is enforced on every push. An operator
request made between Phase 353 and 258; not a phase.

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
