# Phase 236 — European diagnostic tooling, cross-platform comparison

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Say what is only visible when the European makes' tooling is compared side by
side — nothing a single make's electrical phase could have said.

Guard: `pytest tests/test_phase236_european_tooling.py`.
Outputs: `known_issues_european_tooling.json`, its test, roadmap row 236.

## Existing-code audit (Step 0)

**1. The row's ground was already taken five times over.** Row 236 names
GS-911, TuneECU and Ducati DDS. Each is in three files already; `CAN` is in
14 and `OBD` in 9. Phases 215, 220, 225, 230 and 235 each covered their own
make's tools, connectors and generic-reader behaviour. A file repeating that
would shadow five phases.

**2. The only uncovered axis is the comparison.** Which tool spans which
makes; where the *same* product behaves differently by make; which makes are
the exception in the group. None of that can be written from inside one
make's file, because each make's own documentation names only itself.

**3. Two proposed topics belong to Phase 235 and were dropped.** ISO 19689
clause text is in the compat catalogue; OBD stage I/II is in the Aprilia/MV
file. The refuters flagged both as writable without naming a manufacturer,
and they were right.

**4. The genericness bar is enforced, not hoped for.** Every entry must name
a specific tool *and* a specific make-level behaviour. The test caught one
entry that had gone vague ("the group's platform") and one that said "at
least one make" — both rewritten with the actual names and adaptor letters.

## Method

Paired capped 6-agent run with Phase 237 — 2 questions × 2 refuter lenses,
the second lens instructed to flag any entry writable without make-specific
hardware. This phase's question was refuted on **contradiction**, not on
genericness: "only 2 of 15 entries are pure theory."

## Results

| Metric | Value |
|--------|-------|
| Known issues | 865 → 878 |
| Entries | 13 — 8 `service-manual`, 5 `model-generated` |
| Research | paired run with 237 (6/6 returned) |
| Refuter verdicts on this question | 2 refuted — on contradiction, not genericness |
| Proposed entries dropped as generic | 2 of 15 (both already Phase 235's) |
| Entries my own test sent back as vague | 2 |
| Phase tests | 30 |
| Backend regression | 5820 passed / 1 failed → fixed, targeted re-run green; clean full figure recorded at 237 |

**The headline finding was wrong, and the correction is a better finding.** The
research reported that TuneECU degrades *identically* on newer Triumphs and
KTMs — write survives, read does not — and built a consent-and-liability
scenario on it. A refuter read the table's cells rather than its summary:
Triumph's degraded rows are diagnostics-and-write, KTM's are diagnostics
*only*. The tool cannot write a 1290 Super Duke at all. The finding had even
contradicted itself between its scope and claim fields. What ships is the
asymmetry itself: the same tool loses different functions on different makes,
and a shop that learns its behaviour on one make and generalises is wrong on
the other.

**A second contradiction was internal.** The finding's closing paragraph said
the red-plug Triumphs were absent from the table; its own earlier section had
listed them as present. Scrambler 1200, Tiger 850/900, Street Triple 765 RS
from a VIN break, Trident 660 and Tiger Sport 660 are all there. Only the
400s are not.

**Three things deliberately not printed.** The Triumph connector transition
year — a refuter found the stated timeline off by three model years, and a
wrong year decides which lead a shop orders. A Ducati dealer-tool part number
— it came from a reseller listing that names a different version. And the
PADS acronym's expansion in this file — the cited source did not contain it,
and Phase 235 already owns it.

**The genericness bar caught me twice.** The test requires every entry to
name a specific tool and a make-level behaviour. One entry said "the group's
platform"; another said "at least one make" and "a 3-pin shell". Both were
rewritten with what the source actually says: TuneECU's adaptor B is literally
named "Guzzi-Ducati-Aprilia 3pin", and KTM's single 6-pin shell takes adaptor
C for K-Line or D for CAN. The bar produced better entries, not fewer.

**Phase 233's ownership guard fired, and was made an invariant.** It forbids
MV designations outside the MV files; 235 had been exempted by filename. This
file names MV Agusta, and so will 237–239. Exempting by the `european_`
prefix rather than by filename means no later cross-make phase has to come
back and extend a list — the constant-for-invariant bug, avoided this time
rather than hit.

**Key finding: a cross-make claim built from a table's summary fails at the
table's cells.** The research's one genuinely comparative insight was the one
it got backwards, because it summarised a column it had not read row by row.
