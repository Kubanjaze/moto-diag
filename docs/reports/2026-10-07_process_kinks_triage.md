# Process clean-up triage: moto-diag after Track O and the warranty rows

2026-10-07. Covers the 17 phases closed since Phase 358 (2026-09-27 to 2026-10-07): 359, 356, 357, 360, 361, 274, 275, 281, 369, 370, 273, 292, 373, 374, 377, 376 and 375. This copy in the repository is the canonical one. It continues 358's numbering: K1–K17 are in `2026-09-27_process_kinks_triage.md`.

Every figure below was measured on 2026-10-07 from:
- the phase logs in `docs/phases/completed/`;
- `docs/FOLLOWUPS.md` in both repositories;
- the code of the close-out, deploy and finding skills;
- `pmset -g custom`;
- the advisor's running list of kinks.

When the triage was written, nothing in it had been changed. The operator's decision follows; the triage itself is unchanged below it.

---

## The operator's decision, 2026-10-07 (verbatim)

> approved: 378 = K18–K25. K22: fix the README line too. K23: the standing lines move into checks or CLAUDE.md's "How a phase runs". K24: add the line to the close-out skill. K26: (a). K27: (a) now, (b) once the first shop's real data is in. K11: I'll decide by Oct 23.

The operator sent it to the session that had just closed Phase 375. That session opened Phase 378 from it and wrote the same words into `docs/prompts/378_process_cleanup_2.txt` (`12b21f6`).

What came of it:
- **Phase 378** built K18–K25 and merged as `9b8b155` on 2026-10-08. Its regression of record is 10723 passed at `bdc063d`.
- **K26 and K23** are CLAUDE.md's new rule 6. K18's order is in rule 4. **K27** is in the deploy skill's text.
- **K11** is still the operator's, by Oct 23.
- **F197**, found by the advisor verifying 378: K25's `verify-live` reports a mismatch with the approved diff but exits 0, and check 8 does not gate on it.

---

## What 358's triage left open

- **K10, Low Power Mode on AC: done.** `pmset -g custom` shows `lowpowermode 0` on AC and on battery.
- **K11, the Subconscious plan: still yours, by Oct 23.** The plan page showed "Cancels Oct 23, 2026".
- **K12, parked:** reviews inside one long advisor session. K25 below would turn a deploy's review into one command a fresh session can run.
- **K13, parked with K11.**
- **K14, not done.** `checklist_items.source` was to fold into 357. Neither 357 nor any later migration added it.

## The recommendation

1. **You, no code:**
   - K11 by Oct 23;
   - your words where a rule changes (K22's README line, K23, K24), and your call on K26 and K27.
2. **One builder phase, row 378, "Process clean-up 2":** K18–K25.
3. **Then your next call:** F192, the reference-data track (293–302), or the open findings.

**Why now:** K18 and K19 each caused a failure or a near miss in the last two days. 376 applied a migration before its regression, and F196 turned a test red every evening. K20 turns the backend red the next time mobile files a finding. Each fix is small.

## What the run cost

- **17 bug fixes in 17 phases:**
  - 359: 4; 375: 3;
  - 281 and 273: 2 each;
  - 356, 360, 274, 370, 292 and 373: 1 each.
- **13 live migrations (072–084), 0 incidents.** Each was dry-run on a copy, approved where it changed rows, and checked against its backup afterwards.
- **Three second regressions of record, all from the fold pin (K21):**
  - 274: 30 min 4 s;
  - 275: 18 min 55 s;
  - 281: one run lost a worker to F183, then a rerun of 20 min 11 s.
- **Clock-made test failures: 4** (K19).
- **Planned mobile stops: 4** (360, 361, 281, 377), by design: the API snapshot is a contract between the two repositories.

---

## Fix in the clean-up phase (row 378)

### K18. One deploy order, enforced
- **Seen:**
  - The close-out skill's step 8 says "Merge, then deploy".
  - But `deploy.py` reads the scope and the approved diff only from `docs/phases/in_progress/`, and close-out step 6 moves them to `completed/` before the merge.
  - So every phase with a migration applies live from its branch, before the close-out commit.
  - Nothing fixes when that happens relative to the regression of record. 376 applied 083 before its regression (`e452b99` records "083 live"); 377 and 375 applied after theirs.
  - If a regression went red after an early apply, the migration its fix might have to change would already be live.
- **Fix:**
  - the close-out skill states one order: regression of record, then apply live from the branch, then the close-out commit (which moves the deploy files), then the merge;
  - `apply-live` refuses unless the phase log has a regression line at a commit with no `src/` or `tests/` change against HEAD. verify_phase's check 2 already computes that diff;
  - known-bad fixtures: a phase log with no regression line, and one whose regression commit is behind a code change.
- **Size:** small.

### K19. Tests that read the real clock: a guard, not a sentence
- **Seen:** four failures from a test turning the real clock into a day, month or minute.
  - **F10:** gate 9 and the Phase 178 quota tests failed on a month's last evening. Fixed by 370.
  - **370 bug fix #1:** Phase 176's 429 test failed once in 29 runs, on a wall-clock minute.
  - **F196:** a 275 export test failed every evening from 20:00 to 24:00 EDT, from 377 until 375's bug fix #1.
  - **F196, widened:** 274's P&L test failed on a month's last evening (375's bug fix #2).

  375 found 9 such lines in 6 files by a stated rule. It cleared them with the whole process's clock faked by libfaketime. Every prompt still carries the line "never record a regression on a month's last day after 20:00 EDT".
- **Fix:**
  - **a whole-tree test,** like 377's census of `src/`. It pins the test lines that turn the real clock into a day, month, year or minute, and fails on any new line that does not use 370's frozen clock;
  - **a script** that runs the pinned files with the clock faked at 375's four moments: a month's last evening, an ordinary evening, New Year's Eve, and 00:30. The close-out skill names it;
  - after both, the prompt line can go.
- **Size:** small.

### K20. A finding filed in mobile turns the backend red
- **Seen:**
  - `finding_check` B1 compares the backend header's "highest assigned" with the union of both repositories' entries (`present |= entries(sibling)`).
  - The mobile header states only its own file's highest ("F181 (this file)").
  - So when mobile files a finding above the backend's highest, the backend's B1 fails until a backend commit updates its header. It happened with F179 (360) and F181 (361).
  - A mobile session cannot make that commit, since another repository needs its own session.
- **Fix:**
  - each header states its own file's highest, and B1 checks that;
  - `next_f_number.sh` keeps allocating from the union;
  - known-bad fixtures: a sibling with a higher number must not fail B1, and a stale own header must.
- **Size:** small.

### K21. The fold pin forces a second regression
- **Seen:** `tests/test_roadmap_continuity.py` pins the 18 folded rows as a literal. A batch close folds rows, so its close-out edits this test after the regression of record. verify_phase's check 2 then demands another run, which is what happened in 274, 275 and 281.
- **Fix:** derive the folds from the ROADMAP with a second, independent parse, and keep R7's planted fixtures as the control. Then there is nothing to edit at close-out.
- **Size:** small. It matters again the next time rows are batched.

### K22. Stale labels
- **Seen:**
  - verify_phase.sh's check 11 heading and the close-out skill's description say "seven artefacts". `closeout_check` has had eight (A1–A8) since 358.
  - README.md lines 231–232 still say a skill added mid-session is not available until the next one. CLAUDE.md removed that clause on 2026-09-27, but README was outside the change you approved.
- **Fix:** correct both. The README line needs your words.
- **Size:** tiny.

### K23. Rules that live only in prompts (needs your words)
- **Seen:** every prompt since 359 carries the same ten carry-forward lines.
  - **Some are already enforced elsewhere.** 244G's scanner runs in the fast whole-tree check (`test_phase244G_guard_shapes.py` is one of its 37 files). The push guard refuses a commit and a push in one command.
  - **Others live nowhere else:** the deploy order (K18) and the clock rule (K19).
  - So a phase started without an advisor's prompt would miss them.
- **Fix:** each standing line either becomes a check (K18, K19) or moves to CLAUDE.md's "How a phase runs". Prompts then carry only the phase's own facts and stops.
- **Size:** small.

### K24. A script whose output ships is committed with it (needs your words)
- **Seen:**
  - 359 lost `gen072.py` when a restart cleared `/private/tmp` (359's bug fix #3). Its output, `LIVE_ROWS_072`, ships in `src/`.
  - Later phases commit their generators in the phase folder (`377_live_rows_preview.py`, `376_mutate.py`), but only by habit.
- **Fix:** one line in the close-out skill. A script whose output ships, or whose output a migration loads, is committed in the phase folder with it.
- **Size:** tiny.

### K25. A deploy's check as one command
- **Seen:**
  - Every deploy since 359 was checked against its backup with scripts kept in a session scratchpad: a backup-API copy, a comparison of schema and rows, and field diffs. `/tmp` cleanup wiped them once (370).
  - verify_phase's check 8 prints only the schema version and the `known_issues` count.
  - Opening a backup read-only leaves `-shm` and `-wal` files beside it.
- **Fix:**
  - `deploy.py verify-live <phase>`, read-only. It copies live and the phase's backup through SQLite's backup API, opening the backup with `immutable=1`;
  - it prints the schema objects added, removed and changed, the tables whose rows differ, integrity and foreign keys;
  - verify_phase's check 8 calls it.
- **Size:** small to medium.

---

## Needs your call

### K11 (carried). The Subconscious plan
Decide by Oct 23: renew it for bulk reading, or let it lapse. Rule 2's fallback route already exists.

### K26. Builders installing software
- **Seen:** 375 installed libfaketime with Homebrew (0.9.13, from homebrew/core), without asking, to fake the clock for K19's check. Nothing says whether a builder may install software. It was useful and harmless.
- **Options:**
  - (a) allowed for Homebrew core tools a test needs, named in the phase log and the handoff;
  - (b) ask first, as for a credential.
- **Recommendation:** (a).

### K27. Five backups
- **Seen:** three live migrations went in on 2026-10-07 alone (082, 083, 084). With five kept, the oldest backup is from 2026-10-06 17:34. A defect found more than five deploys after its migration has no backup from before it. Each backup is 31 MB.
- **Options:**
  - (a) keep 5;
  - (b) keep 5, plus the first backup of each week;
  - (c) keep 10.
- **Recommendation:** (a) while live holds smoke data, and (b) once the first shop's real data is in.

---

## Park or drop

- **K28: keep as is.** When you paste a decision I drafted, the builder asks whether it is yours (373, 375). That is rule 1 working as you set it on 2026-09-25: "asking was right; record that it has to stay that way".
- **K29: drop.** The edit guard blocked close-out commands chaining `sed -i` (361, 275), a docs edit naming `tests/` through a variable (370), and a script edit to `src/` (376). It fails closed by design, and the remedy, the Edit tool, worked each time.
- **K30: drop.** A commit went past a red fast check through `wholetree.sh | tail` (361). The push guard would have refused the push, and builders now run the check on its own.
- **K31: park.** The push guard checks the working tree, so pushing a planned stop's docs means stashing the held work (361). It has not recurred.
- **K14: park as a product row.** `checklist_items.source` is a schema and CLI change, not a process one.
