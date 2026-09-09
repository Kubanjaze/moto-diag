# Phase 237 — European failure patterns, as differential diagnosis by make

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-08

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

_(v1.1)_
