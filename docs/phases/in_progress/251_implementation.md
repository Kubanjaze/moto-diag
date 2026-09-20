# Phase 251 — Vespa and Piaggio: a new marque, anchored per document

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-20

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

**S0-3. Vespa and Piaggio are not marques in this corpus yet.** The make
junction holds sixteen marques and neither is among them. Phase 250C keys
the model vocabulary by derived marque, so a new marque arrives with its
models reachable the day its rows land — provided the make column names it
plainly. That is now a correctness requirement on how these rows are
written, not a nicety.

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

## Verification Checklist

- [ ] Every row anchored to a named document, or dropped
- [ ] Every number labelled; no number without a fetched source
- [ ] No row restates Track K's Piaggio tooling rows
- [ ] Vespa and Piaggio resolve as marques, with their models, after the load
- [ ] The new test file scanned by 244G's raw-source guard
- [ ] Mutations caught
- [ ] Full regression green, 0 failed and 0 skipped
- [ ] Live DB loaded copy-first, before-state printed; count docs moved
- [ ] Roadmap row, `implementation.md` history row, `phase_log.md`
