# Phase 258 — Gate 14: the scooter / small-displacement track through the real front doors

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-24

---

## Goal

Row 258: "Gate 14 — Scooter / small displacement integration test. Query
scooter/small bike → CVT + electrical + carb workflow." Track M's closing
gate, in the house style Gates 8, 9, 11, 12 and 13 set: every query goes
through the **real** CLI root or the HTTP API, never the repository layer;
a class of executable documentation records what the corpus honestly lacks
and is meant to fail the day someone fills it; and a gate guards the gates
before it.

Track M built its three layers one phase at a time — CVT (254), electrical
(354), carburettor (353) — over the substrate the track's middle phases
laid: the transmission axis (255), the retrieval chokepoint (256), the
canonical junction (255C) and the per-vehicle transmission field (257B).
The gate's first duty is to walk the row's path and report what a
technician actually gets. Step 0 walked it (`258_step0.md`): **the path
carries the track's content for the machines all three layers cover** —
and it carries two measured exceptions worth the gate's name: the three
SYM overlap machines reach their CVT content only as another model's rows
(tier 2), and the Fiddle 50 — which 354's own tests name as a tier-0
machine — resolves transmission `unknown` and has the scoped CVT layer
withheld entirely.

This phase runs as the operator's Subconscious/GLM builder session inside
a sandbox (the standing rule 2 arrangement): everything through the front
doors as always, but no push, no merge, no deploy and no regression of
record — those are the Opus session's, outside.

## Decisions

**D1. The gate reports; it does not repair.** Zero production code, as in
Gates 9, 11, 12 and 13. Every gap Step 0 measured is either another
phase's content (the CVT rows' SYM spellings — 254's rows, their identity
is (make, model, title) per F129), a lookup entry (the Fiddle 50 spelling),
a tokenisation behaviour (relevance plurals), or a corpus-history debt
F149/F151 already record. Each ships as a finding and an executable
pin meant to fail the day someone fixes it — the pattern Gate 13 set with
row 250B. No fork to take to the operator: nothing here asks for a
threshold change or a rule change.

**D2. Absences are asserted, not assumed.** Every honest-gap test states
the measured absence in its docstring and is written so it fails the day
the absence is filled.

**D3. The prompt is a front door.** The diagnostic path is walked through
the real `diagnose quick` with the AI call replaced (Gate 13's D3),
asserting on what the command handed the model. The API half uses a real
key minted in-process and revoked by id.

**D4. Track M's invariants are re-run here, not restated.** The gate
asserts, against the live seed: the six-value provenance vocabulary with
353/354's rows carrying `service-manual`/`regulation`; 11 of 13 CVT rows
transmission-scoped and the two unscoped ones named; tier-0 pair integrity
for every gate machine (no F142 pair among them); the 1,060-row documented
count; and the axis withholding scoped CVT rows from a manual small bike
while its own Grom rows arrive.

**D5. The findings get numbers, and the gate does not fix them.** Filed
in `docs/FOLLOWUPS.md` per the finding skill: F153 (SYM CVT spellings),
F154 (Fiddle 50 lookup spelling), F155 (relevance plurals / tier-0
displacement), F156 (Metropolitan↔CHF50 name bridge), F157 (no adapter
row for any scooter make). The year-window, DTC-file and F149/F151 gaps
are pinned as tests citing the findings and records that already exist.

**D6. Sandbox finish line.** Step 0, v1.0, the build, its tests, the four
whole-tree checks and the close-out documents all commit on `phase-258`.
The regression of record, the refute pass, the merge, the deploy and the
live backup/load are **pending for the Opus session**, and are marked so
in the phase log. `closeout_check` A5 stays red until then, by design.

## Scope

One new test file, `tests/test_phase258_gate14.py`, with a module-scoped
fixture that stands up a fully seeded database the way `db init` does
(Gate 13's fixture pattern: DTCs → every `known_issues_*.json` in sorted
order → both junction rebuilds → the adapter catalogue). Classes:

1. **TestEveryScooterMakeAnswersThroughTheCli** — `kb list --make` for
   Kymco, SYM, Piaggio, Vespa, Genuine (plus Honda, Yamaha, which hold
   scooter content beside big-bike content); the provenance label shows
   beside every row; the make filter does not cross into another make.
2. **TestTheThreeLayersReachTheCommandsPeopleUse** — the layer terms
   Step 0 measured (`variator`, `weight roller`, `clutch bell`,
   `driven pulley`, `primary sheave`, `drive belt width`,
   `stator resistance`, `regulator rectifier`, `pilot screw`,
   `auto by-starter`) each return their row with its label, through the
   CLI and through `GET /v1/kb/search`.
3. **TestTheDiagnosticPath** — the five machines that cover all three
   layers (CHF50, Agility 50, People S 250, Fly 50, LX 50) walked through
   real `diagnose quick`; the prompt census pinned per machine; the
   symptom-dependence pinned both ways (S0-4's displacement, S0-5's
   rescue); the cap still 12.
4. **TestTheSymException** — S0-2's answer, pinned: SYM Jet Euro 50,
   Joyride 125, Fiddle 50 hold exactly 2 tier-0 pairs (electrical +
   carb); the CVT rows reach them at tier 2 and still reach the prompt;
   the Fiddle 50's `unknown` resolution withholds the 8 scoped rows.
   Each test names F153/F154 and is meant to fail when they close.
5. **TestTheGapsTheHandoffPredicted** — an injected scooter (PCX150,
   Zuma 125) receives no carb row at any tier and its electrical row at
   tier 0 (Zuma 125's row reaching the prompt only under a charging
   symptom); a carburetted Ruckus has no scooter-electrical row of its
   own and F149's three unverified rows are its only charging content;
   the carb row inside the window (2015) and not outside it (2008); a
   Grom withholds the 8 scoped CVT rows and reaches its own 8 tier-0
   rows; a CBR1000RR reaches none of the three layers at tier 0/1.
6. **TestCrossSurfaceAgreement** — `kb search` against
   `GET /v1/kb/search`, `kb list --make` against `GET /v1/kb/issues`;
   the F151 zero-reach for the five scooter makes on both surfaces.
7. **TestTheHonestGaps** — no adapter row for any scooter make (F157);
   no `dtc_codes` file for any Track M make; no scooter row carries a
   DTC code; F151's cross-platform rows unreachable for the five scooter
   makes; the 2005 Metropolitan reaching no CHF50 row (F156); the two
   unscoped CVT rows reaching manual bikes at tier 2 by design.
8. **TestTrackMCorpusInvariants** — D4's list, plus (make, model, title)
   uniqueness and the 1,060-row count.
9. **TestRegression** — Gate 13 re-run as a subprocess (it transitively
   re-runs Gates 8, 9, 11 and 12 — the deviation Gate 13 itself
   recorded); `SCHEMA_VERSION` pinned at 66.

## Non-goals

- **No production code.** No migration for the SYM spellings (F153), no
  lookup entry for the Fiddle 50 (F154), no stemming in
  `relevance_tokens` (F155), no junction bridge for the Metropolitan
  (F156), no compat rows (F157), no DTC seeding, no retrieval change.
- **No new corpus content.** The gate writes no `known_issues` row and
  corrects none.
- **No network, no LLM key, no live database.** The fixture builds its
  own from the packaged seed; the snapshot `data/motodiag.db` is used
  read-only for the count agreement.
- **No merge, no push, no deploy, no regression of record** — the Opus
  session's half of the standing arrangement.

## Claims for the Opus refute pass

The gate states no new facts from source documents; every assertion is a
measurement of this repo's own seed and code. The corpus rows it walks do
carry document claims, made by their own phases and refuted there; where
a test's docstring repeats one (e.g. the Ruckus carb row's 2012–2025
window, 353's; the CHF50 rows' modelling, 354's), the claim is 353/354's
to defend and their phase docs hold the citations. The refute pass should
check: (a) each pinned "today's truth" matches the seed, (b) each
honest-gap test would actually fail if the gap were filled (the mutation
list below), and (c) the S0 measurements reproduce on a fresh seed.

## Results (v1.1)

**Shipped:** `tests/test_phase258_gate14.py` — 125 tests in nine classes,
and **no production code**, as D1 said. No seed row was written or
corrected; no schema, no migration. The fixture builds its own database
from the packaged seed the way `db init` does and seeds the adapter
catalogue; nothing touches the live database, the network or an LLM key.

- 125 tests, of which 1 re-runs Gate 13 as a subprocess (which transitively
  re-runs Gates 8, 9, 11 and 12 — the deviation Gate 13 itself recorded).
- **11/11 mutations caught** (the list under Verification).
- The four whole-tree checks green before the close-out commit:
  191C F9 lint + 244G + roadmap continuity **58 passed**; `finding_check`
  exit 0, both variants (completed/ and in_progress/).
- `COLLECTED_TEST_FLOOR` raised 9188 → **9321** (collected count with the
  gate file present), raised before the regression of record per the
  floor's own rule.
- **The regression of record did not run** — the standing arrangement for
  this session; it is pending for the Opus session, and `closeout_check`
  A5 stays red until it lands. Every other close-out assertion passes.

### What the gate confirmed

Every Step 0 measurement reproduced on a **freshly seeded** database,
which is the stronger claim: the fresh seed loads to exactly 1,060 rows,
the count the live snapshot and the 353 handoff both carry.

The row's path carries the track's content. The five full-coverage
machines (CHF50, Agility 50, People S 250, Fly 50, LX 50) reach CVT,
electrical and carburettor rows in one 12-row prompt; the composition
250B built answers the symptom (a charging complaint rescues the Zuma
125's crowded-out tier-0 electrical row; a belt complaint reaches the
belt rows on every machine); the transmission axis withholds all scoped
CVT rows from a manual Grom while its own eight tier-0 rows arrive; a
CBR1000RR reaches none of the three layers at tier 0 or 1; the chokepoint
records the Fiddle 50's cost in `retrieval_withheld` (≥ 8 rows). The
12-row prompt census is pinned per machine, so the next retrieval change
names itself.

### What the gate found that Step 0 had not — and what it corrected in Step 0

- **The adapter bullet in Step 0's S0-9 was measured against an unseeded
  catalogue** (the Step 0 harness never ran `seed_all`), so its "No
  compat entries known" answer for the Ruckus and CHF50 was the answer of
  an empty store. Re-measured on a seeded catalogue: a Honda scooter
  inherits the make-level **"Mock Adapter (dev/test only)"** — no real
  adapter is named for any scooter, which is F157's corrected statement.
  Step 0's doc and the finding both restated.
- **"No scooter row carries a DTC code" was false as written**: 252's
  GROM125 code-table row carries eleven Honda blink codes in Honda's own
  pair format (7-1 … 54-2), reachable through `kb by-code 9-1` — the
  positive control the negative claim lacked. The true negative, now
  pinned: no Track M row carries an SAE OBD code, so `kb by-code P0300`
  reaches no scooter row.
- **Genuine is the Damon shape on Track M**: a make with no electrical
  or carburettor row of its own, covered only by 253's rows and the
  multi-make CVT rows. Recorded as the honest gap it is.

These were the build's own bugs (the register is in the phase log), and
their shared cause is the F9 family again: Step 0 wrote universals and
negatives from ad-hoc queries — a `!= ''` filter that passes `'[]'`, a
DB built without the catalogue, titles recalled rather than copied — and
the first `pytest` run was the control those claims never had.

### Findings filed

| F | What | Where it goes |
|---|---|---|
| F153 | The CVT rows pair SYM under spellings the other layers do not use; no SYM scooter reaches a CVT row at tier 0 | Follow-up (migration) |
| F154 | `fiddle 50` is missing from `TRANSMISSION_LOOKUP`; the machine 354's own tests name at tier 0 resolves unknown and loses the scoped CVT layer | Follow-up (one line + evidence) |
| F155 | `relevance_tokens` does not stem plurals, and symptom relevance displaced a tier-0 carburettor row for tier-2 rows sharing one word | Follow-up |
| F156 | A 2002–2006 Metropolitan is a CHF50 that reaches no CHF50 row under its own name — and reaches the CVT recall rows at tier 0 | Follow-up (content decision with a year dimension) |
| F157 | No adapter compatibility row exists for any scooter make; a Honda scooter's only answer is the make-level dev/test mock | Follow-up (sourcing question) |

F149, F151 and F132 are cited where the gate measured their reach, not
re-filed; their entries record what 258 added — F149's three rows are
the Ruckus's only charging content at tier 1 (pinned), and the F151
rows reach none of the five scooter makes on either surface (pinned).

### Deviations

- **The regression of record, the refute pass, the merge, the deploy and
  the live backup/load did not run** — the operator's standing
  arrangement for this Subconscious session: everything to "ready to
  merge" commits on `phase-258` in this clone; the rest is the Opus
  session's and is marked pending in the phase log. A5 is expected red
  until the regression line lands.
- **Gates 8, 9, 11 and 12 are not re-run directly** — Gate 13 is, and it
  re-runs them, so they are guarded transitively (Gate 13's own recorded
  deviation for 5, 6 and 7).
- **The sandbox refused heredocs and `/tmp`** (Operation not permitted),
  so commit messages went through `-F` files in the session tmp — the
  message-file form of the working rule and the same form the 353
  handoff records for merges. Noted in the phase log, not worked around.
- **The root `implementation.md` header names Phase 258** while the
  regression line is pending; the A7 rule names the newest phase, and
  258 is the newest close.

### Verification

- The 16 machines walked through the real `diagnose quick` with the AI
  call replaced, never through the retrieval helper; the API half used a
  key minted in-process and revoked by id when the module finished.
- The four whole-tree checks green on the close-out tree:
  `test_phase191c_f9_lint.py` + `test_phase244G_guard_shapes.py` +
  `test_roadmap_continuity.py` (58 passed) and `finding_check.py` exit 0,
  including the in_progress/ variant.
- Mutations, all caught: an SYM pair added to a CVT row (tier-0 counts
  and the SYM tier labels); `fiddle 50` added to the lookup (the Fiddle's
  four pins); a compat row for Kymco; a `kymco.json` DTC file; F149's
  reg/rec row scoped to Shadow; Kymco added to a cross-platform carburettor
  row's make; the Ruckus carburettor window opened to 2008; Metropolitan
  added to the CHF50 carburettor row's models; plural stemming in
  `relevance_tokens` (the LX 50 displacement); the transmission scope
  removed from the roller-wear row (the Grom and the census); the prompt
  cap raised 12 → 16. **11/11.**
- Full gate file: **125 passed** (215 s; the Gate 13 subprocess is 3:30 of
  it). Regression of record: **pending, Opus.**

## Verification Checklist (v1.1)

- [x] The new test file scanned by 244G's raw-source guard before the regression
- [x] Every honest-gap test fails when its absence is filled — 11/11 mutations
- [x] Mutations caught — 11/11
- [x] The four whole-tree checks green
- [x] Roadmap row 258 updated; findings F153–F157 filed
- [x] `implementation.md` history row and `phase_log.md` entry
- [ ] Regression of record, refute, merge, deploy — pending, Opus
