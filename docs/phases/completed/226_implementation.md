# Phase 226 — Triumph Bonneville family (Hinckley, 2001 on)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Open the Triumph block with the Hinckley Bonneville family: the
parallel-twin modern classics across their air-cooled and liquid-cooled
generations.

CLI: `motodiag kb list --make triumph`; guard is
`pytest tests/test_phase226_triumph_bonneville.py`.

Outputs:
- `known_issues_triumph_bonneville.json`
- `tests/test_phase226_triumph_bonneville.py`
- Roadmap row 226 corrected as the research dictates
- Documented known-issue count updated (773 → 784)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. Triumph has zero entries.** 773 entries across ten makes and not
one Triumph — the single mention anywhere is incidental (points ignition
in a vintage entry). As with KTM at 221, this phase opens a block, so
there is no same-make file to collide with.

**2. The topic is close to empty, so the hazard is gaps, not
re-telling.** The modern-classic / retro-twin topic that a Bonneville
entry would sit in has almost no coverage: `W800`/`W650` **0 files**,
`XSR` **0**, `CB1100` 1, `360-degree crank` **0**, `air-cooled twin` 1.
"Modern classic" matched 5 files but on inspection those are "retrofit"
and "retro-fit" — false positives. This is the 223 situation (real gaps)
rather than the 221 situation (topic told nineteen times). What does
exist is 9 parallel-twin files and the 270-degree crank in 2, so the
designation bar still applies: every entry must name a Bonneville-family
designation, and a generic parallel-twin entry must score zero against
it.

**3. The row's numbers omit a generation.** Row 226 reads "865/900/
1200cc". The Hinckley Bonneville launched in 2001 with a **790cc** twin
before the 865 — if the research confirms the years, that generation is
in neither row 226's list nor row 229's, whose "early Hinckley
carburetted" sits in a sentence about the T509/T595 triples. Same shape
as the 690 Duke at 222. Corrected at close-out if confirmed.

**4. The adapter catalog has a Triumph gap this phase does not fill.**
Five Triumph rows: `obdlink-lx` on `bonneville%` **2016–2025 only**
(the liquid-cooled CAN bikes), plus Tiger and 675 rows. The air-cooled
2001–2015 Bonneville has no row at all, and no Triumph row is `full`.
Row 230 owns Triumph tooling by name ("TuneECU software, dealer mode"),
so — exactly as 221 did for KTM — the count is guarded at 5 and the gap
is left for its owner rather than pre-empted.

**5. Deferral boundaries.** 227 owns the Tigers, 228 the triples, 229
the pre-2001 and 1990s Hinckley bikes, 230 fault codes, TuneECU and
dealer mode. So: no triple content, no Meriden content, no DTC content,
no tooling content, `dtc_codes: []` throughout.

**6. The external facts are not written from memory.** 225 established
the pattern: the generation map, the documented faults per generation,
the valve gear and crank angle by generation, and the EFI-with-
carburettor-look hardware are being researched by agents with web
access and each finding refuted by two lenses, with 212's lesson built
in. Content waits for the survivors. Where the research says "unknown",
the entry says so or is not written.

## Logic

1. Research the generation map and the documented faults; accept only
   findings that survive both refuters.
2. Write entries anchored on what the research established and only
   that: generation identification (shared names, different engines),
   documented faults with their evidence type visible, and the
   air-cooled/liquid-cooled service differences.
3. Validate mechanically: designation bar with a parallel-twin
   counter-assertion, no interval figures unless cited from Triumph's
   schedule, deferral boundaries, catalog count guarded at 5, symptom
   format, provenance.

## Key Concepts

- **Shared names, different engines** is the family's own trap: T100,
  Thruxton, Scrambler and Speedmaster all name both an 865 and a
  liquid-cooled successor.
- **Evidence type is part of the entry.** A recall, a bulletin and a
  forum consensus are not the same weight, and the prose says which.
- **Research before writing** for anything external — the 225 pattern.
- Claim checks exempt negation both ways (219), reported speech (221),
  comparison (222) and quotation (223).

## Verification Checklist

- [x] Every entry names a Bonneville-family designation in title and
      body, with a counter-assertion that a parallel-twin entry from
      another make scores zero
- [x] Every fault entry states its evidence type in prose (recall /
      bulletin / forum consensus / report)
- [x] No service interval figure stated unless cited from Triumph's own
      schedule — regex asserted
- [x] Shared-name trap covered: at least one entry names a model name
      that spans two engines
- [x] No 227/228/229 content; no DTC or tooling content (230);
      `dtc_codes: []`
- [x] Adapter catalog Triumph rows unchanged at 5; row 230 annotated
      with the air-cooled gap
- [x] Row 226 corrected (790 generation) if the research confirms it
- [x] Symptom needles quoted from shipped data; regression green; F9
      clean

## Risks

- **Fabricated faults are the hazard here**, more than duplication. The
  topic is empty, so nothing stops an invented "known issue" except the
  research gate and the evidence-type discipline.
- **Research agents can be confidently wrong**; two lenses and the
  `undecided` state are the mitigation.
- **No independent reader** of the final prose, as in 217–225.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 773 → 784 |
| Entries | 11 (10 `service-manual`, 1 `forum`) |
| Research agents / refuters / died | 4 / 8 / **0** |
| Findings survived / partially refuted | 2 / 2 |
| Content changed by refutation | 3 (engine-number rule scoped; commonality claim labelled; a missed recall added) |
| Guards re-scoped | 2 (both halves of Gate 2's forum-tip rule) |
| Phase tests | 44 |
| Backend regression | 5375 passed / 0 failed |

**This is the first Track K file that is not `model-generated`, and that
was the phase's most consequential decision.** Every earlier file carried
that provenance honestly, because it was written from training data.
These entries are not: they come from Triumph handbooks, the T120 service
manual, and recall records filed with national regulators. Marking them
`model-generated` would have understated provenance as surely as the
reverse would overstate it — and provenance accuracy is the entire reason
the `source` column exists.

**The vocabulary did not quite fit, which is worth recording.** The
CHECK-constrained set is `unverified / model-generated / forum /
service-manual / mechanic-verified`. There is no value for "official
regulator recall record". `service-manual` is the closest honest bucket,
and the precision it loses is carried in each entry's prose, which names
what it is drawn from. A future phase adding a `regulator` value would be
reasonable; inventing one here would have broken the constraint.

**Gate 2's rule was a denylist, and a denylist assumes the world stops
growing.** It excluded `model-generated` and treated everything else as
forum-derived. A third population makes it demand forum tips from
service-manual entries — fabricating exactly the provenance the column
exists to record. Both halves now key off the same allowlist. This is the
third time in six phases that a guard has been written as "everything
except X" and then broken by a Y.

**The refutations earned their cost.** Two of four findings came back
partially refuted, and all three corrections changed shipped content: a
790-vs-865 engine-number rule that would have sent someone to order the
wrong pistons was scoped to the one model it holds for; a "no parts
commonality" line was demoted from Triumph's advice to a disputed forum
claim; and a fire-risk recall the research had missed entirely was added
by a refuter searching for contradictions.

**Key finding: research does not only add facts, it removes them.** The
most valuable output of this phase's refuters was three claims that do
not appear in the shipped file.
