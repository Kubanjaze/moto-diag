# Phase 234 — MV Agusta 4-cylinder

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Cover the F4 and the four-cylinder Brutales, and replace the "exotic,
dealer-only" impression with specifics.

Guard: `pytest tests/test_phase234_mv_agusta_four.py`.
Outputs: `known_issues_mv_agusta_four.json`, its test, roadmap row 234,
count 842 → 847.

## Existing-code audit (Step 0)

**1. Written from the paired run with Phase 233** — no research launched
here. `radial valve` returned **zero files** corpus-wide before this
phase, so the ground is genuinely uncovered.

**2. The row's framing needed replacing, not repeating.** Row 234 says
"exotic pricing, limited dealer network", which is an impression rather
than a fact a shop can act on. The research was asked for specifics and
produced them: the workshop manual exists and names its tools, so
mechanical work is documented; what constrains an independent is parts,
tooling and campaign status.

**3. The sibling boundary is the live hazard.** 233 and 234 share a make,
and the research itself cross-contaminated — see Results.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 842 → 847 |
| Entries | 5, all `service-manual` |
| Research runs launched by this phase | 0 (paired with 233) |
| Cross-contamination caught by refutation | 1 |
| Figures deliberately omitted | 2 (shim diameter, an impossible capacity) |
| Phase tests | 31 |
| Backend regression | 5684 passed / 0 failed |

**A refuter caught the research contaminating this phase from its
sibling.** The swing-arm screw campaign was attached to the F4; the
regulator scopes it to three-cylinder models only, and a query for the F4
returns nothing at all. The finding had carried its own warning against
cross-contaminating from the triples, and then did it. The campaign sits
in Phase 233's file, where it belongs, and tests on **both** sides assert
the boundary — this file must not contain it, and the triple file must.

**The shim diameter is deliberately absent, and that absence is the
entry.** Sources disagreed and none was authoritative. Rather than pick
one, the file tells a shop to measure an existing shim before ordering —
because the default behaviour is to reach for the Japanese kit already on
the shelf, and the mismatch is otherwise discovered with the camshafts
out. An entry that says "measure first" is worth more here than a
confident number that might be wrong.

**"Radial valve" is demystified rather than repeated.** The name is why
shops decline the work; it describes valve *placement*, and the cam lobes
are ground at a compensating angle to act on conventional bucket tappets.
The manufacturer's manual describes an ordinary shim-under-bucket job. A
claim circulating online that these are shim-over-bucket contradicts that
manual, and the file names the claim in order to correct it.

**Key finding: replacing an impression with specifics is a deliverable.**
"Exotic, dealer-only" told a shop nothing. What is doable, what tooling
has no substitute, and what sets the timescale — that is an answer.
