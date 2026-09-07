# Phase 215 — BMW electrical + FI dealer mode — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-215-bmw-electrical`

---

### 2026-09-07 — Plan v1.0 + Step 0 audit (inline)

- **This phase is not shaped like 211–214.** Those wrote known_issues
  JSON. This one touches three surfaces: the DTC seed, the hardware
  adapter catalog, and known_issues — and it services the fault-code
  backlog the previous four phases deferred here by writing
  `dtc_codes: []` on every entry.
- **The Harley DTC file sets the safe pattern.** 55 codes exist:
  generic (35) and harley_davidson (20). Every Harley code uses a
  standard OBD-II prefix — P0xxx, the manufacturer-defined P1xxx range,
  U1016, B1004 — with make-specific *causes and fixes*. `get_dtcs`
  resolves make → generic → any, so a BMW row shadows the generic one
  automatically, which means a BMW entry must ADD content rather than
  restate.
- **GS-911 is absent from a catalog that already knows the problem.**
  24 adapters, 110 compat rows, 12 of them BMW — and one already says
  a generic ELM327 clone is *incompatible* with the S1000RR because of
  "BMW proprietary CAN session layer that rejects generic ELM327
  handshake". The BMW motorcycle dealer-level tool itself is missing.
- **The accuracy risk is sharper than anything in Track K so far.** A
  vague knowledge-base entry wastes an hour; **a wrong fault code sends
  a mechanic to the wrong component with false confidence**, because a
  code number reads as fact rather than opinion. BMW bikes emit
  standard OBD-II P0xxx codes — shared and safe. BMW proprietary codes,
  the ones GS-911 and ISTA read, are not P-codes and are not something
  to transcribe from memory.
- **Decision: document the format, do not invent the numbers.** That
  BMW proprietary codes exist and need a real tool is a knowledge-base
  entry. A dedicated fabricated-code refuter is added as a fourth lens,
  and a short correct DTC file is the intended outcome even if it is
  small.

### 2026-09-07 — Built. The BMW block is closed; the fabrication risk did not materialise, a subtler one did.

- **Three surfaces, all landed.** `dtc_codes/bmw.json` (10 codes, 55 →
  65 in the seed); `known_issues_bmw_electrical.json` (3 entries, 701 →
  704); GS-911 in the adapter catalog (24 → 25) with 5 BMW compat rows
  (110 → 115). All five BMW files load together to **44 entries**, no
  title collision. 41 agents, 0 errors, 0 undecided.
- **Not one fabricated code.** Every one of the 10 is a standard-format
  P0xxx whose description is the real OBD-II meaning of that number;
  BMW content lives only in causes and fix. No P1xxx was invented and
  no BMW proprietary code was transcribed. The proprietary format is
  documented as knowledge — that "no codes found" on an ELM327 is not
  "no fault" — rather than invented as data.
- **The one DTC drop is the phase's most instructive verdict.** P0135
  was not killed for being wrong; it was killed because the corpus's
  existing generic O2 coverage in `cross_platform_fi.json` already gives
  a heater-resistance range, the heat-damaged-routing cause and the
  aftermarket-exhaust eliminator path, and the BMW row offered only
  generic O2-heater causes. Because make-specific rows resolve BEFORE
  generic ones, that row would have been *"strictly weaker than the
  generic row it would shadow — a BMW owner hitting P0135 would lose
  the resistance spec and gain nothing."* A make-specific row can be
  worse than no row.
- **One issue entry dropped for triple duplication** — a CAN-bus entry
  refuted as a generic playbook, as a restatement of
  `harley_electrical`'s CAN entry (which does it better, with real
  U-codes and 60/120/0-ohm interpretation), *and* as a diluted Phase
  212 ZFE trio. The verdict also caught a scope error: its "F-series,
  K-series … 2004" span swept in the pre-CAN F650GS single and the
  longitudinal K1200RS, neither a CAN-bus bike.
- **I acted on the GS-911 draft's own uncertainty list.** Required to
  declare what it was unsure of, it produced fifteen items. Two changed
  the data: `supports_mode22` flipped **true → false** (the drafter:
  "arguably wrong … reads live data via BMW proprietary service
  requests, NOT generic OBD Mode 22" — and the flag feeds the
  recommender); and the R1300GS compat row was dropped ("the most
  speculative item here … NOT verified"). The surviving `verified_by`
  strings say "surfaced in search; page not opened" where that is
  true, which is the right state for a provenance field.
- **Shadowing verified live**, not assumed: `get_dtcs("P0335",
  make="BMW")` returns the BMW row; `make="Honda"` still returns the
  generic one.
- 24 phase tests; regression **5056 / 0**; F9 lint clean.
- **Key finding: precedence turns "adds nothing" into "actively
  subtracts."** The planned risk was fabrication. What actually
  threatened the product was a mediocre make-specific row *hiding* a
  better generic one — a property of any lookup with make → generic
  fallback, and worth carrying into every remaining Track K phase.
