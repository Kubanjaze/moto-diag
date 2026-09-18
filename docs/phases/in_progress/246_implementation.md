# Phase 246 — BMS diagnostics: the generic layer, anchored per make

**Version:** 0.9 — DRAFT FOR OPERATOR REVIEW before any content is authored | **Tier:** Standard | **Date:** 2026-09-18

---

## Why this stops at the plan

This is the first roadmap row since the 244 series that *authors corpus
content*. Every lesson that series paid for — F86's fabricated campaign
numbers, CORR-001's coolant jacket on an air-cooled twin, `repair.py`'s
invented torque figures — was authored content that read as sourced. A
sourced BMS corpus is a design change the operator should see before it is
built. Step 0 is done; the scope below is a proposal.

## Goal

Row 246: "Cell balancing, SOH (state of health), voltage curves, thermal
derating, cycle counting." Phase 242 drew the boundary in its own risk
register — *"a Zero BMS fault pattern is in scope; how BMS cell balancing
works is not"* — and 243 and 244 repeated it: 246, 247 and 249 own the generic
BMS, inverter and thermal layers. This phase writes the generic BMS layer:
what cell balancing is and when it happens, what SOH means and how each make
exposes it, what the voltage curve looks like and why a technician cares,
what thermal derating does to available power, and what cycle counting
tracks — **each entry anchored to a manufacturer document for at least one
make**, or not written.

## Step 0 — findings

**S0-1. What exists.** Nine BMS-adjacent make-specific rows across the three
EV seed files — `known_issues_zero.json` (17 rows, 16 `service-manual`, 5
BMS-ish), `known_issues_livewire.json` (14, 11 `service-manual`, 2),
`known_issues_energica.json` (12, 10 `service-manual`, 2) — plus 241's HV
floor (10, `model-generated`). Zero generic entries: nothing says what cell
balancing *is*. `dtc_codes` has ten categories, all combustion-shaped
(`engine` 48 … `abs` 2); no `battery`/`hv` category; **zero seeded DTCs**
use the `^(HV|MC|BMS|INV|CHG|REG)_` prefixes `fault_codes.py:195`
recognises — 244's Doubt A established those prefixes are a Phase 111
fixture convention, not any manufacturer's.

**S0-2. Sources that exist, by make.**
- *Zero*: the SR/S dealer service manual is published (ManualsLib listing;
  automated fetch is bot-blocked — the operator opens it); the
  community-maintained Unofficial Zero Manual documents BMS, cell balancing
  (small current to low cells, mainly during CV charge taper, only when
  plugged in), the app's single worst-imbalance millivolt figure, and
  per-module SOH via dealer tools (its TLS certificate is expired; treat as
  `forum` class). An owner-forum SOH thread exists.
- *Energica*: 244 located the owner's manual's 110-code table, pp. 77-83,
  standard SAE P-codes; `P0516 BMS TEMPERATURE SENSOR SHORT CIRCUIT FAULT`
  is in it. A citable manufacturer source for BMS *faults*, not for BMS
  *mechanics*.
- *LiveWire*: 243 established the codes need Digital Technician II
  (dealer-only); the owner's manual is the only public source, and 243 found
  the catalogue endpoint returns 403. Generic-EV search results for
  LiveWire BMS are all aggregator content.
- *Generic engineering* (balancing topologies, SOH definitions, derating
  curves): abundant, none of it a motorcycle manufacturer's. Under the
  corpus's provenance classes that is `model-generated` — the class 244Z's
  lesson says to minimise.

**S0-3. The design question this row turns on.** "Generic" content with no
manufacturer anchor is exactly what F86 was. The proposal: every 246 entry
is written as *what the BMS does* **and** *how this make shows it* — e.g.
"cell imbalance: the BMS balances low cells at small current during the
constant-voltage taper, only while plugged in (Zero service manual §…); the
Zero app shows the worst imbalance in mV; per-module SOH is dealer-tool
only" — with `make` list-valued across the makes the anchor covers, and
`source = service-manual` **only** where a page is cited, else `forum` or
`model-generated` honestly. An entry that cannot be anchored to any make's
document is not written.

**S0-4. Substrate.** A `dtc_category` for HV/battery is a *data* question
(the category meta table 244R fixed), not a schema change — verify at build.
No new tables. No AI calls.

**S0-5. Cadence.** 242–244 ran a six-agent sweep-and-refute per make. This
row spans three makes and an engineering domain; the same discipline solo
is feasible but slow, and the refuter lens is the part that matters most
here (it is what killed `HD-20-LW-BMS` in 243). **Operator decision:** opt
into a research workflow for 246, or run it solo.

## Proposed scope

1. **Five generic entries** — balancing, SOH, voltage curve, thermal
   derating, cycle counting — each anchored per S0-3, `make` list-valued,
   `dtc_category` assigned where a code exists (Energica P0516 family).
2. **A per-make "how it shows" appendix inside each entry**, not separate
   rows, so `kb search bms` returns one answer per concept.
3. **A `battery` DTC category** if the meta table allows a data-only add;
   Energica's BMS P-codes recategorised into it.
4. **Tests**: every 246 entry names a source page or is not `service-manual`;
   no entry states a numeric threshold (mV, °C, cycles) without a cited page
   — the 244Z charging-threshold rule, generalised; the five concepts are
   reachable through `kb search`.
5. **Research record** in this doc: survivors by source class, rejected
   claims with reasons.

## Non-goals

- No per-make failure patterns (242–244 own those); no inverter (247) or
  cooling-loop (249) content.
- No numeric thresholds from memory. None.
- No wiring, no new commands: content reaches mechanics through `kb search`,
  `kb symptom`, `diagnose`, as 243 recorded.

## Verification Checklist (proposed)

- [ ] Five entries, each with at least one manufacturer page cited
- [ ] No numeric threshold without a cited page (test)
- [ ] `kb search "cell balancing"` / `"state of health"` / `"derating"` each return a 246 entry
- [ ] `dtc_category` meta unchanged in schema; `battery` added as data if at all
- [ ] Mutations: strip a citation (test fails); add an unsourced mV figure (test fails)
- [ ] Full regression green

## Open for the operator

1. Workflow opt-in for the research, or solo.
2. Whether the Unofficial Zero Manual counts as `forum` (my proposal) or is
   excluded.
3. Whether to add the `battery` DTC category in this row or leave it to 247.
