# Track K — European Brands — Closure Summary

**Status:** ✅ **Track K closed** at Phase 240 / Gate 12 on 2026-09-08.
**Phases:** 211 → 240, plus two substrate follow-ups (225B, 235B) — 32 phases including Gate 12.
**Known issues:** 660 → 917 at closure (+257, every one with a recorded provenance).
**DTC files:** 2 → 8 (BMW, Ducati, KTM, Triumph, Aprilia, MV Agusta added; each row earning its shadow over the generic table).
**Adapter catalogue:** KTM 4 → 18 rows, Triumph 5 → 22, Aprilia 0 → 15, MV Agusta 0 → 6; 34 adapters.
**Parts catalogue:** 62 → 125 rows, 83 → 100 cross-references; Aprilia, MV Agusta and Moto Guzzi from zero.
**Schema version at closure:** 52 (Track K added migrations 051 — `known_issues.source` — and 052 — the `regulation` value).
**Project version at closure:** 0.13.52.
**Regression at closure:** 5945 passed / 0 failed; Gate 12 46 tests.

MotoDiag opened Track K with 660 known issues that were overwhelmingly Japanese
and American, no record of where any of them came from, and a roadmap block
of thirty rows written from memory. It closes with 917 entries, a six-value
provenance vocabulary, six new fault-code tables, three catalogues extended
into makes that had nothing, and a working method — capped research,
adversarial refutation, and a test for every correction the refuters forced —
that the roadmap rows themselves were often the first casualty of. Eight
rows were corrected before content was written from them: an ECU supplier
that does not exist, a gate number already taken, a designation that was a
model and not a part, an interval difference that was two engines and not two
models.

## Phase inventory

| Phase | Title | Entries | Known issues | Key finding |
|------:|-------|--------:|-------------|-------------|
| 211 | BMW R-series boxer twin (1969+) | — | 660 → 672 | the honest label cost one migration, one parameter and a render function, and is what lets the remaining 29 phases proceed without pretendin |
| 212 | BMW GS adventure line | — | 672 → 684 | one drafting pass would have shipped a confidently wrong entry — what killed it was a second agent whose only job was to disbelieve the firs |
| 213 | BMW S1000RR / S1000R / S1000XR | — | 684 → 690 | in a saturated corpus, "specific enough to be worth adding" is a far harder bar than "true" — all twelve rejects were plausibly correct, jus |
| 214 | BMW K-series touring | — | 690 → 701 | a guardrail that is right for one platform is a liability on the next — rules from one phase must be re-derived against the next phase's har |
| 215 | BMW electrical + FI dealer mode | 3 | 701 → 704 | precedence turns "adds nothing" into "actively subtracts" — a property of any make→generic lookup. |
| 216 | Ducati Monster / Streetfighter (1993+) | — | 704 → 716 | a shared component name is not shared hardware — split the guardrail rather than relaxing it. |
| 217 | Ducati Panigale superbike line | 10 | 716 → 726 | a guardrail can be wrong against the very next phase in the same block, by the same manufacturer — and the checker needs as much scepticism  |
| 218 | Ducati Multistrada | — | 726 → 734 | guardrails can be conditional, and gates can decay by addition rather than by fault. |
| 219 | Ducati desmodromic valve service | — | 734 → 740 | a validator over prose must distinguish assertion from reference, and negation can arrive from either side. |
| 220 | Ducati electrical + FI | 5 | 740 → 745 | a guard should outlive the deliverable it was written for |
| 221 | KTM 1290 Super Duke / Super Adventure | 6 | 745 → 751 | a validator over prose must exempt reported speech, not just negation |
| 222 | KTM Duke naked line (125/390/690/790/890) | 5 | 751 → 756 | a validator over prose must exempt comparison, not just negation and reported speech |
| 223 | KTM enduro (EXC / EXC-F / 690 Enduro R) | 6 | 756 → 762 | a validator over prose must exempt quotation |
| 224 | KTM engine families (LC8 / LC8c / LC4) | 4 | 762 → 766 | a row can be structurally right while its stated content is already written — and not knowing a make-specific failure pattern is a result to |
| 225 | KTM electrical + engine management (Keihin / Bosch / Continental / Vitesco) | 7 | 766 → 773 | research changes what a phase can honestly say, in both directions |
| 225B | KTM mid-size Adventure (390 / 790 / 890 Adventure) | 10 | 855 → 865 | a model line can be invisible because of its name. |
| 226 | Triumph Bonneville / T100 / Speed Twin | 11 | 773 → 784 | provenance is a vocabulary problem as well as a discipline |
| 227 | Triumph Tiger adventure (1050/800/900/1200) | 11 | 784 → 795 | a refuter's most valuable output is a claim you then do not ship. |
| 228 | Triumph Street Triple / Speed Triple / Daytona | 11 | 795 → 806 | the value of research is measured in the claims it removes and the ones it corrects, not the ones it adds |
| 229 | Triumph vintage (pre-Hinckley Meriden + early Hinckley) | 13 | 806 → 819 | when a topic is saturated, the phase's job is to find the axis the corpus lacks |
| 230 | Triumph electrical + tooling (TuneECU / TuneBoy / DealerTool) | — | 819 → 824 | an inherited claim is not a verified one |
| 231 | Aprilia RSV4 / Tuono V4 | 8 | 824 → 832 | a clean recall search can be a data artefact |
| 232 | Aprilia Dorsoduro / Shiver / SR Max | 5 | 832 → 837 | an absence is only useful next to the presences |
| 233 | MV Agusta 3-cylinder (F3 / Brutale 675/800 / Turismo Veloce) | 5 | 837 → 842 | the obvious repair can be the wrong one, and only the campaign's own mechanism tells you. |
| 234 | MV Agusta 4-cylinder (F4 / Brutale 750–1078) | 5 | 842 → 847 | replacing an impression with specifics is a deliverable. |
| 235 | Aprilia + MV Agusta electrical, fault codes + dealer tools | 8 + 13 DTC rows + 21 compat rows | 847 → 855 | the make that looks readable is the dangerous one. |
| 235B | `regulation` provenance value for known_issues | — | schema 51 → 52 | a relabelling is a behaviour change unless you check the render path. |
| 236 | European electrical cross-platform | 13 | 865 → 878 | a cross-make claim built from a table’s summary fails at the table’s cells. |
| 237 | European common failure patterns | 15 | 878 → 893 | the refuters’ duplicate list is the most useful artefact this phase produced |
| 238 | European valve service intervals | 13 | 904 → 917 | the primary source may already be on disk. |
| 239 | European parts sourcing + pricing | 11 + 63 parts rows + 17 xrefs | 893 → 904 | a catalogue row fails at the fitment pattern, not the part number. |
| 240 | Gate 11 — European brand coverage integration test | — | 917 at closure | a gate’s dry run is where the gate’s own assumptions fail |

## Ten disciplines Track K developed

### 1. Provenance is a vocabulary problem before it is a discipline (211, 226, 235B)
Migration 051 gave every entry a CHECK-constrained `source`; Phase 226 was
the first to write `service-manual`; Phase 235 found the vocabulary had no
slot for a verbatim EU regulation and that `unverified` would drag it into
Gate 2’s forum-tip rule; 235B added `regulation` by table rebuild, and Gate 2
was re-scoped from a denylist to an allowlist along the way.

### 2. The backwards genericness test (213, 221, 229, 231, 237)
When a make is absent but its *topic* is saturated, every entry must name
make-specific hardware, with a corpus-wide counter-assertion that the existing
entries score zero. At 237 the refuters applied it themselves and named
nineteen of thirty-four proposed entries as duplicates, file and title.

### 3. Earning the shadow (215, 220, 235)
`dtc_repo` resolves make-specific before generic, so a make row that restates
the generic row *hides* it. Every shadowing row must differ in causes and fix.
At 235 the corollary became the finding: a make whose codes look standard and
are not (Aprilia, no P1xxx block) is more dangerous under a generic reader than
one whose codes are openly proprietary (MV Agusta) — silence is the safer
failure.

### 4. Mention versus use, a validator lineage (216–223, 230, 233, 237, 238)
A validator over prose must exempt negation, reported speech, comparison,
quotation, and the rider’s own symptoms; a mileage guard must distinguish an
interval from the mileage at which a part failed; a matcher must normalise
hyphens and stems. Fourteen false positives across the track, every one my
selector and never the content.

### 5. The constant-for-invariant bug (221, 222, 230, 235, 236, 237)
A guard that pins a count, a slug list, or a filename instead of asserting the
invariant breaks at the next phase and teaches nothing. Zero-guards were
inverted to "the gap is filled and the slug is spelled thus"; the European
cross-make exemption is by prefix, not by list.

### 6. Capped research, two refuter lenses, paired across siblings (227 onward)
After the user’s concern about unchecked long-running agents, every research
run is 2 questions × 2 adversarial lenses = 6 agents with progress check-ins.
Pairing sibling phases on one run halved the runs across the block. The
refuters’ record: a phantom recall number that was a Citroën campaign, a
regulator index that omits the affected model, a make filed as "APRILLA", a
do-not-ride recall whose obvious repair was the wrong one, a "could not be
obtained" source found on the very page cited, six manufacturer manuals found
unopened on disk.

### 7. No campaign reference numbers (231 onward)
A cited number belonged to another manufacturer. Entries describe a campaign’s
mechanism and remedy and route to the frame number, which cannot go stale and
cannot be wrong in that particular way. Gate 12 enforces it across every
European file.

### 8. A deliberate absence is a deliverable (224, 233, 234, 236, 238)
The MV F4 shim diameter, the Triumph connector transition year, the 2025 390
build location, MV’s crank direction, a currency-mangled conversion cost: each
is an entry that says what is not known, why, and what to do instead — because
a confident wrong number is worse than none.

### 9. The primary source may already be on disk (235, 238)
Two refuters disagreed on a count; the manual was in the scratchpad and settled
it at 19. A finding declared no same-engine interval pair differs; six MV
manuals a previous agent had downloaded and no one had opened held the one
that does.

### 10. Content cannot be pipelined across a phase boundary (231)
The Phase 208 doc-count guard ties documented figures to the live seed count —
a whole-tree invariant. Writing the next phase’s file into the tree while a
regression runs fails the guard correctly. Everything after 231 was staged in
the scratchpad and entered the tree only after the previous phase merged.

## Known limitations → seeds for later tracks

- **Moto Guzzi has no Track K row.** No DTC file, no compat rows, no make-file
  of its own; seven issues and nine parts rows from the cross-make phases
  only. Gate 12 records this as executable documentation.
- **MV Agusta F4 shim diameter** is in no manufacturer document (234, 238).
- **Aprilia 660-family valve interval** rests on aggregators only (238);
  Aprilia’s own maintenance sheets omit the valve row.
- **MV three- versus four-cylinder tool coverage parity** is unconfirmed by any
  source (235, 236); OBDSTAR publishes per-model coverage only as downloads.
- **Triumph’s connector transition year** and **the 2025 390 platform’s build
  location** are deliberately unprinted (236, 225B).
- **One duplicated cross-reference pair in the Phase 153 parts seed** is
  detected by 239’s test and left as data.
- **The KTM 690 / Duke rocker-arm and several 237 differentials** rest on owner
  reports, labelled `forum`; a `mechanic-verified` pass would upgrade them.
- **Pushes are classifier-blocked** from this environment; `master` is ahead
  of `origin/master` by every Track K commit since 235.

## Track K opens for Track L

Track L (241–250) is electric: HV safety and lockout, Zero, LiveWire,
Energica, Damon, BMS and inverter diagnostics, thermal management. It inherits
a provenance vocabulary with a slot for regulation — HV work is regulated
work — a research cadence that catches phantom sources, and a corpus whose
gates now assert their own invariants.
