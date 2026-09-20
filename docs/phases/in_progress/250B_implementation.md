# Phase 250B — The electric layers never reach the model

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-19

---

## Goal

Row 250B, opened by Gate 13 with the measurement in hand: four phases and
26 rows of BMS, inverter, regen and thermal content do not reach a
diagnosis on any electric make. Make the prompt carry what the rider's
complaint points at, without starving the safety floor Phase 241 put first
on purpose. Second, smaller item in the same area: the garage cannot show
an electric bike's motor power (F95).

Gate 13's `TestTheDiagnosticPathAsItIs` and its garage test are the
acceptance criteria. They are written to fail when this lands; this phase
updates them to the new measured truth in the same commit.

## Step 0 — findings

Measured on a freshly seeded database (996 rows) on 2026-09-19.

**S0-1. Today, per Gate 13.** Zero SR/F and LiveWire ONE reach the
controller layer only; Energica Ego and Harley-Davidson LiveWire reach
none of the four. Every prompt is filled to its twelve-row cap and the
twelve do not change when the symptom does.

**S0-2. Raising the cap is not the fix.** Rank of the first row of each
layer in today's order:

| Query | bms | inverter | regen | thermal | cap needed | prompt then |
|---|---|---|---|---|---|---|
| Zero SR/F | 21 | 8 | 23 | 26 | 27 | 24,666 ch |
| Energica Ego | 23 | 21 | 25 | 26 | 27 | 24,067 ch |
| LiveWire ONE | 18 | 2 | 20 | 22 | 23 | 21,168 ch |
| Harley-Davidson LiveWire | 76 | 28 | 94 | 15 | **95** | **68,434 ch** |

A cap that fixes the Zero costs 2.4× the prompt; one that fixes the Harley
costs 8.5×, three times over in the interactive flow. The 12 was chosen as
a cost decision at 244S and stands.

**S0-3. The Harley-Davidson LiveWire case is not a ranking problem at
all.** Its model does not resolve, so every row it gets is tier
`make_wide` — generic V-twin content. The twelve rows sent for a
battery-electric motorcycle are stator failure, compensator sprocket
noise, intake manifold seal leak, starter solenoid, clutch pack wear and
the like: an engine, a clutch and a stator the machine does not have. The
root cause is one level down (S0-9), but a powertrain-aware selection
fixes the symptom without waiting for it.

**S0-4. A powertrain filter is most of the fix.** Keeping only rows whose
make names an electric marque: Zero 53 → 52, Energica 43 → 42, LiveWire
ONE 46 → 45, **Harley-Davidson LiveWire 165 → 45** — the Harley collapses
onto the LiveWire ONE's own profile. This is the missing powertrain filter
Phase 243 recorded as debt; four phases have now been shaped by it.

**S0-5. It is a no-op for combustion bikes, measured.** Of the twelve rows
sent today for a Sportster 1200, CBR600RR, MT07, SV650 and R1250GS, **zero**
are HV-safety or electric-make rows — tiering already keeps them out. 241's
accepted over-inclusion exists in the retrieval set, not in the prompt.

**S0-6. Composition beats enlargement, at the same cost.** Eight rows by
today's ranking plus four reserved slots, after the powertrain filter:

| Query | layers today | layers composed | critical today | critical composed | prompt |
|---|---|---|---|---|---|
| Zero SR/F | inverter | all four | 9 | 9 | 10,445 → 11,132 ch |
| Energica Ego | none | all four | 5 | 5 | 10,099 → 11,265 ch |
| LiveWire ONE | inverter | all four | 7 | 7 | 10,949 → 10,156 ch |
| HD LiveWire | none | all four | 3 | **7** | 8,069 → 10,156 ch |

The safety floor holds everywhere and improves on the Harley, because
combustion content stops crowding it out.

**S0-7. Reserving by *relevance* beats reserving by a fixed layer list.**
Scoring candidates on token overlap with the reported symptoms and giving
the reserved slots to the best matches, measured on a Zero SR/F and a
Harley-Davidson LiveWire:

| Reported | Layers that arrive |
|---|---|
| "range dropped by half" | bms, thermal (+ inverter on the Harley) |
| "pack overheats while charging" | bms, thermal |
| "brake light does not come on under regen" | regen, inverter |
| "motor controller fault code" | inverter, thermal |

A fixed list would always send all four and answer the rider's question by
accident. Relevance is also a general rule rather than an electric one,
which matters because every other track will want it.

**S0-8. What constrains the change.** `known_issues_for_vehicle` has two
production callers and is directly exercised by the 244C, 244E, 244F and
244I suites, three of which read its **source text** (the severity-SSOT
guard, the junction-fallback guard with indentation-exact matching, and
244C's "no marque name hard-coded here" guard). The diagnose path is
exercised only by 244S, 123 and Gate 13. A change confined to
`_load_known_issues` therefore has a fraction of the blast radius.

244S pins four things a naive composition would break: the tier sequence
must stay non-decreasing (`model → make_wide → make_other_model`); the
result must be **exactly** full at the cap; at least one tier-0 and one
tier-2 row must survive, because the prompt must still say "same make,
DIFFERENT model"; and a specific near-neighbour row must not be dropped.

**S0-9. The deeper cause, which is not this row's.** The model-resolution
pool is keyed by the raw `known_issues.make` column, so a row reading
"Zero, Harley-Davidson, LiveWire, Energica" files its models under that
whole string. `known_models("LiveWire")` returns **0** against 23 junction
models; Damon 0 against 10; Harley-Davidson 13 against 36; Zero 14 against
32; Triumph 82 against 104; BMW 51 against 74. Ten of sixteen marques are
partial, two cannot resolve a model at all, and six vocabulary keys are
not marques — one is a prose sentence holding three models. This is the
defect 244F fixed for makes and 244I fixed for model *values*, one level
down in the *keys*. Operator decision, 2026-09-19: **it opens as row
250C**, because it changes resolution for all sixteen marques and Track
K's makes are affected as much as Track L's.

**S0-10. F95 is small and well-founded.** Phase 110 already models,
validates and persists `motor_kw`, and the API's vehicle routes accept it.
Only two things are missing: `garage add` has no `--motor-kw` option, and
the list renderer reads `v.get('motor_kw', '?')`, whose default never
fires for a key that exists holding `None`. `battery_chemistry` and
`bms_present` have the same CLI gap and are **not** in scope here.

**S0-11. `/ask` has its own path and its own cap.** `videos.py` calls the
resolver with `limit=25`, discards the identity, applies no year filter,
and the vision formatter then slices to `[:12]` with its own hard-coded
number. Changing `_load_known_issues` does not touch it. Filed rather than
fixed.

## Decisions

**D1. The change lives in the diagnose path, not the resolver.**
`_load_known_issues` composes; `known_issues_for_vehicle` keeps returning
what it returns today. This keeps the four resolver suites and their three
source-text guards out of the blast radius (S0-8).

**D2. Reserve by relevance to what the rider reported, not by a fixed
layer list.** S0-7. The rule is general; the electric layers are the case
that exposed it.

**D3. Compose, then re-sort by the canonical key.** The chosen rows are
re-ordered by `(match_tier, severity rank, title)` before they reach the
prompt, so 244S's monotonicity assertions still hold and the model still
sees the most specific rows first.

**D4. Powertrain knowledge does not go in `marques.py` or
`vehicle_resolver.py`.** 244C guards those two modules against a
hard-coded marque name, and rightly. A new `knowledge/powertrain.py`
classifies a corpus row's powertrain relevance, deriving what it can and
naming the battery-electric-only marques in one place.

**D5. The cap stays 12.** S0-2 and S0-6: composition delivers the layers
at today's size, so there is no cost case for raising it.

## Scope

1. `knowledge/powertrain.py` — classify a row as electric-relevant,
   combustion-relevant or both, from the marques and models it names.
2. `cli/diagnose.py` — `_load_known_issues` gains optional `powertrain`
   and `symptoms`; with neither it behaves exactly as today. Filter,
   reserve by relevance, re-sort, cap. Call sites in `_run_quick`,
   `_run_interactive` and `code.py` pass what they already hold.
3. `cli/main.py` — `garage add --motor-kw`, and the renderer's fallback.
4. Gate 13's six diagnostic tests and its garage test, updated to the new
   measured truth in the same commit.
5. New tests: the composition rules (relevance, re-sort, exact fill, tier
   coverage), the ICE no-op on five combustion bikes, and the garage
   round-trip.

## Non-goals

- **No resolver change and no SQL change.** The vocabulary keying is 250C.
- **No `/ask` change** (S0-11), no FTS, no scoring framework — token
  overlap, the shape `predictor.py` already uses.
- **No cap change**, no new severity ordering, no corpus edits.

## Verification Checklist

- [ ] Gate 13's tripwires updated, and each one's new assertion measured
- [ ] The ICE no-op proved on five combustion bikes
- [ ] 244S's four pins still green, tier monotonicity included
- [ ] The new test file scanned by 244G's raw-source guard
- [ ] Mutations caught
- [ ] Full regression green, 0 failed and 0 skipped
- [ ] Row 250C opened with S0-9's measurement; F100/F101 filed
- [ ] Roadmap row 250B, `implementation.md` history row, `phase_log.md`
