# Phase 244V — The reference data a technician asks for mid-job

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-17

---

## Goal

Phase 244U's fixed gate exposed 20 orphans, and 17 of them are one thing: a
reference layer nobody can reach. 20 torque specs, 8 valve clearances, 14
service intervals and 5 wiring circuit references — complete, tested, and
reachable from no command or route since Phase 92/93 shipped them in April.

The wiring data in particular is the kind of thing a technician keeps a
workshop manual open for: the three yellow stator leads and what they should
read at 5000 RPM, the safety-switch chain that has to be complete before the
starter relay will click, "tap the starter relay while pressing start — if it
cranks, the relay contacts are bad", "clean the ABS sensor tip at every tire
change; 90% of ABS faults are contamination".

## Step 0 — findings

**S0-1. The data is authored, generic, and says so.** The module's own
docstring reads *"These are generic/typical values — always verify against the
model-specific service manual for exact specs"*, and Phase 93's doc repeats
it. The values are plausible and carry their own warnings ("Replace aluminium
crush washer every change. NEVER over-torque — strips aluminium cases").

**S0-2. It came from the same wave as the fabricated recalls** (commit
`3b38ca6`, Track F). That is a reason to be careful, not a reason to stop: no
value here impersonates an official identifier the way `nhtsa_id` did, and a
generic torque for an M12 drain plug is a real category. **But it is authored
reference data, so every output has to say so where the number is read** —
not only in a docstring nobody sees.

**S0-3. Torque is the safety-relevant one.** An under-torqued caliper bolt is
a brake failure and an over-torqued one strips an aluminium case. The caveat
is not boilerplate here; it is the honest scope of what this data can answer.

**S0-4. The lookups are partial-match and the tables are small.** Each
`get_*` takes a string and matches case-insensitively; there are
`list_all_torque_specs` and `list_all_service_intervals` already, and
`CIRCUIT_REFERENCES` is a list of five. No new data, no schema, no AI.

**S0-5. Wiring these will make allowlist entries stale**, which is the gate
working in its second direction. Phase 244U classified them one day earlier;
this phase removes the ones that gain a caller.

## Scope

1. **A `motodiag ref` command group**, registered like every other group:
   - `ref torque [QUERY]` — a named fastener, or the whole table
   - `ref valve [QUERY]` — clearances by component or engine layout
   - `ref interval [QUERY]` — service intervals
   - `ref circuit [NAME]` / `--system electrical` — the wiring reference,
     rendered with wire colours, expected readings, test points, common
     failures and diagnostic tips
2. **Provenance on every screen.** A single constant, rendered under every
   result: these are generic values, authored for this project, to be
   verified against the model-specific manual. Torque output additionally
   leads with it, because that is where a wrong number does harm.
3. **A miss says what exists.** An unmatched query lists the available names
   rather than printing nothing — the failure mode 244R fixed for
   `--category`.
4. **The allowlist loses the entries that gain callers**, and the gate proves
   it by failing in the stale direction if they are left behind.
5. **Tests through the commands**, including the provenance line, a miss, and
   a spot-check that a rendered value matches the table.

## Non-goals

- **No API routes and no app surface.** Same reasoning as 244T: a contract
  change that Gate 11 pins deserves its own phase, and the CLI is where a
  technician with a bike on the lift already is.
- **No new reference data**, per-model or otherwise. Roadmap rows 297 and 301
  are where that belongs, and it needs manufacturer sources.
- **No prompt injection.** `build_service_data_context` and
  `build_wiring_context` stay unwired: feeding generic numbers into a
  diagnosis invites the model to state them as specific, which is the
  laundering problem this project already fixed once for vision findings.

## Verification Checklist

- [ ] `ref torque "drain plug"` prints the spec in Nm and ft-lb with its note
- [ ] `ref torque` with no query lists the table
- [ ] Every torque screen carries the verify-against-the-manual line
- [ ] `ref valve`, `ref interval` and `ref circuit` each carry provenance too
- [ ] `ref circuit charging` shows wire colours, expected readings, test points, failures and tips
- [ ] `ref circuit --system electrical` lists the circuits in that system
- [ ] A miss lists what exists instead of printing nothing
- [ ] `build_service_data_context` and `build_wiring_context` remain unwired, with a test saying why
- [ ] The allowlist no longer lists the functions that now have callers, and the gate agrees
- [ ] Mutations: drop the provenance line; make a miss silent; swap a rendered value; leave a stale allowlist entry — each caught
- [x] Full regression green — **6,961 passed, 0 failed, 27:37**

---

## Results (v1.1)

**Built as planned, with one change of approach and one rendering bug that
only a run could have found.**

`src/motodiag/cli/reference.py` registers a `ref` group on the root CLI with
four commands. Each takes an optional query and falls back to the whole table:

```
motodiag ref torque "drain plug"     motodiag ref circuit charging
motodiag ref valve inline-4          motodiag ref circuit --system electrical
motodiag ref interval "brake fluid"
```

### What the commands render

`ref circuit charging` is the one worth naming, because it is what the phase
was for. It prints the circuit's description, then a wire table — colour,
function, connector location, expected reading ("50-80V AC at 5000 RPM (per
pair)", "<0.5 ohm to battery negative") — then test points, common failures
and diagnostic tips. Four screens of a workshop manual that were sitting in a
Python list nothing imported.

### Provenance

One constant, `PROVENANCE`, rendered under every successful screen, and a
parametrised test asserts it on **all nine** of them rather than a
representative sample — the one that forgets is the one someone torques a
caliper bolt from. Torque additionally leads with a panel naming both failure
directions, and a test pins that the warning appears *above* the first number:
a footer under twenty rows is not read at the moment the number is.

Six negative assertions were added alongside it. Saying the right thing is
half of provenance; the screen must also not say "official", "OEM", "factory
spec" or "per the manufacturer" anywhere.

### Deviation 1 — the full tables are built through `list_all_*`

The plan said the `list_all_torque_specs` / `list_all_service_intervals` /
`list_all_circuits` accessors existed. They did, on the allowlist as
`public-api` orphans. Building each table by listing names and looking each
one up — rather than iterating the raw dicts — costs nothing at this size and
gives those three functions a real caller, so **eight** allowlist entries
were removed rather than the five the plan implied. The clearance table has no
lister of its own (Phases 92/93 gave one to the other three and skipped it);
adding a fourth would have been growing the module this phase exists to wire,
so the constant is read directly, with a comment saying why.

### Deviation 2 — rich ate the system label

`title=f"{circuit.circuit_name}  [{circuit.system}]"` renders as
`Charging circuit — stator to battery` and nothing else: rich reads
`[electrical]` as a markup tag and silently drops it. Caught in the first
smoke run, not by review. Parentheses now, and a test asserts `(electrical)`
survives rendering.

### The gate, in both directions

Removing the eight entries left `test_phase209B_integration_gaps.py` green,
which is the stale direction doing its job — had any of the eight still lacked
a caller, the new-entry test would have failed instead. Two of 244U's own
scale pins moved and were rewritten rather than deleted:

- `test_the_orphan_list_grew_by_exactly_twenty` → `..._is_the_running_count`,
  now recording 46 → 66 → **58** so the trend is legible.
- The engine-layer test asserted `>= 17`; it is now `0 < n <= 15`, a ceiling
  instead of a floor. A phase that wires more of the layer passes; one that
  adds unreachable engine capability fails. The layer is still there — cost
  estimation, parts recommendation, repair-procedure generation.

### What stayed unwired, deliberately

`build_service_data_context` and `build_wiring_context` remain on the
allowlist, with a documenting test naming them. Feeding "typical Japanese rear
axle nut: 100 Nm" into a prompt about a specific bike invites the model to
state it as that bike's figure, which is the laundering problem this project
fixed once already. Delete that test when a phase wires them *with* a way for
the answer to say which numbers are generic.

No API or app surface, per the non-goal, and a test greps `src/motodiag/api`
to keep it that way — a route would need a Gate 11 snapshot refresh and
regenerated mobile types.

### Verification

- 55 tests, all through the CLI. **11/11 mutations killed**, including: drop
  the provenance line; make a miss silent; make a miss exit 0; print an empty
  table instead of the vocabulary; render `0 miles` as `0`; restore the
  bracket that rich swallows; drop the cold-spec note; render wires only; drop
  the `--system` filter; never register the group.
- `ruff` clean on both new files; no new findings in the files touched.
- No schema change, no migration, no data authored.
- Full regression **6,961 passed, 0 failed, 27:37** (6,914 → 6,961: +55 new, -8 net from the two 244U pins being rewritten rather than added to).

## Verification Checklist

- [x] `ref torque "drain plug"` prints the spec in Nm and ft-lb with its note
- [x] `ref torque` with no query lists the table
- [x] Every torque screen carries the verify-against-the-manual line
- [x] `ref valve`, `ref interval` and `ref circuit` each carry provenance too
- [x] `ref circuit charging` shows wire colours, expected readings, test points, failures and tips
- [x] `ref circuit --system electrical` lists the circuits in that system
- [x] A miss lists what exists instead of printing nothing
- [x] `build_service_data_context` and `build_wiring_context` remain unwired, with a test saying why
- [x] The allowlist no longer lists the functions that now have callers, and the gate agrees
- [x] Mutations: drop the provenance line; make a miss silent; swap a rendered value; leave a stale allowlist entry — each caught
- [x] Full regression green — **6,961 passed, 0 failed, 27:37**
