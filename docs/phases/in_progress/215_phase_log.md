# Phase 215 — BMW electrical + FI dealer mode — Phase Log

**Status:** 🔨 In progress
**Started:** 2026-09-07
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
