# Phase 240B — Closing the Track K audit debt — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-09 | **Closed:** 2026-09-09
**Repo:** https://github.com/Kubanjaze/moto-diag
**Merged:** `fab19ac` on `master`, pushed `ea872ff..3cae3fb`

---

## 2026-09-09 — Plan v1.0 written

Track K closed at Phase 240 with Gate 12, but the closure audit left debt the
gate did not cover. `TRACK_K_AUDIT_DEBT.md` records it and warns, in its own
words, that section A is "the confirmed subset, not the full set": the
contradictions auditor found 16 cross-file contradictions, the workflow capped
each dimension at `findings.slice(0, 8)`, and **eight were never verified**.

**Step 0 — existing-code audit.** Read `TRACK_K_AUDIT_DEBT.md` and all 2858
lines of `TRACK_K_AUDIT_VERIFIER_NOTES.md`, including the 17 rejected verdicts.
Then re-verified the load-bearing claims against the tree rather than trusting
the notes:

- Corpus totals reproduce exactly — 917 entries, `model-generated` 131,
  `service-manual` 108, `forum` 17, `regulation` 1, legacy-null 660.
- Exactly two untipped `forum` entries corpus-wide. **The debt document's
  index is off by one**: it names `known_issues_triumph_bonneville.json[11]`;
  the entry is at index **10** (the file holds 11 entries, 0-based).
- All three claimed-vacuous guards reproduce. The Phase 237 mileage guard is
  worse than reported — the file contains no km/mile token of any kind, so the
  loop body has never executed. Uncomma'd figures (`12000 km` in the MV triple
  file, `18000 miles` in the Triumph Tiger file) exist elsewhere and would slip
  past the current pattern.
- **Mutation-tested the six dead discriminators**: replacing `_asserts` with
  `return False` in all seven files leaves 180 of 181 tests passing. Only
  `test_phase221_ktm_1290.py` fails, and it earns that from a real-data positive
  assertion (`assert bosch`), not a synthetic probe. Reverted clean.
- Aprilia and MV Agusta shadow **zero** generic DTC codes, so B4's
  "shadow-earning claim is unverified there" has nothing to verify.

**Three debt-document items do not survive verification** and are recorded as
no-change so nobody re-litigates them: B2 (the MV F4 shim relabel to
`unverified`), B4 as framed, and two of section C's three provenance claims
(parts-fiche and KTM electrical). Only the tooling file's split is real.

**One conflict adjudicated.** The two B1 verifiers contradict each other. The
MV-sprag verifier rejected the finding because
`test_phase233_mv_agusta_triple.py` asserts `"Forum tip" not in fix_procedure`
for every entry. But that assertion *is* the mis-scoped denylist Phase 226
identified inside Gate 2 and then reproduced locally — a guard that enforces the
violation is not evidence the violation is permitted. Resolved in favour of the
Bonneville verifier and the Family 1 finding: fix both entries, re-scope both
guards.

**Baseline regression confirmed before any edit: 5954 passed, 0 failed
(10m54s).**

**Two scope-boundary flags raised rather than silently absorbed.** Section A
omits a confirmed contradiction (Aprilia V4 charging, `european_differentials[5]`)
— it substituted the MV swingarm item for it. Section C omits a confirmed
provenance finding (`known_issues_triumph_vintage.json` labels all 13 entries
`service-manual` while two rest on a marque club and a retailer). Demoting those
two collides with the B1 biconditional, because fabricating a forum tip is
exactly what Phase 226 warns against.

Plan v1.0 written to `docs/phases/in_progress/240B_implementation.md`.

---

## 2026-09-09 — Build complete

**Part 1 — the contradictions dimension, re-run uncapped.** The original audit
script was never in the repo (it lived in the workflow journal), so the
dimension was re-run as a fresh adversarial sweep partitioned six ways, each
slice required to produce verbatim quotes from both sides, a same-subject
argument, an operative cost, a reachability trace through the real retrieval
predicate, and a recorded kill attempt.

**Result: 27 contradictions and 13 uncertain findings**, against the original
run's 6 confirmed. The `slice(0, 8)` cap had not trimmed a tail — it hid the
majority of the dimension. Written up in
`docs/phases/completed/TRACK_K_AUDIT_DEBT_2.md`, with each finding marked
[VERIFIED] or [REPORTED] so the mistake that produced this debt — reporting 16
and verifying 8 — is not repeated silently.

**Five structural defects surfaced that no content audit would have found.**
These are the mechanism behind the whole contradiction pattern:

- **S1** `issues_repo.py` orders `severity DESC` on a TEXT column, so SQLite
  returns `medium, low, high, critical` — `critical` comes back **last** on all
  three retrieval paths. Three other modules in the same repo map severity to a
  rank correctly; this one is the outlier. 73 test files assert on `results[0]`,
  so fixing it needs its own phase. Found independently by five of six slices.
- **S2** Three entries carry a `make` of "All European makes" / "All makes",
  which `make LIKE '%X%'` can never match. One of them is
  `european_intervals[4]` — the target of contradiction A5.
- **S3** `european_tooling[2]` holds a KTM *and* a Triumph correction under
  `make: 'KTM'`; the Triumph half is unreachable from any Triumph query and was
  back-propagated nowhere.
- **S4** That same entry runs to `year_end` 2026 while every corroborating row
  stops at 2020, making it the sole TuneECU answer for MY2021+ — and it implies
  the tool works on machines it does not support.
- **S5** Two machine-readable service intervals are wrong: a blanket 7,500-mile
  "Desmodromic valve service" for *every* Ducati including the two spring-valve
  engines, and a KTM 690 valve check stored as 15,000 **miles** where the corpus
  states kilometres. `scheduler.next_due` reads `every_miles` and never `notes`,
  so both caveats are unreachable by the code that schedules the work.

All five are recorded and scheduled, not fixed. Fixing S1 reorders every
knowledge query in the product.

**Part 2 — the six section A contradictions**, each following its verifier's
`corrected_fix` rather than the auditor's recommendation, which was wrong or
tree-breaking in five of six. No entry was added, removed or split, so the
corpus stayed at 917 and every pinned count and the Phase 208 doc-count guard
stayed green. A5 was fixed at two sites rather than one because S2 makes the
first site unreachable from a KTM lookup.

**Part 3 — guards and gates.** B1: the two untipped `forum` entries got a
trailing tip (position 0.78 and 0.73, matching the house range, so
`predictor._extract_preventive_action` returns a self-contained action rather
than a truncated procedure), and the whole family of ten negative-only guards
was converted to the biconditional — 3 → 13 members asserting both halves. B3:
all eight constant cumulative pins now derive their totals from the same JSON
the test loads, and the make-filtered count is counted rather than assumed
equal to the file total, which it is not (`make LIKE '%X%'` is a substring
match and the Aprilia block already breaks it). B4: Aprilia and MV shadow zero
generic codes, so the zero is pinned as a tripwire with an actionable message,
plus the make-row reachability positive and a pin on `dtc_repo`'s
`candidates[0]` fall-through. B5: the three dead guards and all six dead
discriminators de-vacuumed.

**Nine mutation scenarios, all caught.** Every new or repaired guard was
mutation-tested: reintroduce the defect, confirm the guard fails, revert. The
headline is the discriminator family — before, stubbing `_asserts` to
`return False` left 180 of 181 tests passing; after, **all seven files fail**.

**Three items closed as no-change after verification**, with the reasoning
recorded so nobody re-litigates them: B2, B4 as framed, and two of section C's
three claims.

**Two things the debt document got wrong**, both corrected in place: the
Bonneville forum entry is at index **10**, not 11; and ROADMAP row 233's "not
while being tightened" clause is itself the over-correction Phase 240B fixed.

**Regression: **5991 passed / 0 failed** (baseline 5954; +37 tests)** (baseline 5954/0).

---

## 2026-09-09 — Close-out

Merged `fab19ac`, pushed `ea872ff..3cae3fb`. Then a completion-gate pass
against CLAUDE.md found five things still open, all now done:

1. **This log still said `Status: Planned`.** Corrected, with close date, repo
   URL and the merge/push refs.
2. **The implementation doc's Risks section had no resolution notes**, which
   the gate requires. Added as a table — including that two risks did
   materialise (the forum-tip test turning red, and scope pressure) and how
   each was handled.
3. **`TRACK_K_AUDIT_DEBT.md` still described everything in it as open**, so the
   next reader would have re-litigated the three items verification rejected.
   It now opens with a closure box naming exactly what was fixed, what was
   closed as no-change and why, and the two confirmed findings it omits from
   its own sections.
4. **`TRACK_K_SUMMARY.md` carried a stale claim** — "pushes are
   classifier-blocked from this environment; `master` is ahead of
   `origin/master` by every Track K commit since 235". That is no longer true
   and would have misled the next session into thinking the remote was behind.
   Corrected, and the 240B outcome recorded alongside it.
5. **A gate-number collision two tracks ahead.** Row 250 was written as
   "Gate 12", which Phase 240 already holds — so every gate row from 250 to
   352 was off by one. This is the *same* error Phase 240 hit and corrected
   mid-phase, when row 240 was written as "Gate 11" that Phase 205 already
   held. Renumbered 250→13 … 352→21, with the correction recorded on row 250,
   so Phase 250 does not have to discover it the hard way. Gates 10 and 11 are
   Phases 204 and 205; 12 is Phase 240.

Also added a **Track K open-debt block to `docs/ROADMAP.md`**, immediately
before Track L, so S1–S5 and the 27 unfixed contradictions are visible from the
roadmap rather than only from a completed-phase document.

Phase 240B is closed. `docs/phases/in_progress/` is empty.
