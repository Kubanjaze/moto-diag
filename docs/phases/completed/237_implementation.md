# Phase 237 — European failure patterns, as differential diagnosis by make

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

For a given presenting symptom, say what a mechanic checks *first* depending
on which European make is on the bench — and why the answer differs. The
value is in the differences; the commonality is already written.

Guard: `pytest tests/test_phase237_european_differentials.py`.
Outputs: `known_issues_european_differentials.json`, its test, roadmap row 237.

## Existing-code audit (Step 0)

**1. The row's ground was already covered three times over.** Row 237 names
"voltage regulator (BMW hexhead), stator (Ducati), cam chain (Triumph)".
Across the corpus, `stator` appears in 57 files, `rectifier` in 47, `cam
chain` in 39. A generic `cross_platform_charging` file already covers stator
winding failure, shunt-vs-MOSFET regulators, connector melting and rotor
magnet degradation; `cross_platform_ignition` covers the rest. Twenty-six
European make-files then cover each make's own instances.

**2. The row therefore had to be reframed, not written.** As at Phase 234,
where an impression was replaced with specifics. The only uncovered axis is
the *differential*: same symptom, different make, different first check.
The research was told this explicitly and given the saturated topics by
name.

**3. The refuters were told to score genericness, and they did.** Of 34
proposed entries, **19 were flagged** as either restating the two generic
files or duplicating an existing European make-file — with the specific
file and title named in each case. The row is smaller than it was planned to
be, and that is the honest outcome rather than a shortfall.

**4. This phase ships from the surviving fifteen**, after applying the
source-quality refuter's seven defects — see Results.

## Method

Paired capped 6-agent run with Phase 236. This phase's question was refuted
on **genericness** (19 of 34); Phase 236's on contradiction. Two different
failure modes from one run, which is what two lenses are for.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 878 → 893 |
| Entries | 15 — 12 `forum` (all with tips), 3 `model-generated` |
| Proposed by research | 34 |
| Flagged duplicate or generic by refuters | 19 — each with the existing file and title named |
| Source-quality defects applied | 7 |
| Phase tests | 25 |
| Backend regression | 5846 passed / 0 failed |

**The row shrank by more than half, and that is the finding.** Row 237 named
"voltage regulator (BMW hexhead), stator (Ducati), cam chain (Triumph)" —
topics in 12, 57 and 39 files respectively, plus a generic charging file that
already covers the causal chain and the remedy list. The refuters were told
to score genericness and named nineteen duplicates down to the file and
title: the oilhead Hall-sensor pigtail is already in the BMW R-series file,
the coupled desmo clearances in the Ducati desmo file, the dry-clutch rattle
in the Monster file, the Aprilia flywheel "recall kit" in the RSV4 file, the
stator-connector chain in the generic charging file. Writing them again would
have shadowed each. Fifteen survive, and each is a *differential* — same
symptom, this make, this first check, and why a Japanese-trained routine
gets it wrong.

**Two corrections changed shipped content.** "SE-R" in the KTM source is the
**950 Super Enduro R**, a model — the research had read it as a regulator
type and scoped the overcharging failure to every 950 and 990. The entry now
covers one machine, and carries the mechanism the research dropped: the
under-seat whistle is battery acid boiling off through the safety valve, and
the source blames the regulator's location beside the rear exhaust header.
The KTM water-pump entry's distinguishing hook — a weep hole present in
2009–10 and deleted for 2011, so the first symptom changes by year — was
attributed to a page in which the word "weep" occurs zero times. It is gone;
the entry says only what the source supports and prints no interval, since
the source is a compilation rather than a KTM document.

**One figure removed for currency.** The Moto Guzzi 8V conversion cost in
circulation is a New Zealand dollar figure the research rendered as US
dollars. No figure ships; the entry says why, and adds the fact the source
does give — the manufacturer covered the conversion where full dealer
service history existed.

**Three entries lacked an explicit order and the test sent them back.** A
differential is a claim about what to do *first*; three fix procedures
implied an order without stating it. Made explicit, which improved each.

**Five copies of the same guard, not two.** Phases 227, 228, 231, 232 and 233
each hold a designation-bar test forbidding their make's model names outside
their own file. I had fixed 233's by name at 236; 228 and 231 fired here, and
a sweep found 227 and 232 waiting to fire at 238/239. All exempt the
`european_` prefix now, as an invariant. This is the Phase 235 audit lesson
— an identifier-keyed search finds one phase's habits — repeated, and the
sweep this time found two failures before they happened.

**Key finding: the refuters' duplicate list is the most useful artefact this
phase produced.** Nineteen named pairs of "proposed entry → existing entry"
is a map of what the corpus already knows, produced by an adversary with no
stake in the phase's size.
