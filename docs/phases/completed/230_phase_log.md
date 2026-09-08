# Phase 230 — Triumph electrical + tooling — Phase Log

**Status:** ✅ Complete — closes the Triumph block
**Started:** 2026-09-08 | **Completed:** 2026-09-08
**Repos:** `Kubanjaze/moto-diag`, branch `phase-230-triumph-electrical`

---

### 2026-09-08 — Step 0, capped research, three inheritances, close

- **The first closing phase to arrive with a written brief.** Row 230
  carried three inheritances recorded on it by earlier phases, and each
  was verified here rather than trusted.
- **(1) The adapter gap (from 226) needed two answers, not one.** The
  injected air-cooled Bonneville from 2008 is well covered and now has
  full-access rows. The **carburetted 2001–2007 machines have no engine
  control module and no diagnostic connector at all**, so they get an
  explicit `incompatible` row. That distinction is the value: an absent
  row implies the catalog merely lacks a tool, when the truth is that no
  tool can exist and diagnosis is by measurement only. Two adapters
  added, 17 compat rows, Triumph rows 5 → 22. **DealerTool is
  third-party despite its name**; Triumph's own dealer software is the
  separately distributed Triumph Diagnostic Tool.
- **(2) The naming question inverted the KTM answer rather than
  inheriting it.** Phase 225 found TuneBoy is only a tune editor on KTM.
  On Triumph it also ships a diagnostic module — though it publishes no
  function matrix for it, so its per-model diagnostic coverage is
  recorded as **unestablished** rather than assumed either way.
- **(3) P0315 held completely.** A refuter re-downloaded Triumph's
  bulletins and confirmed verbatim: Euro 5 markets only, machines
  typically adapted at the factory, a small number needing it at PDI,
  **cannot be cleared with the normal erase function**, and requiring a
  full power-down after adaption. Written as an unperformed adaption
  first and a sensor fault second, because on a recently delivered
  machine that ordering is the whole diagnosis.
- **Cylinder numbering settled with an exception**, which is why it was
  worth researching. Triumph's own tables give "Left to Right" for the
  transverse triples, but the **Rocket 3's longitudinal triple is "Front
  to back, 1 at front"** — so all three misfire rows carry the exception
  and no observer position is invented, since the source does not state
  one.
- **Seven DTC rows and five knowledge entries.** The best entry is one
  nobody would go looking for: Triumph's workshop manual specifies lamp
  behaviour per code, and **a flashing lamp means an identity or
  security mismatch while a steady one means an ordinary fault** — so
  the lamp narrows the search before a tool is connected. Also: the
  socket is OBD-II *shaped* but speaks Triumph K-line, so a generic
  reader fits and reads nothing; and Triumph documents **no** dash
  diagnostic mode, so the button sequence owners share is recorded as
  not-factory-procedure rather than repeated as one.
- **Refutation removed an unsourced ISO standard number, corrected a
  misread tool-coverage column** (an "N/A" in a kit column read as
  unsupported when it meant no starter-kit SKU) **and fixed a vendor URL
  that does not exist** (the site is client-rendered, so every path
  returns a shell).
- **The 226–229 row-count guards were inverted deliberately.** All four
  asserted exactly five Triumph rows — right while the gap was open,
  wrong once it closed, and the same constant-for-invariant shape as the
  KTM count at 222. They now assert the original five survived and the
  gap is closed.
- **Eleventh mention-versus-use slip**: a check for an "official" claim
  about DealerTool matched the *symptom* "is dealertool the official
  triumph tool" — the mechanic's question, not a claim. Claim checks run
  on assertion-bearing fields only.
- **6 agents, 760K subagent tokens, 25 minutes**, progress reported.
- 819 → 824; 51 Triumph entries across five files; 42 phase tests;
  regression 5558/0; F9 clean.
- **Key finding: an inherited claim is not a verified one.** P0315 had
  been written down twice before it reached this phase, which made it
  feel established. It was checked again and it held — the point being
  that holding was the outcome, not the assumption.
