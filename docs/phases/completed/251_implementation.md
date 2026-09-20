# Phase 251 — Vespa and Piaggio: a new marque, anchored per document

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-20

---

## Goal

Row 251: "Vespa / Piaggio (50-300cc) — Italian scooters, air/liquid-cooled,
MP3 tilting 3-wheelers, LX/GTS/Primavera." Track M opens, and it opens on
an empty subject: the corpus has **no Vespa row at all**. Written under the
rule Track L kept: every entry is anchored to a manufacturer document named
in the description, or it is not written; every number carries its label;
one row, one label; a regulator record on its own row; a community source
dated.

## Step 0 — findings

Measured against the live database (996 rows) on 2026-09-20.

**S0-1. The subject is empty.** Zero rows mention Vespa. Zero mention CVT,
variator, roller weights or MP3. Two mention "scooter" and five mention
Piaggio — and all of them arrived sideways, through Track K's Aprilia and
Moto Guzzi work.

**S0-2. What Track K already established, which 251 must reference rather
than restate.** Four of those five Piaggio rows are the Group's tooling
story: *"Aprilia and Moto Guzzi share one dealer tool, PADS, and one
interface"*, *"DiagCode covers only the Piaggio Group, but exceeds the
factory tool"*, *"Aprilia and Moto Guzzi share one parts catalogue, one
supersession"*, and MV Agusta's row naming the Group's software. A fifth is
a service-manual row on Moto Guzzi roller-tappet kits. The scooter mentions
are Aprilia's: *"The SR Max is a scooter, not a motorcycle — it shares
nothing…"*. So the Group's dealer tooling is **written**; what is missing is
the machines.

**S0-3. Vespa and Piaggio are not marques in this corpus yet, and 250C
means they will be the day the rows land.** The make junction holds sixteen
marques and neither is among them. Verified on a copy of the live database
rather than assumed: loading a single row whose make reads "Vespa" and
whose model column reads "GTS 300, Primavera 150, Sprint 150" makes Vespa a
known marque, resolves all three models exactly, and a Vespa GTS 300 query
comes back at tier `model`. Before 250C those models would have filed under
the raw make string and resolved nothing. The condition is that the make
column names the marque plainly, which is now a correctness requirement on
the authoring, not a nicety.

**S0-4. No adapter, no fault-code file.** `compat_matrix.json` covers
eleven makes and neither Piaggio nor Vespa. `seed/dtc_codes/` has no
piaggio or vespa file. Both are absences to record, not to fill: this row
writes knowledge-base content, and the corpus has an established place for
"what tool reads this machine" — the Group tooling rows above.

**S0-5. The row's own boundaries are other rows in this track.** Row 254 is
"Small-displacement CVT diagnostics", 256 is "Scooter electrical (12V
minimal)", 257 is "Small-engine carb service". So the generic CVT layer,
the generic scooter electrical layer and carburettor service are **not**
251's, exactly as 246-249 owned the generic layers that 242-244 did not.
251 is the machines: what Vespa and Piaggio publish, for which models, and
what the regulator recorded.

**S0-6. The count moves.** README, the quickstart, the install guide and
the launch checklist all state 996 and move together (Phase 208's guard).

## Decisions

**D1. Anchored or not written.** Every statement names the document it came
from — manual, service-station page, parts portal, or a regulator record
with its campaign number. A claim whose page the refuter cannot fetch is
not `service-manual`; it is downgraded or dropped.

**D2. One row, one label**, and a forum row names its site and the page's
own date. 246's rule, kept.

**D3. The MP3's tilt-lock is the row's distinctive subject.** Nothing in
this corpus describes a tilting three-wheeler. If the documents support it,
it earns a row of its own; if they do not, the absence is written.

**D4. The Group tooling is referenced, never restated.** PADS and DiagCode
are already shipped rows. A 251 row that needs them names them and points.

**D6. A mirrored document is named as mirrored.** Piaggio serves
`vespa.com` and `manuals.vespa.com` with HTTP 403 to every non-browser
client, and its owner's-manual channel is gated behind a VIN and personal
data — which the research did not submit and will not. The genuine Piaggio
documents carry their own codes and copyright lines and were readable only
from third-party mirrors. Phase 246 met this before and set the rule: a
`service-manual` row names the document by code **and** says it was read
from a mirror copy. 251 keeps it. What a row may never do is imply the
statement came off a Piaggio server.

**D7. "HiPER" is not written unless a document says it.** The research
brief asked about a "HiPER" engine family — my own assumption, carried in
from the roadmap row's vocabulary. Six fetched Piaggio documents never use
the word; Piaggio writes "hpe" and "i-Get". A phase that invents a family
name in its own prompt and then finds it "confirmed" is the failure mode
242 recorded. It is not written.

**D5. What the machines do not have is content.** If Vespa publishes no
valve-clearance figure for a model, the row says so rather than borrowing
one from a forum and labelling it manual.

## Scope

1. `known_issues_vespa_piaggio.json` — the machines: model families and what
   distinguishes them, what the manuals publish for service, the MP3's
   tilting front end, the regulator record, and a dated community row only
   where a community number is the only number.
2. A content test in 249's shape: every row anchored, every number
   labelled, no restatement of Track K's tooling rows, the new marques
   reachable through the junction 250C now keys by marque.
3. The four user-facing docs' count, moved together.

## Non-goals

- **No generic CVT, electrical or carburettor layer** — rows 254, 256, 257.
- No `dtc_codes` seeding, no adapter compatibility rows (S0-4).
- No schema change, no migration.
- Nothing from memory: no interval, torque or capacity that a fetched page
  does not state.

## Results (v1.1)

**Shipped:** `known_issues_vespa_piaggio.json`, ten rows — seven
`service-manual`, three `regulation`, none `model-generated` and none
`unverified`. Corpus 996 → 1006. Two new marques.

- 64 tests, 11 mutations.
- Full regression **7,467 passed, 0 failed, 33:25**.

### The rows

Three of them carry what the corpus had no equivalent of. The **HPE
schedule change**: a GTS 300 i.e. replaces its drive belt every 15,000 km
(Cod. 1Q000478) while the HPE engine moved it to 10,000 km (1Q000725,
1Q001103 USA), took valve clearance from 20,000 to 10,000 and pushed the
plug out to 20,000 — the older schedule leaves an HPE belt 5,000 km late.
The **MP3 roll lock**, which nothing here described before: four
simultaneous engagement conditions, the lamp decode, the throttle-triggered
release, the 30 km/h cap, the double-flick unlock, and a rider sensor in
the front of the saddle that a bag will trigger. And the **CVT limits**
Piaggio publishes — belt minimum 21.5 mm against a 22.5 ± 0.2 mm standard,
with a tooth-root cracking criterion that does not depend on measurement.

The regulation rows carry the four brake-plating campaigns as what they
are — one supplier, one failure mode, **two plating processes**, because
the zinc-nickel lines of 20V617000 were the fix for the zinc ones and
failed in turn — and 07V253000, a recall whose stated cause is a service
practice: refitting the muffler without renewing the exhaust gasket, which
melted the rear brake hose.

### What the refuters changed

Three refuters re-fetched every page these rows cite. **Not one figure
moved.** The intervals were re-verified by column x-coordinate rather than
mark count; the six-pin pinout, the 10-bar hot-start threshold, the valve
clearances and the wear limits all stood. What they killed was the
connective tissue the sweeps had written around the figures:

| The sentence | Why it died |
|---|---|
| the brake procedure replaced one that was "ineffective" | Piaggio wrote "improves the bleeding effectiveness"; ineffective/fail/defect appear zero times |
| "the roll lock fails safe locked by design" | that sentence scopes a bench reset; in service the manual documents the lock *disengaged* with a 30 km/h cap |
| failure lamp: flashing = fault, steady = rider | not exhaustive — steady **with the continuous alarm** is a stuck lock. The discriminator is sound, not cadence |
| tilt-lock fluid level is a scheduled check | it is pre-delivery; shipping it would have invented a maintenance item |
| four campaigns, one defect | the fourth is zinc-**nickel**: the remedy plating, failing in turn |
| "Quasar appears in no Piaggio document" | a universal negative from four manuals chosen where it could not appear |
| the reset is SYSTEM RESET → LOWER STOP SEARCH | that is step 1 of 3; it omits the POTENTIOMETER RESET the manual's caution attaches to |

Every one was researched, plausible, and indistinguishable from the
verified sentences beside it. Each has a test, and each is a mutation.

### A finding about the research tooling itself

The census sweeps produced **three different confident answers**. One ran
2,750 queries with 2,038 failures and 10,322 retries — a 74% hard-failure
rate — printed that count, and then printed "DISTINCT CAMPAIGNS = 3" as
its finding. `api.nhtsa.gov` 403s Python's default User-Agent and
edge-blocks bursts, so a client mapping 4xx to "no results" cannot tell
"no recalls" from "I was blocked". Ground truth is at least ten campaigns.

So the ten-campaign list is written as a **floor, not a census**, and the
row says so; its test forbids any completeness claim. This repo has no
live NHTSA endpoint — `recalls.json` is static — so it is not a defect
here, but it binds any future recall-sync row, and it is filed.

### Deviations

**D7 was refined by the evidence.** The plan said "HiPER" would not be
written unless a document said it. A document does: the Typhoon 50 service
station manual names the two-stroke 50 family "Piaggio Hi-PER2". What
remains unwritten is the thing the brief actually got wrong — HiPER as a
*four-stroke* family name, and "Quasar" and "Master", which appear in the
four manuals searched only as an immobiliser key and a brake
master-cylinder.

**No forum row.** The only community source found has no readable page
date, so under the rule it cannot carry a row. 249 shipped none for the
same reason.

### Verification

- Ten rows, every one anchored to a document named in its description;
  mirror provenance stated where it applies (Phase 246's rule).
- Vespa and Piaggio resolve as marques with 32 and 35 models, and GTS 300,
  GTS 310 HPE, MP3 500 and Beverly 125 all resolve to their model and
  return rows at tier 0 — which works because 250C keyed the vocabulary by
  derived marque eight hours earlier.
- 11 mutations, all caught. Three survived the first pass; all three were
  weak guards, now testing the property rather than a token.

## Verification Checklist

- [x] Every row anchored to a named document, or dropped
- [x] Every number labelled; no number without a fetched source
- [x] No row restates Track K's Piaggio tooling rows
- [x] Vespa and Piaggio resolve as marques, with their models, after the load
- [x] The new test file scanned by 244G's raw-source guard
- [x] Mutations caught — 11/11
- [x] Full regression green — **7,467 passed, 0 failed, 33:25**, 0 skipped
- [x] Live DB loaded copy-first, before-state printed; count docs moved
- [x] Roadmap row, `implementation.md` history row, `phase_log.md`
