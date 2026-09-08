# Phase 227 — Triumph Tiger adventure line

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Cover the Tiger adventure line — the middleweight and large triples
across their chain- and shaft-driven generations.

CLI: `motodiag kb list --make triumph`; guard is
`pytest tests/test_phase227_triumph_tiger.py`.

Outputs:
- `known_issues_triumph_tiger.json`
- `tests/test_phase227_triumph_tiger.py`
- Roadmap row 227 corrected as the research dictates
- Documented known-issue count updated (784 → 795)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. Tiger has zero mentions anywhere in 784 entries** — not one, in any
file. But the *adventure topic* is among the corpus's best covered: 66
entries across `bmw_f_series_gs` (12), `ducati_multistrada` (8),
`suzuki_vstrom` (10), `honda_dualsport` (10), `kawasaki_dual_sport` (10),
`yamaha_dualsport` (10) and `ktm_1290` (6), with "adventure" matching 16
files and "shaft drive" 9. So this is the 221/226 situation, not the 223
one: the make is absent and the topic is saturated, which means the
backwards genericness test applies at full strength. Every entry must
name a Tiger designation, and an existing adventure entry must score
zero against the same check.

**2. The row omits a generation, for the third block-opening phase in a
row.** Row 227 reads "800/900/1200". The **Tiger 1050** and Tiger Sport
1050 are neither in that list nor in row 228's — 228 does list "1050",
but as part of "Street Triple / Speed Triple", which is the Speed Triple
1050, a naked sport. By body style the Tiger 1050 is an adventure-sport
and belongs here. Same shape as the 690 Duke (222) and the 790
Bonneville (226). The earlier Tiger 885i/955i straddle row 229's "early
Hinckley" boundary and are flagged rather than resolved unilaterally.

**3. What the corpus cannot already say: crank arrangement.** `T-plane`
returns **0 files**, `120-degree` **0**, `firing order` 2. Phase 226's
strongest finding was that crank angle is not the split it looks like;
the Tiger 900 is reported to have moved from an even-firing triple to a
T-plane crank, which would be the same class of fact and is uncovered
here. It is being researched rather than asserted.

**4. The adapter catalog has a Tiger-shaped gap this phase does not
fill.** Two `tiger%` rows, both `partial`, both **2013–2025** — so the
2011–2012 Tiger 800 has no row, the same shape as the air-cooled
Bonneville gap Phase 226 left. Row 230 owns Triumph tooling; the count
stays guarded at 5.

**5. Deferral boundaries.** 226 owns the Bonneville twins, 228 the
Street and Speed Triples, 229 the pre-Hinckley and early Hinckley bikes,
230 fault codes, TuneECU and dealer mode. `dtc_codes: []` throughout.

**6. Provenance follows Phase 226, not the phases before it.** External
facts are researched by agents with web access and each finding refuted
by two lenses; entries resting on Triumph publications or regulator
recall records are `service-manual`, entries resting on owner reports
are `forum`, and each says in prose what it is drawn from. Nothing here
is `model-generated`. The user chose this explicitly for this phase.

## Logic

1. Research the generation map, the T-plane question, the documented
   faults and the adventure-specific service detail; accept only
   findings that survive both refuters, and let refutations remove
   content as readily as they add it.
2. Write entries anchored on what survived, with evidence type visible
   in the prose.
3. Validate mechanically: designation bar with a corpus-wide
   counter-assertion over the adventure files, no interval figures
   unless Triumph-cited, deferral boundaries, catalog guarded at 5,
   provenance, symptom format.

## Key Concepts

- **The make is absent and the topic is saturated** — 66 adventure
  entries mean an entry must name a Tiger, not merely avoid their topic.
- **Crank arrangement is the likely differentiator**, as it was in 226,
  and it is uncovered in this corpus.
- **Evidence type is part of the entry**, per 226.
- Claim checks exempt negation both ways (219), reported speech (221),
  comparison (222) and quotation (223) — and select on mention versus
  use, which has now caught me in eight phases.

## Verification Checklist

- [x] Every entry names a Tiger designation in title and body, with a
      counter-assertion run over the adventure files corpus-wide
- [x] Every entry states its evidence type in prose; sources are
      `service-manual` or `forum`, never `model-generated`
- [x] No service interval stated unless cited from Triumph's schedule
- [x] The T-plane claim is written only as the research established it,
      with the affected models named and unknowns admitted
- [x] Shaft-drive versus chain stated per generation
- [x] No 226/228/229 content; no DTC or tooling content (230);
      `dtc_codes: []`
- [x] Adapter catalog Triumph rows unchanged at 5
- [x] Row 227 corrected (Tiger 1050) if the research confirms it; the
      885i/955i boundary with 229 flagged
- [x] Symptom needles quoted from shipped data; regression green; F9
      clean

## Risks

- **Duplication is the sharpest hazard**, with 66 adventure entries in
  the corpus. An entry that could have been written about a GS or a
  V-Strom does not belong here.
- **Fabricated recalls** remain the other hazard; gated on research with
  campaign numbers and URLs.
- **No independent reader** of the final prose, as in 217–226.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 784 → 795 |
| Entries | 11, all `service-manual` |
| Research agents / refuters / died | 4 / 8 / **0** |
| Findings survived / refuted | 3 / 1 |
| Researched claims refuted and **not shipped** | 5 |
| Findings handed to another phase | 1 (P0315 → row 230) |
| Roadmap corrections in the row | 2 (Tiger 1050 omitted; "Ohlins" unsupported) |
| Phase tests | 46 |
| Backend regression | 5421 passed / 0 failed |

**The row was wrong twice, and the second error is the more interesting
one.** It omitted the Tiger 1050 — the third block-opening row omission
in a row, after the 690 Duke and the 790 Bonneville. But it also said
"Ohlins on top trim", and no Triumph handbook names a suspension
manufacturer at all; the spec pages give Marzocchi on the Tiger 900 GT
and Showa on the 2022+ Tiger 1200, with WP earlier. Öhlins is not part of
the Tiger line. A row can be wrong by naming a supplier that was never
there, and only research catches that.

**Five researched claims were refuted and none of them shipped.** The
Tiger 1050's front wheel, the Pro package's contents, the brake-pad
corrosion mechanism, the XR/XC acronym expansion, and the 2024 Tiger 900
valve interval. The last is the one a shop would have acted on: a refuter
extracted the handbook's maintenance table with per-word coordinates and
resolved the valve row to the 12,000 and 24,000 columns, showing the
widely repeated 18,000-mile figure to be a misreading of a column header.
The entry states it is false rather than quietly using the right number,
because a customer arriving with the wrong figure needs to be told.

**One finding went to another phase instead of into the file.** P0315 —
a crankshaft-position adaption code that cannot be cleared with the
normal erase function — is exactly Phase 230's material. It is recorded
on row 230 and asserted absent here. Research that produces content for a
phase you are not writing is still worth doing; the alternative is
discovering it twice.

**Cost, recorded because the user raised it.** 12 agents, 1.55M subagent
tokens, 53 minutes. From Phase 228 the cap is ~6 agents with progress
check-ins during the run.

**Key finding: a refuter's most valuable output is a claim you then do
not ship.** Two phases running, the refutation pass has removed eight
claims that would otherwise have gone into the corpus, three of which
would have sent a shop to the wrong part or the wrong interval.
