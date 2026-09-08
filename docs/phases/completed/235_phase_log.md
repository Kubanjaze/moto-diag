# Phase 235 — Phase Log

**Aprilia + MV Agusta electrical, fault codes and dealer tools**
Branch: `phase-235-aprilia-mv-electrical` | Date: 2026-09-08

## Step 0 — existing-code audit

- `compat_matrix.json`: 146 rows, nine makes, **zero** for either make here.
  Phases 231 and 232 each assert that zero with a counter-assertion that other
  makes have rows, so the number carried meaning rather than being incidental.
- `dtc_codes/`: seven files, neither make present. New ground for two makes.
- Phase 231 explicitly deferred `\bP0\d{3}\b` and `\bPADS\b` to this row,
  case-sensitively — after `PADS` had matched brake *pads* at 231.
- Phase 232 already ships the dash-invisible torque-monitor claim, so this
  phase must extend the scope rather than restate the fact.
- Roadmap row 235 named "Mercuri (MV)" — a string found nowhere else in either
  repo and in no source consulted. Corrected to Eldor rather than written from.

## Research

One capped 6-agent run (2 questions × 2 refuter lenses), the cadence held
since 227. **6/6 returned.** Three verdicts refuted, one clean.

Both questions carried the standing warnings: the phantom recall number from
231 and the sibling cross-contamination from 234.

## Verification I did myself

Two claims were load-bearing enough not to delegate.

1. **The never-displayed code count.** The finding said fourteen and listed
   fifteen; refuter A said 18; refuter B said 19. The Aprilia Service Station
   Manual was on disk, so it was flattened, de-hyphenated and counted: **19**,
   matching refuter B exactly. My own first pass returned 18 because the
   sentence wraps as "in- strument" — the precise trap refuter A had just
   described. Recorded as a module constant with the trap beside it.
2. **The Euro 4 entitlement.** Fetched Regulation (EU) 2018/295 and confirmed
   Appendix 1 points 3.12 and 3.13 verbatim, because it is the one claim in
   this phase a workshop would act on against a manufacturer.

## Build

| Surface | Change |
|---------|--------|
| `known_issues_aprilia_mv_electrical.json` | 8 entries (4 service-manual, 4 model-generated) |
| `dtc_codes/aprilia.json` | 7 rows, new make |
| `dtc_codes/mv_agusta.json` | 6 rows, new make |
| `adapters.json` | 28 → 34 |
| `compat_matrix.json` | 146 → 167; aprilia 0→15, mv-agusta 0→6 |
| `tests/test_phase235_*.py` | 50 tests |
| 231 / 232 guards | zero-assertions inverted, invariant not constant |
| Docs carrying the seed count | README, launch-checklist, quickstart, install |

## Failures caught during the build

- **My own test caught a content hole.** 231 deferred the `PADS` vocabulary
  here; my prose named neither PADS nor TEXA while the adapter catalogue named
  both. Entries now name them and carry the contrast that matters.
- **A year-range guard fired on a deliberate `incompatible` row.** The rule is
  that an unsourced range must not masquerade as coverage; a row asserting no
  coverage at any age is not that. Scoped the test to its intent rather than
  loosening the assertion.
- **Regression tooling, not content:** `.venv/bin/pytest` does not put the
  repo root on `sys.path`, so `test_phase125_quick.py`'s `from tests.…` import
  fails to collect. `python -m pytest` is the correct invocation.
- **My Step 0 audit was too narrow, and the regression caught it.** I grepped
  for the *exact* test name used in Phase 231 and concluded that only 231 and
  232 held the zero-guard. Phases 233 and 234 held the same guard under a
  different name — `test_mv_still_has_no_adapter_rows` — so two inversions
  were missed and failed in the full run. A third failure came from the same
  shallow reading: Phase 233 asserts that no file outside the MV model files
  names an MV designation, and this phase legitimately names them. Re-done as
  a semantic search rather than a name match, then confirmed by running every
  test file that touches the corpus: **95 files, 1354 passed**. The lesson is
  that an audit keyed on one identifier finds one phase's habits, not the
  invariant — the same shape as the constant-for-invariant bug, one level up.
- The Phase 233 boundary was **scoped, not loosened**: 235 is exempted because
  it owns a different axis (codes and tooling across both makes, which cannot
  be written without naming models), and the boundary is enforced from 235's
  side instead, where model-specific failure content is forbidden.

## Close-out

- 847 → 855 known issues.
- Regression: 5734 passed / 0 failed. F9 lint clean.
- Cleared for: roadmap ✅, implementation.md row + version bump, merge to
  master, delete branch.
- **Deferred, with reasons:** a `regulation` provenance value (needs its own
  phase — extending migration 051's CHECK touches the Gate 2 test and two API
  modules); MV three- vs four-cylinder tool parity (unconfirmed by any source,
  recorded in the catalogue rather than guessed); MV P1xxx meanings (no primary
  document obtainable, so no rows shipped).
- **Still open from 223:** the KTM 390/790/890 Adventure line has no roadmap row.
