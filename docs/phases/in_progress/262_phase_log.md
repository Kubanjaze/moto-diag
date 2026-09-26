# Phase 262 — Track N batch 3: crash support, track-day preparation, and emissions compliance — phase log

**Status:** 🚧 In progress
**Branch:** `phase-262` (Opus session, main checkout)

---

### 2026-09-26 — Opened: Track N batch 3

The operator's prompt, 2026-09-26: start Phase 262, Track N batch 3 of
3, and run it to its finish line. Batch 3 is rows 262 (crash and
insurance claim support), 263 (track-day and race prep) and 267
(emissions and smog compliance, California first). Then gate 272.

**Ledger convention, 261's and 264's, as the operator restated it.** 262
carries the batch. Rows 263 and 267 close ✅ "folded into 262" with no
CLOSED date. One history row (262) and one handoff.

**Also in scope, in the same migration** (the operator's words):
1. "F161: generic_winterization_v1's four live items carry figures no
   maker's document supports … Remove each unsupported figure or replace
   it with a pointer to the cited winterization_v1."
2. "F162: fix the two further defects the batch-2 reviewers found in
   ppi_chassis_v1."
3. "W30: the one claim added in batch 2's third refute round that has had
   no adversarial read. Give it one, and fix or drop it on the verdict."

**The operator's stop, recorded as given:** "Items 1 and 2 alter
existing live rows, which is a rule-1 stop: back up to ~/backups/motodiag/
first and keep 5; dry-run on a copy; run the F158 census on the copy;
show me every changed row with before and after text, and wait for my
answer before the live apply." No pre-approval of the live apply exists.

**The operator's Step 0 condition:** "If Step 0 finds a row that cannot
be sourced from primary documents, stop and give me the options. Row 262
especially may not be a manual topic."

**Carried forward** (the operator's list): F124, and migration tests that
survive the next migration; no test reads `data/motodiag.db`; no internal
references in any text a user sees (F158); whitespace-proof negatives
with a control on the cited page; names from title pages; the Edit tool
for source edits, and nothing in `/tmp`; and batch 2's lesson: "every
refute round's fixes introduced defects the next round found. After the
last fix round, re-read every claim whose text changed." Regression by
`.claude/skills/closeout/regression.sh`.

Read before acting: CLAUDE.md and the working-rules index; ROADMAP rows
258–272 and the status key; `ROADMAP_AUTHORITY.md`; the newest handoff
(`2026-09-26_264_closed.md`, named by `git log`); F161 and F162 in
`docs/FOLLOWUPS.md`; 264's implementation, phase log and Step 0; F158.

Branch `phase-262` from `master` at `1c836ee`. **Ledger step:** row 262 →
🚧 (65 words by `roadmap_words.py`). The row went in after the first
library census had run, not before it: a lapse against CLAUDE.md's "a
row before its Step 0", recorded here. The census changed nothing on
disk.

### 2026-09-26 — Step 0: the fork the operator anticipated, and the answer

The measurements are in `262_step0.md`. In short:
- **The three categories exist** (`CRASH_SUPPORT`, `TRACK_PREP`,
  `EMISSIONS`); the batch is one content migration (071) plus tests, with
  no new module.
- **Row 262 is partly a manual topic.** Makers cover a post-crash
  inspection, replacing bent parts, and runout limits. No document gives
  photo standards, damage estimation, insurance claims, salvage rules or
  a frame measurement (N8, N9).
- **Row 263's named subjects are mostly the sanctioning body's**: safety
  wire (N10), race coolant (N11), tech inspection and race numbers (N12).
  The makers cover track set-up.
- **No California regulator text was held.**

That is the operator's stop condition. The options went to the operator
with the evidence. **The operator's answers, verbatim:**
- Row 262: "Post-crash + CA salvage law (Recommended)"
- Row 263: "Makers' track prep (Recommended)"
- Row 267: "Fetch official CA + federal text (Recommended)"
- Provenance: "In the text (Recommended)"

**Acquisition (S0-8).** 13 regulator documents were fetched by
`acquire.py`'s own Fetcher and `save()` into
`~/research/motodiag/acquired/Regulation/`, with sidecars. That is 12 in
the first run, EPA's alert refused with a 403, and one DMV page (revived
salvage) in a second run, with its referrer recorded. leginfo's
robots.txt disallows every agent, and the eCFR API is disallowed, so
neither is fetched. Two leginfo sections had been opened by hand with
`curl` before the robots rule was read; nothing from them is saved or
cited.

**Rule 2 ran on its primary route.** The sandbox was proven by planted
writes (repository, library, scratchpad refused; the clone accepted).
Three Subconscious GLM-5.3 calls, one per row:

| packet | pages | facts | quotes on their page | turns | tokens | time |
|---|---|---|---|---|---|---|
| crash (262) | 147 | 122 | 80 | 3 | 417,103 | 177 s |
| track (263) | 256 | 99 | 78 | 5 | 682,063 | 335 s |
| emissions (267) | 286 | 104 | 92 | 4 | 573,777 | 307 s |

**The crash call invented quotes.** All 10 of its KTM 2022 EXC TPI quotes
are on no page. One gives the KTM 950 Super Enduro R's handlebar sentence
(its OM p. 27) to the EXC TPI's p. 63. Nothing from the model is used
unchecked: facts are nominations, and Opus takes every figure from the
page.

**The F158 census on a live copy, before 071:** 79 hits in 47 rows, 0 in
any workflow row. The control, "Phase 999" planted on a copy, was found
exactly once.
