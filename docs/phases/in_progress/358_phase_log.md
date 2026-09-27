# Phase 358 — Process clean-up — phase log

**Status:** 🚧 In progress — v1.0 written, awaiting the operator before build
**Branch:** `phase-358` (Opus session, main checkout; the only writer since
the operator stopped the other session on 2026-09-27)

---

### 2026-09-27 — Opened

**The operator's decision on the triage, verbatim:**

> approved: 358 = K1–K8. order after: content phase (F159/F163/F166 templates + F158's 27 rows) → 356 → 357 → Track O.
>
> before 358 starts:
> 1. move the triage report into the repo at docs/reports/2026-09-27_process_kinks_triage.md and commit. rule 9 — nothing canonical lives only in ~/Documents.
> 2. the 071 deploy diff I approved: if any copy survives in the temp folders, recover it into the repo now with a dated note. if it's gone, say so and record the loss in the 358 log.
> 3. phase prompts move from ~/.cache/motodiag/prompts/ into the repo under docs/prompts/, and future ones are written there.
>
> 358 requirements:
> - K1: the whole-tree command is what the push guard runs. rule 3's list points at the command instead of listing checks. positive control: plant each of the four checks behind the 257–260 failures and show the command fails on each.
> - K3: deploy script in the repo. it writes the approved dry-run diff into the phase folder, and the live apply refuses to run without that file. no more temp copies.
> - K6 and K7 are closeout checks, not prose. K6: the regression line must parse to command + hash + count. K7: a log mentioning refute without a refute checklist fails. each has a known-bad fixture.
> - K8: step0 checklist item — every action the row promises has a way for a user to do it, or the row is rewritten before v1.0.
> - K9, amended: max 3 refute rounds. after round 3, remaining wording defects go to one finding; remaining factual or citation defects mean the row doesn't ship. fixes delete a sentence rather than rewrite it where possible. rounds 2+ refute the diff plus its surrounding sentences, not the whole row.
>
> content phase: decide "retire vs repair" for the two old starter templates at its step 0, with a count of every template and row that references them. not before.

**The operator's handover, verbatim:**

> you take over — you're the only writer on this repo from now on; the other session is stopped. items 1 and 2 are already done by it (docs/reports/2026-09-27_process_kinks_triage.md and docs/phases/completed/262_dryrun_diff.md) — verify both are committed and pushed, don't redo them. re-run the four rule-3 checks it claimed passed on the 071 diff commit and report the result.
>
> then item 3: phase prompts move from ~/.cache/motodiag/prompts/ and ~/.cache/motodiag/glm-builder/*/ into the repo under docs/prompts/, and future ones are written there. first commit on the 358 branch.
>
> then 358 step 0 per my message, report before v1.0.

**Before 358,** done by the stopped session (merge `4ffecec`) and verified
here:
- The triage was moved into `docs/reports/`.
- The 071 dry-run diff that the operator approved survived in Phase 262's
  builder scratchpad. It was recovered to
  `docs/phases/completed/262_dryrun_diff.md` with a dated note, and the
  original is kept byte for byte (sha256 `13a22578…c772`, re-checked here
  against the note and the source). **Nothing was lost.**
- Rule 3's four checks, re-run here on `e51699a`'s tree (`5fdfa8a`): 58
  passed, `finding_check` exit 0.

**Item 3:** done in `0f65f5b`, the first commit on `phase-358`. Ten prompts
moved, byte for byte. **Row 358 🚧:** `6d6f669`.

### 2026-09-27 — Step 0

Recorded in `358_step0.md` (`71687f5`). It ends in the rule-1 stop the
prompt names: the full whole-tree census, 72 files, takes 6 min 05 s,
against a 120 s hook timeout.

### 2026-09-27 — The operator's K1 decision and the three defaults, verbatim

> K1: option 3 — one command, two modes. guard runs the fast set (25 fast checks + finding_check). --full runs all 72, required before the regression of record and before commits in content phases. rule 3 names the command and both modes, nothing else. control on the split: plant a failure in one of the 47 excluded files, show fast passes and --full fails; and plant each of the four 257–260 failures, show fast fails on each.
>
> your three defaults accepted:
> - K3: live apply refuses unless the diff file is committed and unchanged — yes.
> - K6/K7 exemption: yes, but as an explicit pinned list of phase ids, not a cutoff. control: the list matches exactly the 10 you measured.
> - K9: extra column — yes.
>
> measure the hook timeout behaviour as you said, then write v1.0 and report before build.

### 2026-09-27 — The hook's timeout, measured: it fails open

A scratch project, outside the repo, held a `PreToolUse` hook on `Bash`. A
headless `claude -p` (Haiku) was asked to run `touch <marker>`. The hook
records when it starts and when it finishes.

| case | hook | timeout | marker | hook finished | reply |
|---|---|---|---|---|---|
| block now (control) | exit 2 at once | 5 s | absent | yes | "blocked", quoting "probe hook blocks" |
| block late | sleep 12 s, then exit 2 | 3 s | **present** | **no** | "done" |
| pass (control) | exit 0 at once | 5 s | present | yes | "done" |

The block-late case was repeated with the same result. **A hook that runs
past its timeout is killed, and the tool call proceeds.** The push guard
can only guard while it finishes inside 120 s.

### 2026-09-27 — K6, K7 and K9 exemption sets, measured for v1.0

- **K6 (A5 with a command):** 10 closed logs pass the old A5 and have no
  command: 255B, 255C, 255D, 257B, 257, 258, 259, 260, 353, 354. This is
  the operator's "10".
- **K7 (a mention of refute without the block or a one-line none):**
  40 closed logs of 312:
  - 212–217
  - 225B, 225–239
  - 242, 243, 244G, 244M, 244
  - 245–249
  - 254, 255B, 255D, 255, 256, 257B, 258, 259

  It includes the three known prose refutes (255B, 258, 259). A
  structural rule that looked only at headings and opening words found 7
  and missed 255B, so the literal rule was taken. **The operator's "the
  10" is K6's number. K7's list is its own measurement, pinned the same
  way, and is flagged in the report.**
- **K9 (the new column):** the 7 existing blocks: 257, 260, 261, 262, 264,
  353, 354.

### 2026-09-27 — v1.0 written

`358_implementation.md` v1.0. Before build, it is reported to the
operator, with one open question: whether the guard enforces its own
time limit.
