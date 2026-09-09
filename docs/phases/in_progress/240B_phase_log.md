# Phase 240B — Closing the Track K audit debt — phase log

**Status:** Planned
**Opened:** 2026-09-09

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
