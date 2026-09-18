# Phase 246 — BMS diagnostics: the generic layer, anchored per make

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-18

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

## Results (v1.1)

**Built as planned, with one deviation the operator's own rule forced:
seven rows, not five.** Two of the survivors' numbers are community
figures — zerologs.bike's cell-spread bands and its log-derived capacity
estimate — and a row carries one `source` label. A community threshold
inside a `service-manual` row would be displayed under the manual's label
on every surface Part 1 fixed, which is the exact failure Decision 3 exists
to prevent. So each concept that has a community number gets a second,
`forum`-labelled row beside its manual-anchored one, and a test
(`test_a_forum_number_never_shares_a_row_with_manual_content`) holds the
line. `kb search balancing` and `kb search "state of health"` therefore
return two rows each, one per label; the other three concepts return one.

### Part 1 — the label travels with the number (commit `6ea44ee`)

`build_knowledge_context` now emits `, source: <label>` in each entry's
header when the row has one (`--- Issue 1: … (severity: medium, source:
forum) ---`); a dict with no source renders exactly as 244S pinned it.
`DIAGNOSTIC_SYSTEM_PROMPT` tells the model what the label means: a
`service-manual` figure may be stated as the manufacturer's; a `forum` or
`model-generated` figure is unverified, must be said to be ("an
owner-community figure"), and is never presented as a specification.
`tests/test_phase246_bms.py` walks every display surface S0-7 found —
`kb list`, `kb search`, `kb by-symptom`, `kb show`, the prompt — with one
seeded forum threshold ("100 mV") and asserts the label sits beside it on
each.

### Part 2 — the content (`known_issues_bms.json`, seven rows)

| Concept | Row | Source | Anchors |
|---|---|---|---|
| Cell balancing | *Cell balancing is automatic on every make — what the BMS shows the rider is a message, not a millivolt figure* | service-manual | Zero 88-09445-01 §2.2/4.1/6.38/7.6, 8811984-AF §6.40/7.2; Energica ENF003100 Rev. 02 pp. 38/46/50/75/92-93/96 + Ego/Ribelle product pages; H-D 94000703 Table 37 |
| Cell balancing (community) | *Reading cell spread from a Zero BMS log — the community bands are the log-analyser's, not Zero's* | forum | zerologs.bike "Battery Health & Degradation", Last updated July 30, 2026 |
| State of health | *State of health is a dealer-tool number on every make — what the rider sees is a warranty threshold, not a readout* | service-manual | Zero 88-09445-01 §9.3, firmware notes (updated 2026-08-12), bulletin SV-ZMC-020-405; Energica ENF003100 (full text) + product pages; H-D 94000703 pp. 40/173, 94001019, RESS warranty, LiveWire EU 2023/1542 disclosure (S2 only) |
| State of health (community) | *Estimating a Zero pack's usable capacity from its own logs — the community method and its limits* | forum | zerologs.bike "Battery Health & Degradation" (2026-07-30) and "Buying a Used Zero" (2026-09-07) |
| Voltage curve | *No electric motorcycle maker publishes a voltage-to-state-of-charge curve — the rider gets a learned SOC and colour bands* | service-manual | Zero 8811984-AF §1.3/4.3/5.8-5.9, 88-09445-01 §3.50-3.52/4.3/7.6; Energica pp. 36-37/63/75/81-82/91; H-D 94000703 Table 17, p. 99 |
| Thermal derating | *Thermal derating is the BMS refusing charge or discharge at the pack's temperature limits — each make shows it as a message or a colour band* | service-manual | Zero 88-09445-01 §3.26/4.12/5.1/7.6/7.8, 8811984-AF §3.27/4.12/5.1/7.2/7.8-7.10; Energica pp. 36/38/74-75/81/92; H-D 94000703 pp. 41/99/105, 94001019 |
| Cycle counting | *No electric motorcycle maker exposes a cycle counter — what each publishes is the ageing drivers and a storage state of charge* | service-manual | Zero 88-09445-01 §5.1/6.38, 8811984-AF §1.4/5.1/6.40/7.2, Long-Term Storage Guide (2024-12-20); Energica pp. 63/92/97-98 + product pages; H-D 94000703 pp. 40-41, Table 43, 94001019, RESS warranty |

Every row is written as *what the BMS does* and *how each make shows it*;
every service-manual row names its documents by code in the description
(244's convention — there is no citation column) and says it was read from
a mirror copy where it was; every number in a service-manual row is the
named manual's; the two forum rows name the site, its page and the page's
"Last updated" date, because the site records that its own bands have moved
before (a previous version called 60 mV a warning). Nothing is
`model-generated`. `make` is `Zero, Harley-Davidson, LiveWire, Energica` on
the five generic rows and resolves to all four marques through 244F's
junction (tested); the forum rows are `Zero`. The Energica fault channels
the manual names (P1000/P1001 pack, P1030/P1044 cell, P1005-P1009 BMS
measurement, U0111/U0112/U0412 comms; P1002/P1003/P0514/P0516/P0517
temperature) are listed in `dtc_codes` on the voltage and thermal rows so a
`code` lookup reaches them; `dtc_category` is not assigned (Decision 4;
247's substrate commit). README, quickstart, install guide and launch
checklist: 970 → 977 curated known issues (208's count guard).

### Deviations

1. **Seven rows, not five** — above. Recorded as a rule, not a workaround:
   one row, one label.
2. **The forum source is not the one Decision 2 named.** Decision 2 made
   the Unofficial Zero Manual (zeromanual.com) the `forum`-class source,
   with its official-document exceptions. It was dropped, not swapped by
   choice: its TLS certificate is expired, the refuter could not fetch it,
   and under Decision 1 a page the refuter cannot fetch cannot be cited at
   all. The only community source any refuter could fetch and verify was
   zerologs.bike — a log-analyser tool rather than a forum, classed `forum`
   because that is the corpus's community class — and its four claims are
   the two forum rows. Decision 2's exception (cite the official document,
   not the wiki, where the wiki reproduces it) was therefore never
   exercised: every Zero manual statement is cited to the manual directly,
   which is what the exception would have produced. The content test
   asserts no row names the wiki. The operator confirmed on 2026-09-18 that
   zerologs.bike is independent, not an in-house property.
3. **Every owner's manual was read from a mirror** (dealer-hosted PDFs:
   jimcontent for the 2021 Zero and the Energica Eva, englishelectricmotorco
   for the 2025 Zero, 1903shop.de for the 2020 LiveWire). Each row cites the
   document by its manufacturer code and says "read from a mirror copy".
4. **A refuter-verified figure was replaced with the page's own words**:
   the sweep's "≈0.88 of nameplate" is, on the page, "87.5% to 89.3% of the
   badge"; the row carries the latter.

### Verification

- 51 tests in the two 246 files (9 rule, 42 content); 390 across the 16
  suites run before the regression: both 246 files, 244D (dedup — every
  row inserts), 244F (marques), 244I (models), 208 (docs counts), 78
  (gate 2, forum-tip ratio), 241–244 (the EV files), 244T, 03, 244S, 244E,
  240 (gate 12 — the six-value provenance vocabulary and the README count).
- **6/6 mutations killed**, bytecode cleared and `-B`: strip the document
  name from a service-manual row · add an unlabelled 100 mV threshold as
  `model-generated` · paste the community mV bands into a service-manual row
  · drop the page date from a forum row · strip `source` from
  `build_knowledge_context` · delete the thermal-derating row. The sixth
  survived its first run — the concept check matched `derat` anywhere and
  found "mo**derat**e" in the community cell-spread row — so the concepts
  are now word-bounded and matched in titles only.
- 244G raw-source scan of the new test file: clean. `ruff` clean on the
  246 files (three findings in `engine/prompts.py` pre-exist on master).
- No schema change; `dtc_category_meta` untouched; no new commands.
- Full regression **7,028 passed, 0 failed, 27:22**.

### The `battery` DTC category — audit result, re-verified at close-out (Decision 4)

The operator's condition: the category ships only if the Step 0 audit
confirms it is data-only end to end. Re-run on the branch at close-out,
layer by layer, on a fresh `init_db` database and on the live one:

| Layer | Finding |
|---|---|
| Backend Pydantic literal | None. The API carries `category` as `str` (`api/routes/kb.py:243`); the only `Literal` on this surface is `known_issues.source`. |
| DB CHECK constraint | None on `dtc_codes.dtc_category`. The one `CHECK (category IN …)` in `migrations.py` (line 1967) is on `issues.category`, a different table. |
| Mobile TS types | No union of category names; the offline export types one `dtc_category_meta` row (`api-types.ts:1923`) with `category` as a string. |
| Category → icon / filter maps | None in `moto-diag-mobile/src`; nothing keys on a category name. |
| Tests pinning category counts | None on `dtc_codes`. The only count pin is `len(categories) == 20` on the meta table (`test_phase111`), which a *new* category would break — and none is needed. |

**Verdict: data-only, and the category already exists.** Migration 004
seeded all twenty `DTCCategory` members into `dtc_category_meta`,
`hv_battery` included; a fresh database and `data/motodiag.db` both hold
twenty rows; `motodiag code --category hv_battery` is accepted by the
CLI's meta-table validation and answers "No DTCs found in category
'hv_battery'". **S0-6 was wrong** where it said the meta table holds twelve
rows without `hv_battery`, that the CLI rejects the value, and that adding
it would need migration 063 — the schema pin at 62 is real but irrelevant,
because nothing needs adding. Corrected here rather than rewritten above,
so the record shows what the plan believed and what the close-out found.

**What was done about it: nothing, correctly.** There is nothing to
classify — the corpus seeds zero Energica DTCs (the one "battery" hit in
Step 0 was P0132, an O2-sensor code), because Phase 244 chose to hold
Energica's 110-code table inside a known-issue entry rather than seed it
into `dtc_codes`. So the category exists, validates, and is empty: the
shape 244R fixed, with no rows to fill it. `dtc_category_meta` is
untouched (checklist). The Energica fault channels this phase's rows name
sit in `known_issues.dtc_codes`, where a `code` lookup reaches them.
Seeding the published Energica table into `dtc_codes` — which is what
would make `--category hv_battery` answer — is content work outside this
row's scope and is recorded as F90 in `moto-diag-mobile/docs/FOLLOWUPS.md`,
not started.

### Research record

**Cadence.** One workflow, opted into by the operator: a five-lens sweep
per make (manufacturer document, regulator record, owner community,
tooling, platform generation) produced 60 claims citing 14 URLs; **one
refuter per URL fetched the page itself** and checked every claim citing
it (14/14 fetched; the operator's rule that another agent's vouching does
not count); a critic then read the survivors against the pages. Tally: 60
survive (46 clean, 14 downgraded), 0 refuted, 0 unverifiable. The critic
judged the pass real — 13 downgrades, four locator errors, one
contradiction caught in a manual (Zero 2021 §3.50 says Charge Target
"0-100"; §3.51-3.52 say 30-95% in 5% steps; the row ships 30-95% with the
contradiction noted).

**Grid.** Every cell of the 5 concepts × 3 makes grid has a service-manual
claim. Class balance: 56 service-manual, 4 forum (all zerologs.bike; the
wiki was never reached). Documents: Zero 2021 SR/F owner's manual
88-09445-01 (11 claims), Zero 2025 owner's manual 8811984-AF (9), Zero
firmware release notes (3), Zero Long-Term Storage Guide (1), Zero
bulletin SV-ZMC-020-405 via NHTSA (1); Energica Eva owner's manual
ENF003100 Rev. 02 (13), Ego and Eva Ribelle product pages (2); H-D 2020
LiveWire owner's manual 94000703 (8), 2023 LiveWire ONE manual 94001019 on
the Service Information Portal (5), 2020 RESS limited warranty (2),
LiveWire EU Battery Regulation disclosure (1).

**Numbers re-fetched before use.** The critic flagged five figures the
refuter verified on the page but no claim quoted; I fetched both zerologs
pages on 2026-09-18 and took the sentences verbatim: capacity against
nameplate "±3 percentage points"; "87.5% to 89.3% of the badge" (not
"≈0.88"); "below 70% of nameplate raises an attention finding and below
50% a critical one"; "78-byte health records … full-charge capacity in
ampere-hours"; "State of health needs at least 4 usable charges out of the
bike's own logs"; "Gen3 main-board logs carry no battery current channel";
and the bands "≤ 40 mV excellent / 41-80 mV normal / 81-120 mV moderate /
> 120 mV significant" with the site's own note that its previous table
called 60 mV a warning.

**Not written.** Claim 53 (mileage as an ageing proxy — generic Li-ion
editorial, killed); the 110% Extended Range SOC and the 24-month
no-pro-ration period (no quote); claim 58's "implied SOH end-of-life"
(the author's inference); the LiveWire Connect discontinuation,
coulomb-counting, a 28S pack and a 4128 mV cell (mentioned by a lens,
never submitted); the Experia warranty parenthetical (embedded data
bundle, page not fetched); the MBB V44/BMU V19 release-note aside (page
not fetched for that claim). Trimmed per the critic: Zero's "thermal
strategy" to a cross-reference (a powertrain throttle, not a battery
derate; 247/249); Energica LIMP to its battery triggers; LiveWire's Temp
widget and "OBC Too Warm" rows to the RESS rows; "there is no owner-facing
SOH field" softened to "none is documented" (the firmware page is silent
on the dash); "readable by any UDS-capable tool" struck; "ambient" struck
from the 43 °C figure; the ZDU bulletin narrowed to what it says (logs,
not SOH).

**Deliberate absences, carried in the rows as sentences.** No make
publishes a voltage-vs-SOC curve, an OCV table, or a rider-facing pack or
cell voltage. No make shows a rider an SOH value (Zero: dealer BMS log;
LiveWire: dealer evaluation; Energica: no concept). No make publishes a
cell-balance tolerance or mV figure. No make exposes a cycle counter.
Energica publishes no °C behind LIMP, the cold-charge refusal, or its
temperature codes, and every Energica statement is anchored to the 2018
Eva. LiveWire's UDS SOH read is documented for S2 models only. Zero's
storage-mode SoC differs between the 2021 (60%) and 2025 (about 80%)
manuals; both are carried, year-scoped, with no cause asserted.

**zerologs.bike — confirmed independent.** The critic's condition on the
four forum claims was that the operator confirm the site is not an
in-house property. Its pages identify it as an independent log-analyser
("Made for Zero Motorcycles owners", with contact, about and support
pages) and nothing on them ties it to Zero; the operator confirmed on
2026-09-18 that it is not ours. The two forum rows ship labelled `forum`,
naming the site and the page dates, which is what Decision 3 requires of
any community number.

## Verification Checklist

- [x] Five concepts, each with at least one manufacturer page cited — seven rows, every service-manual row naming its documents
- [x] No numeric threshold without a cited page (test)
- [x] `kb search "balancing"` / `"state of health"` / `"derating"` each return a 246 entry (test)
- [x] `dtc_category_meta` untouched — the category already exists there (S0-6 corrected above); nothing to classify
- [x] Every display surface of a known issue shows `source`; the prompt test fails when it is stripped
- [x] The Zero wiki is cited nowhere (never fetched; test)
- [x] Mutations: 6/6
- [x] Full regression green — **7,028 passed, 0 failed, 27:22**
