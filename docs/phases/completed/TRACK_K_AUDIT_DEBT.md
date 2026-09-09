# Track K — closure audit findings (open)

Produced by a read-only adversarial audit run immediately before Gate 12
closed Track K on 2026-09-08. Six dimensions, each finding independently
verified by a second agent: **46 verdicts, 29 confirmed real** (the
verification layer rejected roughly 60%, which is its purpose).

**Five findings were fixed at Phase 240** — the leaked deliberate absences,
listed in that phase's implementation doc. A sixth, the Euro 4 "free of
charge" error, was fixed in the Phase 240 follow-up. Everything below is
confirmed and **open**.

**A counting caveat that matters.** The contradictions auditor reported
finding **16** cross-phase contradictions. The workflow submitted only the
first **8** for verification — the script capped each dimension at
`findings.slice(0, 8)` — and 6 of those 8 were confirmed. **Eight
contradictions were therefore never verified and are not listed below.**
Section A is the confirmed subset, not the full set. Anyone working this
list should re-run the contradictions dimension without the cap before
believing the corpus is clean.

The per-finding verifier notes, including every `corrected_fix`, are
committed alongside this file as `TRACK_K_AUDIT_VERIFIER_NOTES.md` — with
the **rejected** verdicts too, so nobody re-litigates an over-claim. Roughly
60% of findings did not survive verification.

The audit's own headline: every one of these is a defect no single phase's
tests could have caught, because each file was written and reviewed against
its own sources and never against its siblings.

## A. Cross-file contradictions — correctness defects

A mechanic acting on the older entry does the wrong work. Ordered by cost of
being wrong.

| # | Contradiction | Files |
|---|---------------|-------|
| A1 | **The BMW alternator belt.** One entry describes a poly-V belt whose tension must be set, across 1994–2023. The other establishes that from mid-2003 BMW moved to an **ELAST stretch-fit belt that is never re-tensioned**, and that treating it as a poly-V **destroys it**. Corroborated by the parts catalogue. | `known_issues_bmw_r_series.json[7]` vs `known_issues_european_differentials.json[1]` |
| A2 | **BMW final drive crown bearing.** One lists "lubricant breakdown from extended change intervals" as a cause and advises shortening the oil interval. The other establishes the pre-2010 bearing is **sealed and greased, never reached by the final-drive oil** — so no oil change addresses it. | `known_issues_bmw_r_series.json[0]` vs `known_issues_european_differentials.json[11]` |
| A3 | **When the legislated OBD layer begins.** One says motorcycles carry it "only from Euro 5 (roughly 2021)". Phase 235's `regulation`-sourced entry, verified against EU law, establishes **OBD stage I from Euro 4** (L3e: new types 1 Jan 2016, all registrations 1 Jan 2017). Wrong by a full emissions generation. | `known_issues_bmw_electrical.json[0]` vs `known_issues_aprilia_mv_electrical.json[3]` |
| A4 | **Ducati valve schedule time element.** One tells a shop to check the elapsed-time element of the desmo schedule. The other establishes from Ducati's own sheets that the **valve check is by distance only** and the months figure belongs to the **timing belts**. | `known_issues_ducati_desmo.json[4]` vs `known_issues_european_intervals.json[3]` |
| A5 | **KTM valve-train architecture.** The intervals file places KTM in the shim-under-bucket column unqualified. The differentials file establishes the **690 LC4 runs a roller rocker** whose bearing fails — a component a bucket-and-shim model does not contain. The intervals file itself covers the 690. | `known_issues_european_intervals.json[4]` vs `known_issues_european_differentials.json[7]` |
| A6 | **MV swingarm bolt failure mode.** The entry denies a documented fact — "not, as is sometimes described, a bolt that breaks while being tightened". The campaign was **detected by a factory worker when a screw broke at the prescribed torque during assembly**. Both halves are true: found at assembly, recalled for in-service failure. | `known_issues_mv_agusta_triple.json[2]` |

**Every verifier warned that the naive fix breaks the tree.** Entry counts are
pinned in several places (`test_phase211_bmw_r_series.py` pins 12 twice;
`test_phase212` pins 24), and a generation-scoping change to
`bmw_r_series.json[7]` breaks a parametrised coverage test that relies on it
spanning 2018. Read each verifier's `corrected_fix` in `TRACK_K_AUDIT_VERIFIER_NOTES.md`
before editing.

## B. Guard and gate defects

- **B1** Two `forum` entries carry no "Forum tip:" — `known_issues_triumph_bonneville.json[11]` and the MV triple sprag entry. Exactly two, corpus-wide, of 17 `forum` entries. Three Track K files enforce the biconditional locally; these predate it. One verifier notes the obvious fix turns a currently-green test red — read it first.
- **B2** A `service-manual` entry that states in its own text that it rests on **no source at all** (the MV F4 shim-diameter entry). The content is right; the label is wrong. `unverified` is the honest value.
- **B3** Eight constant-pinning tests found by the shape sweep — counts and lists a later phase must return and edit. The constant-for-invariant family, still live.
- **B4** `test_phase235_aprilia_mv_electrical.py` never opens `generic.json`, so its shadow-earning claim is unverified there.
- **B5** Vacuous assertions found by coverage and runtime-data analysis across the 211–240 test files.

## C. Provenance labelling consistency

The vocabulary is clean — only the six permitted values appear, and the single
`regulation` entry genuinely quotes legal text. What is inconsistent is that
**the same evidence class carries different labels in the same file**: a tool
vendor's own compatibility table is `service-manual` in four
`known_issues_european_tooling.json` entries and `model-generated` in two;
parts-fiche evidence is `service-manual` in five `known_issues_european_parts.json`
entries and `model-generated` in two. Three `known_issues_ktm_electrical.json`
entries open "General knowledge entry, drawn from KTM's published technical
specifications" — self-contradicting in one clause.

This needs a **rule** decided and applied, not entry-by-entry edits. The
natural rule: the source reflects the weakest link in the entry's
load-bearing claim.

## D. Scope note, not a defect

`src/motodiag/advanced/data/recalls.json` carries 15 European rows with
synthetic campaign ids. It predates Track K (added at Track F, commit
`68f65f4`) and no Track K test reads it. The Phase 231 no-campaign-numbers
decision scopes to Track K-authored content. Either state that boundary in
Gate 12's docstring or extend the scan — leaving it unstated makes the
invariant look broader than it is.
