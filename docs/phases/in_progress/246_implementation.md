# Phase 246 — BMS diagnostics: the generic layer, anchored per make

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-18

---

## Why v0.9 stopped for review

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

**S0-5. Cadence — decided.** Orchestrated, as 242–244 ran it, with one
rule the operator added: **the refuter fetches every cited page itself.**
Another agent vouching for a citation does not count; a page the refuter
cannot fetch (bot-blocked, expired certificate, 404) leaves the claim
*unverified*, and an unverified claim is not `service-manual`. One refuter
per cited URL, checking every claim that cites it.

**S0-6. The `battery` DTC category — audited end to end, deferred to 247.**
`DTCCategory` (`core/models.py:154`) already has `HV_BATTERY = "hv_battery"`
— Phase 111 put six EV categories in the Enum, twenty members in all. The
meta table has twelve rows and no `hv_battery`; `--category` validates
against the meta table (`cli/code.py:377`), so the value exists in code and
is rejected at the CLI. No `CHECK` on `dtc_codes.dtc_category` (the one at
`migrations.py:1967` is `issues.category`); the API exposes `category` as a
plain string; mobile has no TS union, no icon or filter map, only a cached
copy of the meta table. Data-only at the contract. But meta rows are seeded
only by migrations, a migration bumps `SCHEMA_VERSION` 62 → 63, and eleven
tests pin that literal. And **the corpus holds zero Energica DTCs** — the one
"battery" hit is `P0132 O2 Sensor Circuit High Voltage` — so there is nothing
to recategorise and the category would be empty, which is the shape 244R
fixed. No test pins a per-category count; 244R's `used ⊆ meta` guard would
have refused an unmet category. Deferred to 247 as its own substrate
commit, with the Enum/meta gap recorded for it.

**S0-7. Where a `known_issues` number is displayed, and whether the source
label reaches it.** `kb list` renders a Source column
(`cli/kb.py:102-119`); `kb show` prints `Source:` through
`_render_provenance` (`:228-244`); the API's `KnownIssueResponse` carries
`source` as a six-value enum; the mobile app has no known-issue screen. **The
prompt does not**: `build_knowledge_context` (`engine/prompts.py:73-107`)
emits title, severity, scope, symptoms, causes and a 300-character fix
preview — no source — and `diagnose` renders no KB entries itself, so the
model's answer *is* the display. A forum-cited threshold in a fix procedure
reaches the model as if it were manufacturer data.

## Decisions (operator, 2026-09-18)

1. **Research runs as a workflow; the refuter fetches every cited page.**
2. **The Unofficial Zero Manual is `forum`** — except where the wiki is
   reproducing an official Zero document, in which case the official
   document is cited as `service-manual`, and the wiki is not.
3. **Forum-cited numeric thresholds are allowed only if the provenance
   label is surfaced wherever the number is displayed, enforced by a test.**
   Given S0-7 that means `build_knowledge_context` gains a `source` field
   per entry and the system prompt tells the model to attribute
   forum-sourced figures as such; the test walks every display surface.
4. **`battery` category deferred to 247** (S0-6).

## Scope

1. **Five generic entries** — balancing, SOH, voltage curve, thermal
   derating, cycle counting — each anchored per S0-3, `make` list-valued,
   `dtc_category` assigned where a code exists (Energica P0516 family).
2. **A per-make "how it shows" appendix inside each entry**, not separate
   rows, so `kb search bms` returns one answer per concept.
3. **The prompt carries provenance.** `build_knowledge_context` emits
   `source:` per entry; the system prompt instructs attribution of
   forum-sourced figures. `diagnose`'s output is where the number is
   displayed, so this is where the label goes.
4. **Tests**: every 246 entry names a source page or is not `service-manual`;
   a numeric threshold (mV, °C, cycles) is `service-manual`-cited or
   `forum`-labelled — never unlabelled; every display surface of a known
   issue (kb list/search/symptom/show, the prompt) shows `source`, with a
   mutation that strips it from the prompt; the five concepts are reachable
   through `kb search`.
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
- [ ] `dtc_category_meta` untouched (the category is 247's)
- [ ] Every display surface of a known issue shows `source`; the prompt test fails when it is stripped
- [ ] The Zero wiki is cited as `forum` only where it is not reproducing an official document
- [ ] Mutations: strip a citation (test fails); add an unlabelled mV figure (test fails); strip `source` from the prompt (test fails)
- [ ] Full regression green

