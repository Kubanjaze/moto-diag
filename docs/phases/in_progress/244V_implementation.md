# Phase 244V — The reference data a technician asks for mid-job

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-17

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
- [ ] Full regression green
