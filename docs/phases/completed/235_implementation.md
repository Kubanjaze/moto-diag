# Phase 235 — Aprilia + MV Agusta electrical, fault codes and dealer tools

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Close the tooling and fault-code gap that Phases 231–234 each deferred here,
and fill the **zero adapter rows** both makes have carried through the block.

Guard: `pytest tests/test_phase235_aprilia_mv_electrical.py`.
Outputs: `known_issues_aprilia_mv_electrical.json`, `dtc_codes/aprilia.json`,
`dtc_codes/mv_agusta.json`, adapter + compat rows for two new makes, its test,
roadmap row 235, and the inversion of the zero-guards in 231 and 232.

## Existing-code audit (Step 0)

**1. The gap is real and was guarded, not assumed.** `compat_matrix.json` holds
146 rows across nine makes and **zero** for either make here. Phase 231 and 232
each assert that zero with a counter-assertion that other makes have rows, so
the number means something. This phase inverts both — the Phase 230 precedent,
where an `ORIGINAL_*_ROWS` constant was added so the earlier phases assert
what they actually meant (*my* rows survive) instead of a count.

**2. `dtc_codes/` has seven files and neither make.** bmw, ducati, generic,
harley_davidson, ktm, triumph. Adding two makes here is new ground, and
`dtc_repo.get_dtcs` resolves make-specific before generic — so every row added
must **earn its shadow**: differ from the generic row in causes *and* fix.

**3. Phase 231 explicitly deferred the content to this row.** Its
`test_no_tooling_or_code_content` forbids `\bP0\d{3}\b` and `\bPADS\b` in the
RSV4 file, case-sensitively — after `PADS` matched brake *pads*. That test
stays green; this phase owns those strings, in different files.

**4. One claim here is already made, and must not be restated.** Phase 232
ships "a torque-monitor safety layer can stop the engine while storing a code
the dashboard never displayed". The dash-invisibility of the *safety layer* is
therefore taken. What this phase owns is the scope of it — see below — and a
test asserts the distinction rather than trusting me to remember it.

**5. The roadmap row names an ECU supplier I cannot source.** Row 235 reads
"Mercuri (MV)". That string appears **nowhere else in either repo**, and no
source in this phase's research found it; MV's fault tables come from an
**Eldor** ECU. I am correcting the row rather than writing content from it —
noted here because the row is my own and it was wrong.

## Method

Research ran as one capped 6-agent run (2 questions × 2 refuter lenses), the
cadence held since 227. **5 of 6 returned**; the missing agent is the
contradiction lens on the tooling question, so tooling scope is written at the
conservative setting its own caveats ask for — see Results.

**Two refuters disagreed on a number and I settled it against the source
myself** rather than picking one. Detail in Results.

## Planned content

- **DTC, Aprilia** — the false-friend block: codes that look SAE-standard and
  are not, plus the never-displayed set.
- **DTC, MV Agusta** — a genuine manufacturer P1xxx block, third-party sourced
  and labelled as such.
- **Knowledge, ~8 entries** — dealer tools and what each actually does, the
  connector generations, the service-code menu, and the two makes' opposite
  failure modes under a generic reader.
- **Adapters + compat rows** — including deliberate `incompatible` and
  `read-only` rows, as Phase 230 did for carburetted Bonnevilles.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 847 → 855 |
| Entries | 8 — 4 `service-manual`, 4 `model-generated` |
| DTC rows | 13 (Aprilia 7, MV Agusta 6) — two makes that had none |
| Adapters | 28 → 34 |
| Compat rows | 146 → 167; **aprilia 0 → 15, mv-agusta 0 → 6** |
| Research runs | 1 capped 6-agent run (6/6 returned) |
| Refuter verdicts | 3 refuted, 1 clean |
| Claims I verified against the primary source myself | 2 |
| Phase tests | 50 |
| Backend regression | 5734 passed / 0 failed |

**Two refuters disagreed on a number, so I settled it against the source
rather than picking one.** The research claimed "fourteen" Aprilia codes are
never shown on the instrument panel and then listed fifteen, including P0218.
One refuter said 18 and dropped P0116; the other said 19. The manual was on
disk, so I counted it: **19**, and the second refuter's list was exactly right.
P0218 is genuinely not on it — the manual gives P0217 and P0218 identical text
and neither carries the never-displayed sentence.

**My own first count was 18, and it was wrong for the reason I had just been
warned about.** The sentence is line-wrapped in the PDF as "in- strument", so
a plain search for "instrument panel does not indicate" silently misses the
P0611 occurrence. The refuter's note said exactly this and I hit it anyway one
step later. De-hyphenating first gives 19 on the nose. The set is now a
module constant in the test with that trap written down beside it.

**The strongest refutation overturned a full model generation, and it changed
what this phase ships.** The research concluded that any pre-Euro 5 machine on
either make is closed to a generic tool, and encoded that as two `incompatible`
rows spanning 1997–2020. A refuter went and opened the EU regulations the
finding had declared unretrievable, and found that L3e vehicles became **OBD
stage I from 1 January 2016**, that access must be "unrestricted and
standardised", and — the operationally valuable part — that the proprietary
plug is a permitted **"alternative connection interface"** whose pinout the
manufacturer must publish **free of charge** and for which it must supply a
generic-scan-tool adapter "upon request to all independent operators in a
non-discriminating manner". Aprilia's 3-pin and MV's 4-pin Euro 4 plugs are
that interface: a documented bridge, not a wall. I fetched Regulation (EU)
2018/295 and confirmed those clauses verbatim before writing them, because
this is the one claim in the phase a shop would act on against a manufacturer.
The generic-reader rows are now three tiers per make — incompatible to 2015,
**read-only** across Euro 4, read-only on Euro 5 — and the entitlement is its
own entry, scoped honestly: the access is real and narrow, and it is a
type-approval obligation rather than a bench-verified response from any
particular machine.

**The two makes are opposite traps, and that is the phase's finding.** Aprilia
ships **no manufacturer P1xxx block at all** — every fault is an ordinary
P0xxx number — but many of those numbers carry proprietary meanings: P0510 is
rear wheel radius acquisition, not a closed throttle position switch; P0462 is
the quick-shift sensor, not a fuel level sensor; P0217 is manifold pressure
below estimate, not engine over-temperature. MV does the opposite, using a
genuine P1xxx block a generic reader cannot decode at all.

**MV's P1xxx codes are deliberately not decoded here.** The block is real and
named in a knowledge entry so a mechanic knows the code is genuine rather than
a tool fault, but no DTC row is shipped for it, because no MV primary document
could be opened and a guessed meaning would reproduce the exact Aprilia
failure this phase documents. A test asserts no P1xxx row exists — the Phase
233 and 234 discipline applied to a code range.

**The never-displayed entry had to extend Phase 232, not restate it.** 232
already ships the claim that the ride-by-wire torque monitor stores a code the
dash never showed. What is new is the scope: the set is nineteen codes and
most are ordinary — oxygen sensor, its heater, engine and air temperature,
starter switch, secondary air, battery voltage. A routine emissions fault can
be present and current with no light of any kind. A test asserts the entry
says so, rather than trusting me to remember the boundary.

**A test caught a content hole I had left.** Phase 231 deferred the strings
`P0xxx` and `PADS` to this row, and my prose named neither tool while the
adapter catalogue named both — explicit in one surface and coy in the other.
The guard for 231's deferral failed, and the entries now name PADS and TEXA
directly, including the contrast that matters: MV's official tool is sold
openly to anyone, and Aprilia's is not obtainable by an independent at all.

**The guard inversion deliberately avoids the trap I have hit three times.**
Phases 231 and 232 asserted zero adapter rows for these makes; both now assert
the gap is filled and the make slug is `mv-agusta`. Neither pins 235's adapter
slugs, because a slug list would be a constant every later Aprilia or MV
adapter must return and update — the constant-for-invariant bug from 221, 222
and 230. The naming variants stayed in the assertion because they were the
original point: a row filed under "mv" would have satisfied the old zero-check
by spelling rather than by substance.

**My Step 0 audit was keyed on a name and missed two guards.** I searched for
the exact test name Phase 231 used and concluded 231 and 232 were the only
phases holding the adapter zero-guard. Phases 233 and 234 held the same guard
called something else, so the full regression failed on two un-inverted copies
plus one ownership boundary I had not looked for at all. Re-audited
semantically and confirmed against every corpus-touching test file — 95 files,
1354 passed — before the final run. It is the constant-for-invariant mistake
one level up: an audit keyed on an identifier finds one phase's habits rather
than the invariant.

**Provenance vocabulary gap, recorded rather than papered over.** Migration
051 permits `unverified`, `model-generated`, `forum`, `service-manual` and
`mechanic-verified`. A verbatim EU regulation is none of these. Marking it
`unverified` would be worse than imprecise — that value is in Gate 2's
forum-derived allowlist, so a primary legal text would have been held to the
forum-tip rule. The regulation entries are `service-manual`, meaning primary
official document, with the exact citation in the body and a test requiring
it; vendor-documentation entries are `model-generated`. A `regulation` value
would be the honest fix and it needs its own phase — extending a CHECK
constraint touches the Gate 2 test and two API modules.

**Coverage uncertainty is recorded in the catalogue instead of smoothed over.**
No source consulted confirms that MV tool coverage is equal across the
three- and four-cylinder families, and OBDSTAR publishes per-model coverage
only as downloadable lists. Those rows say so in their own notes, and a test
asserts the uncertainty is present. Only four year ranges in the phase are
genuinely source-stated; every other coverage row is labelled an era estimate.

**Key finding: the make that looks readable is the dangerous one.** A generic
scan tool on an MV Agusta fails loudly and sends the mechanic to find the
right tool. On an Aprilia it succeeds, formats a clean answer, and names the
wrong component — because the codes look standard and are not. Silence is a
safer failure than a confident wrong answer, and nothing about the code number
warns anyone which one they are getting.
