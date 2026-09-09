# Phase 240 — Gate 12: European brand coverage integration test

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Close Track K with a gate that asks, through the real front doors, whether
any European bike gets DTCs, known issues, adapters and parts — and that
records honestly where it does not.

Guard: `pytest tests/test_phase240_gate12.py`.
Outputs: the gate, roadmap row 240 corrected to Gate 12, implementation.md.

## Existing-code audit (Step 0)

**1. The row is mis-numbered.** Row 240 reads "Gate 11". Phase 205 closed as
Gate 11 — desktop + mobile end-to-end, Track J's opener — before this row was
reached. This is Gate 12. The same class of correction as "Mercuri (MV)" at
235: the row is mine and it was wrong.

**2. No existing gate sweeps the European makes.** Twelve gate files, none
naming Aprilia, MV Agusta, KTM or Triumph. New ground.

**3. The coverage matrix is uneven, and the gate must say so.** Six makes
have a DTC file, compat rows and a make-file. **Moto Guzzi has none of the
three** — no Track K row names it, and its seven issues and nine parts rows
all come from the cross-make phases 236–239. Gate 12 records that as
executable documentation, in the Gate 11 pattern: tests that pass today and
are meant to fail the day the gap is filled.

**4. House style is settled.** Gates 5/6/7/11: every query through the real
CLI root or the HTTP API, never the repo layer; cross-surface agreement
between the two front doors; a class for what the system honestly cannot
do; and a regression class that re-runs every earlier gate and pins the
schema version.

## Method

No research: a gate is built from the tree, not from sources. The four
query surfaces are `kb search`, `/kb/dtc/{code}?make=`, `hardware compat
check --make`, and `/shop/{id}/parts/search`, on one database seeded the way
`db init` seeds it.

## Results

| Metric | Value |
|--------|-------|
| Gate | 12 — row corrected from "Gate 11", which Phase 205 had already closed |
| Makes swept | 7 — six through DTC, issues, adapters and parts; Moto Guzzi through issues and parts only |
| Query surfaces | `kb search` (CLI), `/v1/kb/dtc/{code}?make=` (API), `hardware compat recommend --json` (CLI), `/v1/shop/{id}/parts/search` (API) |
| Executable documentation of gaps | 5 tests that pass today and fail when the gap is filled |
| Earlier gates re-run | 6 (Gates 5, 6, 7, 8, 9, 11) |
| Gate tests |  |
| Backend regression | 5945 passed / 0 failed |

**The row was mis-numbered, and the correction is a Step 0 finding.** Row 240
was written as "Gate 11" before Phase 205 reached and closed that number as
the desktop-plus-mobile end-to-end gate. Track K's closing gate is therefore
Gate 12. Same class of correction as "Mercuri (MV)" at Phase 235: the row was
mine and it was wrong.

**A dry run against the pre-merge tree caught six wrong assumptions before
the gate ever ran for real.** The API mounts under `/v1`, not bare; every
`/v1` route is API-key gated, so the gate authenticates as a real client
with a key minted for a seeded user; my fixture loaded DTCs, knowledge and
parts and had **forgotten the compat catalogue entirely**, so `recommend`
returned nothing for every make; `compat check` asks whether one named
adapter fits and requires `--adapter`, where the gate's question — which
adapters fit this bike — is `compat recommend`; the parts catalogue is
shop-scoped, so the key's user needs a shop it owns, created through the CLI
as Gate 11 does; and the parts search returns a bare list. Each was found in
seconds against a scratch copy rather than after an eleven-minute regression.

**Moto Guzzi is the honest gap, and the gate records it rather than hides
it.** No Track K row names the make. It has no DTC file, no compat rows and
no make-file of its own; its seven issues and nine parts rows all come from
the cross-make phases 236–239. Five tests document that — in the Gate 11
pattern, passing today and meant to fail the day someone fills the gap,
which is the cheapest reminder to update the gate and the roadmap. A sixth
records that the Aprilia 660 valve interval is unverified.

**The DTC test asks the question Phase 235 was built for.** For each make
with a DTC file, the gate looks up that make's first code with the make set
and asserts the returned row is the make's meaning, not the SAE generic — on
Aprilia, P0510 must come back as rear wheel radius acquisition, not a
throttle switch. That is `dtc_repo` resolving make-specific before generic,
checked through the HTTP front door.

**Corpus invariants are now gated, not just tested per phase.** No campaign
reference number anywhere in the European files (the Phase 231 decision);
the provenance vocabulary is exactly the six values of migration 052 and
`regulation` is in use; and the documented known-issue count equals the live
seed count — the Phase 208 guard's invariant, re-asserted at the gate.

**Key finding: a gate's dry run is where the gate's own assumptions fail.**
Six of them, none about the corpus, all about how the front doors are
actually built.
