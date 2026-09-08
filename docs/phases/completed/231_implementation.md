# Phase 231 — Aprilia RSV4 / Tuono V4

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Open the Aprilia + MV Agusta block with the RSV4 superbike and its
Tuono hyper-naked sibling.

CLI: `motodiag kb list --make aprilia`; guard is
`pytest tests/test_phase231_aprilia_rsv4.py`.

Outputs:
- `known_issues_aprilia_rsv4.json`
- `tests/test_phase231_aprilia_rsv4.py`
- Roadmap row 231 corrected as the research dictates
- Documented known-issue count updated (824 → 832)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. Aprilia has zero entries.** Searching Aprilia, RSV4, Tuono,
Dorsoduro, Shiver, MV Agusta, Brutale, F3 and F4 across 824 entries
returns four hits, and all four are false positives — the Honda CBR600F
file's "F2/F3/F4" generation labels. So the make is absent, and this
phase opens a block.

**2. Neither Aprilia nor MV Agusta has a single adapter row.** The
compat catalog covers nine makes — Harley, Honda, Yamaha, Kawasaki,
Suzuki, BMW, Ducati, KTM and Triumph — and neither of these. That is a
larger gap than the ones 221 and 226 left, and **row 235 owns it** by
name ("Aprilia + MV electrical + dealer tools"), so this phase guards
the absence rather than filling it, exactly as 221 and 226 did.

**3. The topic is saturated even though the make is absent.** `V4`
matches 10 files, traction control 15, Ohlins 15. So the backwards
genericness test applies at full strength: an entry that could have been
written about a Panigale V4 or an S1000RR does not belong here, and the
counter-assertion sweeps the corpus. What is uncovered: `radial valve`
returns **0** and `counter-rotating` **1**, both of which belong to the
MV phases rather than this one.

**4. The row's numbers need checking.** Row 231 says "V4
superbike/hyper-naked, Ohlins, aPRC electronics". Two things to resolve
by research rather than assumption: the **"1100" models' actual
displacement**, since Aprilia's model naming rounds and the last four
phases each found a badge that is not a capacity; and what **aPRC**
actually stands for and covers, since the row uses the acronym without
expanding it and Phase 227 found an unsupported supplier claim in
exactly that position.

**5. Research is capped and paired.** Per the standing rule this run is
6 agents. Because the Aprilia block has two model phases with the same
make and the same sources, one run covers **both** 231 and 232 — two
research questions, one per phase, two refuter lenses each. That halves
the number of runs across the block without exceeding the cap on any
one. Phases 225–230 cost 660–830K subagent tokens per run at this size.

## Logic

1. Research the RSV4 and Tuono generation map, the V4 architecture, aPRC
   and the documented faults; accept only what survives both refuters.
2. Write entries that each turn on something Aprilia-specific, and cut
   any candidate that could be written about another make's V4.
3. Validate mechanically: designation bar with a corpus-wide
   counter-assertion, intervals only if Aprilia-cited, deferral
   boundaries to 232–235, adapter absence guarded at zero, provenance.

## Key Concepts

- **The make is absent and the topic is saturated** — the 221/227 shape.
- **Badges are not capacities** until proven otherwise; four consecutive
  phases found one that was not.
- **The adapter absence is guarded, not filled** — 235 owns it.
- Claim checks exempt negation both ways (219), reported speech (221),
  comparison (222) and quotation (223), and run on assertion-bearing
  fields only, which has caught me in eleven phases.

## Verification Checklist

- [x] Every entry names an RSV4/Tuono designation in title and body,
      with a counter-assertion swept over every non-Aprilia file
- [x] Provenance per entry; `service-manual` entries say what they are
      drawn from; no `model-generated` entry carries a sourced figure
- [x] No interval stated unless cited from Aprilia's own schedule
- [x] The "1100" displacement question resolved explicitly
- [x] aPRC expanded and described as the research establishes it
- [x] No 232 content (Dorsoduro/Shiver/SR Max), no 233/234 content (MV),
      no 235 content (tooling, fault codes); `dtc_codes: []`
- [x] Aprilia and MV adapter rows still **zero** — asserted, with a
      counter-assertion that other makes demonstrably have rows
- [x] Row 231 corrected if the research supports it
- [x] Symptom needles quoted from shipped data; regression green; F9 clean

## Risks

- **Duplication with the crowded V4 and rider-aid segment** is the
  sharpest hazard.
- **Charging-system claims** are widely repeated about these bikes and
  need their evidence type established rather than assumed — recall,
  bulletin or forum consensus are three different conversations.
- **No independent reader** of the final prose, as in 217–230.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 824 → 832 |
| Entries | 8, all `service-manual` |
| Research agents / refuters / died | 2 / 4 / **0** (one run covering phases 231 **and** 232) |
| Cost | 953K subagent tokens, 37 min — for two phases |
| Findings survived / refuted | 0 / 2 (both partially, with concrete corrections) |
| Campaign numbers in the shipped file | **0** — by decision, after a phantom one was caught |
| Phase tests | 34 |
| Backend regression | 5591 passed / 1 failed, then fixed — the single failure was the Phase 208 doc-count guard catching **my own error**: I wrote Phase 232's content file into the tree while this phase's regression was running, so the live seed count became 837 while the docs said 832. The guard is doing exactly its job. The file was backed out, the count re-verified at 832 and the failing test re-run green; the clean full-suite figure is recorded at Phase 232, which runs over the same tree plus that file |

**Research was paired across two phases for the first time.** One capped
6-agent run answered both this phase's question and Phase 232's, since
they share a make and the same sources. That halves the number of runs
across the block without exceeding the cap on any one, and the cost
lands at roughly one-and-a-half single-phase runs rather than two.

**A phantom recall number changed how the file cites campaigns.** The
research attached a UK reference to a brake campaign; in the UK dataset
that number belongs to a *Citroën* recall, and the real campaign was a
Canadian one whose number had been given a UK prefix. Rather than curate
a corrected list, the file cites **no campaign numbers at all** — the
entries describe what each campaign covers and send the reader to the
frame number, which is the action a shop should take anyway and which
cannot go stale.

**The best finding is a search failure, not a fault.** A refuter checking
the claim that the connecting-rod recall was UK-only found a US
counterpart that the original search had missed — because the regulator
files it under the make spelled **"APRILLA"**. So a correctly spelled
by-make lookup returns clean on a machine whose published remedy is a new
engine. That is the second time in the corpus that a regulator's own data
has been the hazard, after the Phase 228 index defect, and both entries
now teach the same habit: check by frame number.

**Key finding: a clean recall search can be a data artefact.** Reporting
"no recalls found" is only as good as the query, and on this make the
query itself is what fails.
