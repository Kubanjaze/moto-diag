# Phase 242 — Zero Motorcycles — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-09 | **Closed:** 2026-09-09
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-09 — Plan v1.0 written

The first make-specific electric phase, on the HV safety floor 241 laid.

**Step 0 — existing-code audit.** Nothing. Zero, Z-Force, ZF14 and Cypher
appear in no knowledge, DTC, compat, parts or template file except 241's
make-agnostic HV file; the vehicle identifier has never heard the name; the
only electric workflow template is the generic PPI. Discipline 9 (the primary
source may already be on disk) was checked across the scratchpad, Downloads
and the repo's data directory and found nothing. Greenfield content on the
Phase 110/111 extension substrate — the same footing as 241.

**Scope boundary, stated before content exists.** Phases 246, 247 and 249 own
BMS, inverter and thermal. 242 covers what is Zero-specific and nothing
generic. The third refuter lens exists to enforce that.

**The figure boundary, stated before content exists.** 241 printed no
machine-specific figure because it opened no manufacturer document. 242 may
print one **only** from a Zero document the research actually opened and the
entry names — the Phase 238 rule, per entry. Otherwise the figure is withheld
and the absence stated. Spec roundups, aggregators and forum recollection do
not count as documents.

**The research is orchestrated, and the plan records its shape.** Track K ran
2 questions × 2 refuter lenses; this phase runs a five-way multi-modal sweep
(manufacturer document, regulator record, owner community, tooling, platform
generation), then three-lens adversarial refutation per claim — source exists
and says this; figure is attributed; claim is Zero-specific — with refuters
defaulting to refuted, then a completeness critic, then synthesis. Every
rejected claim is recorded with its reason. An entry count is what survives,
not a target.

**Two open questions the research answers, not the plan.** Whether Zero's fault
codes are documented in a primary source (then a `dtc_codes/zero.json` ships;
otherwise the absence is recorded), and how the Zero app — the actual
diagnostic route — should be represented given `adapters.json` has no
app-based transport.

Baseline before any work: **6031 passed / 0 failed** (Phase 241).

Plan v1.0 written to `docs/phases/in_progress/242_implementation.md`.

---

## 2026-09-09 — Build complete

**The research ran, and then I had to repair my own prompt before it could be
used.** Five finders returned 75 unique claims. Three refuter lenses judged
each. 29 survived — and every single one was `manufacturer-document`. Zero
recalls. Zero community patterns. That is not what a corpus looks like; it is
what a broken filter looks like.

The figure lens said "every number must trace to a named Zero Motorcycles
document". Correct for a manufacturer claim. Wrong for a recall record, whose
model years, build windows and unit counts come from the **regulator**. My lens
could not pass any regulator or community claim containing a number, so it
refuted all 35 of them. The only visible symptom was the shape of the result.

**A repair run re-judged the 25 claims that had passed source and scope and
died only on that bug, under a source-class-aware standard: 11 recovered — 8
recalls and 3 community patterns.** Without it this phase would have shipped a
Zero file with no recall coverage at all, including no stop-riding campaigns.

**Every recovered claim came back corrected, and four of the corrections change
what a mechanic does.** The 2013 water-ingress campaign covers the FX and XU
only, not the full 2013 line, and its remedy is removal and return of the
modules rather than a sealing operation. The 2020 brake-switch record describes
no stays-on failure mode — but does record that cruise control will not cancel,
which the original claim missed. The 2023-24 key-switch remedy is a firmware
update, not the harness work a shop reading the mechanism would quote. And the
2012 pack-fire remedy is the owner's choice of repurchase or trade-assist, with
a park-it advisory the original omitted.

**14 claims stayed rejected on judgement.** Six were recalls whose verifiers
opened the Part 573 filings and found the claim wrong on substance — one
returned simply "REMEDY IS WRONG AND SAFETY-CRITICAL". Those are not in the
file, and that is the layer working.

**17 entries shipped**: platform identification, the Cypher II/III split, belt
tension and belt care, the service schedule, storage and charging, warranty,
the diagnostic route, the app, firmware, charging accessories, five recall
entries covering eight campaigns, and one forum entry for the unsupported
serial console. 16 `service-manual`, 1 `forum`. Every figure traces to a named
document; **no campaign reference number appears anywhere**, per the Phase 231
rule.

**The same bug bit me a second time, in a test.** My guard requiring a printed
figure to name a Zero document used a `DOC` pattern listing only Zero
publication types — so a recall entry would have failed it for citing a
regulator. Widened. Two instances of one wrong assumption, in a prompt and in a
guard, written hours apart.

**Six mutation scenarios, all caught** — though one had to be redone: my first
attempt at the Zero-specificity mutation stripped the description and left
"Cypher" in `fix_procedure`, so the guard passed correctly and my mutation was
simply incomplete. Redone across all assertion-bearing fields, it fires.

**No DTC file and no compat rows.** The tooling research established that Zero
publishes its fault-code vocabulary as a numbered table in the owner's manual,
not as a machine-readable list, and that the route is the dash, the app and
Zero's dealer unit. The plan left the question open; the research answered it,
and forcing a `dtc_codes/zero.json` would have invented a vocabulary.

**Debt recorded, not shipped:** 5 claims unverified because their refuters died
at a session limit, and the completeness critic never ran, so coverage is
unverified.

Corpus 927 → 944; four user docs moved under the Phase 208 guard. 654
corpus-globbing guards accept the file. F9 lint clean.

Regression: **6047 passed / 0 failed** (baseline 6031; +16 guards).
