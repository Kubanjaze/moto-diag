# Phase 250 — Gate 13: the electric track through the real front doors

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-19

---

## Goal

Row 250: "Gate 13 — Electric motorcycle integration test. Query electric
bike → BMS/motor/regen/thermal analysis end-to-end." Track L's closing
gate, in the house style Gates 8, 9, 11 and 12 set: every query goes
through the **real** CLI root or the HTTP API and never the repository
layer; a class of executable documentation records what the corpus
honestly lacks and is meant to fail the day someone fills it; and a gate
guards the gates before it.

The row names a path, so the gate's first duty is to walk that path and
report what a technician actually gets. Step 0 walked it. The answer is
that the path does not deliver what the row promises, and the measurement
below is the reason this gate exists.

## Step 0 — findings

Measured against a copy of the live database (996 rows) through the real
CLI entry point and a `TestClient` app, on 2026-09-19.

**S0-1. Track L shipped 79 rows across eight files.** `electric_hv_safety`
10 (all `model-generated`), `zero` 17 (16 service-manual, 1 forum),
`livewire` 14 (11/3), `energica` 12 (10/2), `bms` 7 (5/2), `inverter` 8
(5 service-manual, 2 regulation, 1 forum), `regen` 7 (6/1), `thermal` 4
(all service-manual). Phase 245 (Damon) shipped none and is ⏸️, not ✅.
The corpus chain the phase docs claim — 917 → 927 → 944 → 958 → 970 →
977 → 985 → 992 → 996 — matches the live count of 996.

**S0-2. The row's own path does not carry the row's own content.** A
diagnostic query retrieves by vehicle through the junction
(`known_issues_for_vehicle`, fetch 200), filters by year, and caps at
`KNOWN_ISSUE_PROMPT_LIMIT = 12`. Retrieval is **symptom-blind**: the same
twelve rows reach the model whether the rider reports lost range, a hot
pack or a dead regen brake light. Since 240C orders critical first, 241's
ten critical HV-safety rows fill the cap:

| Query | Layers reaching the prompt | Available to it |
|---|---|---|
| Zero SR/F 2023 | inverter only (3) | bms 4, inverter 11, regen 7, thermal 4 |
| Energica Ego 2022 | **none** | bms 3, inverter 6, regen 6, thermal 4 |
| LiveWire One 2022 | inverter only (2) | bms 3, inverter 7, regen 6, thermal 6 |
| Harley-Davidson LiveWire 2021 | **none** | bms 4, inverter 7, regen 7, thermal 12 |

Four phases (246–249, 26 rows) were written so that a diagnosis carries
BMS, controller, regen and thermal analysis. For two of the four pairs
above, none of it arrives; for the other two, only the controller layer
does. The Harley-Davidson query is worse than empty: 165 rows are in
scope and the twelve chosen are combustion content, because the knowledge
search still has no powertrain filter — the debt Phase 243 recorded and
the third phase to be shaped by it.

**S0-3. The two code paths disagree for every electric code.** `kb by-code
P0A05` and `kb by-code P1040` reach Phase 249's cooling-fault row (id
4565) because `find_issues_by_dtc` LIKEs `known_issues.dtc_codes`.
`motodiag code P0A05` — the command a technician reaches for first —
answers "⚠ No DB entry — heuristic classification only" and
"P0A05 — unrecognized code format", Category `unknown`, Severity
`UNKNOWN`. Two causes, both real: no electric make has a file under
`seed/dtc_codes/` (only aprilia, bmw, ducati, generic, harley_davidson,
ktm, mv_agusta, triumph), and `classify_code` has no branch for the SAE
hybrid/EV block, so `^P[0-9]{4}$` never matches a code with a hex letter
in the third position. Phase 244 recorded that hazard for a later phase;
this is the phase that measures it. `generic.json` holds 35 codes and
none in P0A/P0B/P0C/P0D. The categories `hv_battery`, `inverter`, `regen`,
`thermal` and `charging_port` each exist in `dtc_category_meta` with **0**
codes — F90, still open.

**S0-4. No adapter compatibility row exists for any electric make.**
`compat_matrix.json` holds 167 rows over eleven makes — aprilia, bmw,
ducati, harley, honda, kawasaki, ktm, mv-agusta, suzuki, triumph, yamaha.
`hardware compat recommend --make Zero --model SR/F` answers "No compat
entries known for this bike", as do Energica Ego, LiveWire One and
Harley-Davidson LiveWire. Gate 12 could assert an adapter per European
make; Gate 13 cannot, and says so. Note the slug conventions differ: the
compat store keys `harley`, the corpus says `Harley-Davidson`.

**S0-5. The CLI resolves a make; the API does not.** `kb list --make`
runs the resolver and prints its correction, then filters `make LIKE`.
`GET /v1/kb/issues?make=` does no resolution at all. The asymmetry is
invisible for electric makes only because SQLite's `LIKE` is
case-insensitive.

**S0-6. Damon is present as a make and absent as content.** Ten junction
rows name Damon, every one of them `model-generated` and inherited from
241's HV file; there is no Damon seed file, and 245 is paused because no
customer unit has been delivered, no manual exists and NHTSA holds no
Damon vehicle. Same shape as Moto Guzzi in Gate 12: covered only by the
cross-make phases.

**S0-7. Model strings collide across makes.** `known_issue_models` holds
`SR` (Zero) beside `SR400` (Yamaha) and `SRV 850` (Aprilia). Whatever the
gate asserts about model filtering must prove the makes do not cross.

**S0-8. Provenance of the whole corpus, for the gate's regression
class.** 996 rows: `unverified` 660, `service-manual` 157,
`model-generated` 149, `forum` 27, `regulation` 3. Track L's own rows are
anchored; the bulk of the older corpus is not. The six-value vocabulary
Gate 12 pinned still holds.

**S0-9. F93's wording debt is 24 occurrences.** "2018 Eva" appears twice
in `known_issues_bms.json`, ten times in `known_issues_inverter.json` and
twelve times in `known_issues_regen.json` — the anchor Phase 249 replaced
with the document code in its own rows. `known_issues_thermal.json` and
`known_issues_energica.json` carry none.

## Decisions

**D1. The gate reports; it does not repair.** Zero production code, as in
Gates 9, 11 and 12. S0-2 is a retrieval defect, not a corpus defect, and
fixing retrieval inside a gate would put an untested change to every
make's diagnosis inside a phase whose purpose is to measure. The
measurement ships as executable documentation and the fix opens as **row
250B** immediately after this row closes — the pattern 240B and 240C set
after Gate 12. Operator decision, 2026-09-19.

**D2. Absences are asserted, not assumed.** Every honest-gap test pins a
*measured* absence with the measurement in its docstring, and is written
so that it fails the day the absence is filled. A test that would still
pass after someone fixed the gap is not documentation, it is decoration.

**D3. The prompt is a front door.** Gates 8–12 walk the CLI and the API.
Row 250's path ends at the model, so the gate walks to the prompt through
the real Click command with an injected diagnose function, and asserts on
what `build_knowledge_context` produced — never by calling the retrieval
helper directly. No API key, no network.

**D4. Track L's invariants are re-run here, not restated.** The gate
asserts the properties the nine phases claimed — six-value provenance, one
row one label, a forum row names its site and page date, a regulation row
names its NHTSA campaign number, every listed code is named in the row's
text, every make a row names resolves through the junction — against the
live seed rather than against each phase's own fixtures.

## Scope

One new test file, `tests/test_phase250_gate13.py`, with a module-scoped
fixture that stands up a fully seeded database the way `db init` does
(DTCs → symptoms → every `known_issues_*.json` in sorted order → make
index → model index), plus the adapter catalogue through the real
`hardware compat seed`. Classes:

1. **TestEveryElectricMakeAnswersThroughTheCli** — `kb list --make` for
   Zero, Energica, LiveWire, Harley-Davidson and Damon; the label shows
   beside every row; critical-first ordering holds on a safety file;
   241's HV floor returns together with each make's own file.
2. **TestTheFourLayersAreReachableByTheCommandsPeopleUse** — the search
   terms 246–249 pinned (`balancing`, `state of health`, `derating`,
   `inverter`, `motor controller`, `firmware`, `regen`, `brake light`,
   `coast`, `cooling`, `motor temperature`, `ambient`) each return their
   row with its label; `kb by-code` reaches the nine Energica cooling
   codes; `kb by-symptom` reaches the layers.
3. **TestTheDiagnosticPathAsItIs** — S0-2, pinned. The four make/model
   pairs, the layer census of the twelve rows that reach the prompt, and
   the fact that the census does not change when the symptom does. Each
   test names row 250B in its docstring and is meant to fail when 250B
   lands.
4. **TestCrossSurfaceAgreement** — the same query through `kb search` and
   `GET /v1/kb/search`, and `kb list --make` against
   `GET /v1/kb/issues?make=`, with a throwaway API key created in-process
   and revoked by id; S0-5's asymmetry pinned.
5. **TestTheHonestGaps** — no `dtc_codes` file for any electric make; the
   five empty categories; `code P0A05` classifying as unknown; no adapter
   row for any electric make; Damon present-as-make and absent-as-content;
   no regen fault code anywhere in the corpus; no row claiming a
   liquid-cooled battery; F93's 24 occurrences.
6. **TestTrackLCorpusInvariants** — D4's list, plus the identity
   (make, model, title) uniqueness and the 996-row documented count.
7. **TestRegression** — Gates 8, 9, 11 and 12 still pass; `SCHEMA_VERSION`
   pinned at 62.

## Non-goals

- **No production code.** No retrieval change, no classifier branch for
  the hybrid/EV block, no DTC seeding (F90), no adapter rows for electric
  makes. Each is named in a test and left to its own row.
- **No new corpus content.** The gate writes no `known_issues` row and
  corrects none; F93's wording debt is pinned, not paid.
- **No network, no LLM key, no live database.** The fixture builds its own
  from the packaged seed.

## Verification Checklist

- [ ] The new test file scanned by 244G's raw-source guard before the regression
- [ ] Every honest-gap test fails when its absence is filled (proved by mutation)
- [ ] Mutations caught
- [ ] Full regression green, 0 failed and 0 skipped
- [ ] Roadmap row 250 updated; row 250B opened with S0-2's measurement
- [ ] `implementation.md` history row and `phase_log.md` entry
