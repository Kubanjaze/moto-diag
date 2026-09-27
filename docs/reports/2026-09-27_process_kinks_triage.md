# Process clean-up triage: moto-diag after Track N

2026-09-27. Covers phases 257–272 (2026-09-23 to 2026-09-27). This copy in the repository is the canonical one. The operator keeps a personal copy in `~/Documents/motodiag-reports/`.

Every figure below was measured on 2026-09-27 from:
- the phase logs in `docs/phases/completed/`;
- `docs/FOLLOWUPS.md`;
- `pmset -g custom`;
- a listing of the session scratchpads.

When the triage was written, nothing in it had been changed. The operator's decision follows; the triage itself is unchanged below it.

---

## The operator's decision, 2026-09-27 (verbatim)

> approved: 358 = K1–K8. order after: content phase (F159/F163/F166 templates + F158's 27 rows) → 356 → 357 → Track O.
>
> before 358 starts:
> 1. move the triage report into the repo (docs/reports/2026-09-27_process_kinks_triage.md) and commit. rule 9 — nothing canonical lives only in ~/Documents.
> 2. the 071 deploy diff I approved: if any copy survives in the temp folders, recover it into the repo now with a dated note. if it's gone, say so and record the loss in the 358 log.
>
> 358 requirements:
> - K1: the whole-tree command is what the push guard runs. rule 3's list points at the command instead of listing checks. positive control: plant each of the four checks behind the 257–260 failures and show the command fails on each.
> - K3: deploy script in the repo. it writes the approved dry-run diff into the phase folder, and the live apply refuses to run without that file. no more temp copies.
> - K6 and K7 are closeout checks, not prose. K6: the regression line must parse to command + hash + count. K7: a log mentioning refute without a refute checklist fails. each has a known-bad fixture.
> - K8: step0 checklist item — every action the row promises has a way for a user to do it, or the row is rewritten before v1.0.
> - K9, amended: max 3 refute rounds. after round 3, remaining wording defects go to one finding; remaining factual or citation defects mean the row doesn't ship. fixes delete a sentence rather than rewrite it where possible. rounds 2+ refute the diff plus its surrounding sentences, not the whole row.
>
> content phase: decide "retire vs repair" for the two old starter templates at its step 0, with a count of every template and row that references them. not before.

What was done before 358 started:
1. **This report** was moved into `docs/reports/`.
2. **The 071 diff** was recovered. It survived in Phase 262's builder scratchpad and is now `docs/phases/completed/262_dryrun_diff.md`, with a dated note.
3. **Where the decision departs from the triage below:**
   - K9 is in scope, as amended above. The triage had listed it under "Needs your call".
   - The content phase's retire-or-repair choice is made at its own Step 0, not before.

---

## The recommendation

1. **You, no code:**
   - turn Low Power Mode off on AC power (K10);
   - decide the Subconscious plan before it cancels on Oct 23 (K11).
2. **One builder phase, row 358, "Process clean-up":** K1–K8.
   - K6, K7 and K8 change a rule's definition, so the prompt carries your wording for each. So does K9 if you pick it.
3. **One content phase after that:**
   - covers the two starter templates (F159, F166 and part of F163) and F158's 27 rows;
   - it changes live rows, so it stops for your approval as usual.
4. **Then the queue resumes:** 356 → 357 → Track O (273).

**Why the clean-up comes first:** K1–K4 cost time or add risk on every phase that follows. Row 357 adds a migration, which is where K1, K2 and K3 bite.

## What the run cost

- **Red full regressions: 5, all in 257–260.** Each came from a whole-tree check the builder's own choice of tests didn't run:
  - the F9 lint (257);
  - F124's head-pin guard (258, 260);
  - 209B's allowlist (259);
  - 244U's pinned count (259).

  Each serial run then took 45–55 minutes, so about 4 hours in total.
- **Since 261: 0 red regressions in 4 phases** (261, 264, 262, 272). Each prompt carried the list of checks by hand.
- **Regression wall time since the parallel suite (355):**
  - 15:11 (261);
  - 34:41 (264), the throttled machine;
  - 13:53 (262);
  - 11:15 (272).
- **Refute rounds:** 3 in 264 and 5 in 262.
- **Live migrations:** 5 in Track N (067–071). Each was checked against its dry run, with 0 incidents.

---

## Fix in the clean-up phase (row 358)

### K1. One command for the whole-tree checks
- **Seen:** the checks a builder must run before a commit are a list kept by hand. CLAUDE.md rule 3 lists 4, the GLM prompt listed 13, and there are more in reality. Of the four checks behind the five red regressions, only the F9 lint is in rule 3 today. The push guard runs only the ROADMAP check.
- **Fix:**
  - one script (for example `.claude/skills/closeout/wholetree.sh`) that runs every whole-tree check;
  - rule 3 names the script, not a list;
  - the push guard runs it;
  - a planted failure in each check must turn the script red.
- **Size:** small.

### K2. One pin per count
- **Seen:**
  - `len(UNREACHABLE_MODULES) == 34` is pinned in two files: `test_phase209B_integration_gaps.py:119` and `test_phase244Y_delete_pass.py:154`;
  - `ORPHANS == 102` (244U) and `MODULE_ISLANDS == 14` (244Y) are the same kind of pin.

  In 259 one duplicate was missed, which cost a second red regression.
- **Fix:** F124's pattern: one canonical pin per count, which other tests import.
- **Size:** small.

### K3. One deploy script, and the approved diff kept
- **Seen:**
  - The live-migration step was written 7 times, once per data phase: 353, 354, 259, 260, 261, 264 and 262. It covers backup, dry run on a copy, diff of every row, scope check, apply, and proof that live equals the dry run.
  - Every copy sits in a session scratchpad under `/private/tmp`, and none is in the repo.
  - The before-and-after diff you approved for 071 (`dryrun_diff.md`) exists only in a `/private/tmp` scratchpad.
- **Fix:** one script in the repo, which:
  - takes the scope as data;
  - keeps 5 backups;
  - runs the F158 census on the copy;
  - writes the diff you approve into the phase's own documents;
  - refuses the live apply unless live still equals the backup and a fresh copy stays in scope.
- **Size:** medium. **Highest value**, because it is the only step that touches production.

### K4. One F158 census, and the guard it proposed
- **Seen:** two census scripts give two answers on the same database.
  - Mine finds 68 hits in 46 rows, with three patterns.
  - 262's `f158.py` finds 79 hits in 47 rows, because it adds "this phase".
  - The guard test that F158 proposed was never written.
  - Text users see holds 39 hits in 27 rows today.
- **Fix:**
  - one census in the repo;
  - a ratchet test: the count may only fall, and no workflow row may have any.

  Fixing the 27 rows changes live rows, so it belongs to the content phase.
- **Size:** small.

### K5. Folded rows are unchecked
- **Seen:** rows 263 and 265–271 are "✅ Folded into NNN", with no CLOSED date and no documents. `roadmap_check.py` has no rule for them, so a fold that points at a phase that doesn't exist, or never closed, passes.
- **Fix:** R7: a folded row must name a phase that exists and is ✅ CLOSED.
- **Size:** small.

### K6. The regression line must name its command (a rule change: needs your words)
- **Seen:** closeout_check A5 accepts a regression line with a hash and a count and no command. Every phase since 355 prints the command, but nothing requires it.
- **Fix:** A5 requires the command.

### K7. A refute written as prose is invisible (a rule change: needs your words)
- **Seen:** verify_phase check 12 only sees the `/refute` skill's checklist block. 272 reports "no refuter block", which is correct because the gate ran no refute. But a phase that refuted in prose would report the same.
- **Fix:** if the phase log records a refute round, the checklist block is required. If it records none, the log says so in one line.

### K8. Step 0 checks the row's verbs, not only its nouns (a rule change: needs your words)
- **Seen:** row 272 said "run" the workflows, but nothing could run one. Step 0 greps the plan's nouns in `src/`, and "run" isn't a noun.
- **Fix:** for each thing the row says a user does, Step 0 names the user's entry point, or reports it missing.

---

## Needs your call

### K9. When a refute stops (a rule change)
- **Seen:** fixes add claims and new defects, which the next round then finds.
  - **264:** round 2 found 17 defects in round 1's corrected text. Two of them were round-1 fixes only partly applied.
  - **262:** 5 rounds. Round 3 tested 32 changed sentences: 25 kept, 3 kept loose and 4 killed, including round 2's own replacements. Your "one more round" rule stopped it.
- **Options:**
  - (a) At most 3 rounds. After round 2, only changed sentences are re-read. Wording defects left after the last round go to a finding, as F163 and F164 did.
  - (b) Prefer deleting a sentence to rewriting it, because a deletion adds no claim.
- **Recommendation:** (a) plus (b).

### K10. Low Power Mode on AC power
- **Seen:**
  - `pmset -g custom` shows `AC Power: lowpowermode 1`.
  - Regressions that aren't throttled take 11–15 minutes; the throttled one took 34:41 (264).
  - In 355, workers sat at 25–35% CPU while kernel_task ran at 63%.
- **Fix:** System Settings → Battery → Low Power Mode → "Only on Battery". It is a system setting, so only you can change it.

### K11. Subconscious plan
- **Seen:**
  - The Base plan gives 60M tokens a day, about 2 GLM phases, and resets at 00:00 UTC.
  - The plan page shows "Cancels Oct 23, 2026".
  - GLM built 258–260 fast and accurately on content, but weak on integration (see the 2026-09-25 findings report).
  - Since then it has been used for bulk reading only.
- **Decide before Oct 23:** renew it for bulk reading, or let it lapse and use the fallback route that rule 2 already provides.

---

## Park or drop

- **K12 — park.** Advisor reviews in one long session cost about 500K tokens of context per call. K3 and verify_phase turn most reviews into a script a fresh session can run, so the long advisor session can be retired after the clean-up.
- **K13 — park with K11.** In the GLM sandbox, `PYTHONPATH` breaks `test_phase209_packaging` (7 failures), and without `uv` the clone has no separate venv. This only matters if GLM builds resume.
- **K14 — fold into 357.** A `checklist_items.source` column for provenance, shown by `workflow show`, is a schema change. 357 already adds workflow tables.
- **K15 — drop.** The Subconscious 403 at 51.3M of 60M on 2026-09-25 was the daily allowance running out, and the fallback route carried Step 0. There is nothing to fix.
- **K16 — fold into K5.** The batch convention settled R6's one-close-per-number problem; K5 is the gap that remains.
- **K17 — drop.** A builder lost its API connection mid-turn (272). Its milestone commits left the state readable from disk, and it resumed in the same session.

---

## Content the run left open (findings, not process)

| finding | what | where |
|---|---|---|
| F158 | internal build references in text users see: 39 hits in 27 rendered rows | mostly known_issues |
| F159 | uncited figures the documents contradict, in "Brake and tire condition" | generic_ppi_v1 (starter) |
| F163 | defects outside F161's and F162's scope | starter templates, ppi_chassis_v1 |
| F164 | one sentence still unresolved in item 7 | crash_support_v1 |
| F165 | a workflow can't be run | rows 356, 357 |
| F166 | a required engine compression test on electric machines; engine oil asked of every machine | generic_ppi_v1 (starter) |

F159, F166 and part of F163 sit on the two starter templates that migration 007 seeded in Phase 114, to test the schema before any sourced content existed. Sourced templates now cover both jobs, and the starters point to them.

**An option for the content phase:** retire the starters (mark them inactive) instead of repairing unsourced text. One live change would close most of three findings. Gate 15's walk would change with it. This is your call when that phase comes.
