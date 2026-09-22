# Phase 255B — Twist-and-go vs manual small bikes — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-21
**Closed:** 2026-09-22

---

## 2026-09-21 — Step 0 (draft, `b157da2`)

The subject is empty and its vocabulary is not: `twist-and-go` returns 0
rows across 1,045, while the nouns it would use are well populated and
almost none is scoped — 48 manual-side rows already unscoped and already
reaching scooters. The PCX question Phase 256 left open is measured and
**reframed**: it is not a reserved-slot question. Eight of the 254 rows do
name the machine, but the junction stores `Honda PCX150` while the tier
query compares the resolved `PCX 150`. 469 of 2,424 junction rows carry a
marque prefix. Two further corpora are found with no applicability field at
all.

## 2026-09-21 — Plan v1.0 (`5568b30`)

Five decisions taken. One premise in the brief corrected by the operator and
load-bearing: dropping `Filly LX 50` from 4609 does **not** restore the
Filly's prediction — it withdraws an over-claim. The Filly resolves
`unknown`, so a `{cvt}` row is withheld before and after. Verified before
writing the plan.

## 2026-09-21 — The evidence library moved (`61ef363`, mobile `f2963a9`)

263 source documents were sitting in `/private/tmp/claude-501/<session>/`,
which is not durable — the session id in this phase's own handoff was
already dead. Moved to `~/research/motodiag/` and verified byte-identical by
md5 across all 9,624 files before the source was removed. Same class of
mistake the deploy rule already forbids for backups, made with irreplaceable
evidence.

## 2026-09-21 — Four data commits (`f0a4732`, `351d73f`, `15d7b4b`, `933ef71`)

4609 withdraws the Filly claim. 4615 splits. 4611 splits. 4605 gains
Harley-Davidson, BMW and LiveWire, closing **F115** — proved end to end
through the chokepoint, with a Kawasaki Ninja 400 as the negative control.

**F129 found and measured rather than argued:** `known_issues` has a UNIQUE
index on `(make, model, title)` and `add_known_issue` upserts `ON CONFLICT
DO NOTHING`, so a seed edit to any of those three columns inserts a second
row instead of updating the first. Re-seeding after the 4609 edit took a
12-row corpus to 13, the over-claiming row still present.

**A rollback bug, found by running the round trip rather than reasoning
about it.** `rollback_sql` is pure SQL with no `post_apply` hook, so
restoring the columns did not rebuild the derived junctions: 2,424 → 2,422.
**And the first test for it passed with the fix removed — twice** — because
its baseline came from a rollback, and then from a reconstruction that still
did not restore one column. Rebuilt on an independently reconstructed
pre-phase seed.

## 2026-09-22 — The library was deduplicated (`3372b27`, mobile `11d26aa`)

**Counting paths as documents inflated every "N manuals say X" claim.** 263
`.pdf` files, **172 distinct documents**. The Buddy Kick manual existed
under five paths. Two claims were already wrong: a manual cited as *"two
editions"* was three paths holding one byte-identical file, and a SYM count
treated two paths as two machines. 75 copies removed, 533.8 MB.

**One more census instance for the list:** this phase wrote *"247 readable
PDFs"* into `ROADMAP_AUTHORITY.md` — a **file** count quoted as a
**document** count. Wrong by 75.

## 2026-09-22 — Seven content subjects, seven deaths

Two adversarial refuter cycles, every citation opened at page level. Nothing
shipped. Each subject and the document that killed it is in v1.1's
Deviations. The pattern across all seven: **the rows were written from
category reasoning before the library was read**, and the makers' own
manuals contradicted the premise each time.

The conclusion the phase reached about its own subject: **the
twist-and-go/manual distinction is already carried by the transmission axis
and the filter.** Every row that tried to state it in prose was false, or
true of one maker only, or true of one document only. No successor content
phase scheduled.

## 2026-09-22 — The 4611 split was backed out (`07dc1ac`)

**The lesson that generalises: a split separates a claim from its
counter-evidence.** The general half asserted that a kickstart and an
electric starter do not share interlocks, so a working kickstart indicts the
brake-lever switch. Genuine's Buddy 50 owner's manual supports it. Kymco's
Agility 50/125 and Super 8 50X owner's manuals contradict it — *"While
squeezing the rear brake lever, kick down on the kick start lever"* — so on
a Kymco the brake lever **is** required and the comparison proves nothing.

**That quote was already in 4611 and stayed in the half I did not move.**
Each half read coherently alone. Two refuter cycles over other rows missed
it; a completeness critic reading neighbouring rows found it two commits and
one push after it shipped. The debt is recorded **CLOSED AS WRONG**, not
carried forward: a maker-specific claim cannot live in a
transmission-scoped row.

**The same error in miniature, one commit later (`eb2163e`).** Repairing it,
I narrowed the model column by searching each machine's own manual for
kickstart vocabulary — and **kept Piaggio Fly on a single hit in a
boilerplate fault table**, while the Fly 125's own specification reads
*"Start-up Electric"*, one occurrence of `kick` in 223 pages. A hit in a
fault table, a contents list or an index is not evidence a machine has the
part. The fix repeated the error it was fixing.

## 2026-09-22 — F132 (`7ee5646`)

Eleven unevidenced year windows and thirteen repair estimates nulled,
shipped on a measured table rather than an argument. The prediction that
non-CVT machines would see zero change **did not hold**.

## 2026-09-22 — The regression went red twice

**134 failures at `c56dceb`.** `_insert_255B_new_rows` lost its anchor
guard: `init_db` runs migrations, so without it migration 065 fires on an
empty database and seeds rows before the loader writes anything. Every
failure was a `test_loads` in another phase's file, counting rows after
loading one seed file.

**The guard was deleted by one of my own `re.sub` edits**, whose non-greedy
`.*?\n\)` matched past the tuple it was regenerating — **and a separate
index-surgery edit removed both tests that pinned it.** A protection and its
tests deleted in the same stroke leave nothing to notice, and nothing did.

**And the F132 table had been measured on that broken database**, so it was
wrong: 123 entering and +1 for non-CVT machines, where the true figures are
**143 and +2**. Corrected in all three places it appeared. A measurement
taken on a broken fixture reads exactly like a correct one.

**4 further failures at `3289cfa`** — the Phase 208 invariant catching four
documents still claiming 1,045 known issues after the corpus reached 1,046.
The invariant working as designed.

## 2026-09-22 — Close-out

Regression **7,997 passed / 0 failed / 0 skipped / 29:47** at `1fbcdaa`.
Merged `3a5fbdb`. Deployed: schema 64 → 65, 1,045 → 1,046 rows, backup
md5-verified, dry run on a copy first. Post-deploy smoke: a Road King and an
R1200GS receive the drive-belt vocabulary row; a Ninja 400 does not.

**Process fixes adopted as enforcement rather than memory**, operator's
decision 2026-09-22: no `re.sub` / `sed` / index surgery on source or test
files, and a pinned floor on the number of tests the suite collects, so a
commit that deletes tests fails.
