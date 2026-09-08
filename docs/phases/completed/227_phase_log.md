# Phase 227 — Triumph Tiger adventure line — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-08 | **Completed:** 2026-09-08
**Repos:** `Kubanjaze/moto-diag`, branch `phase-227-triumph-tiger`

---

### 2026-09-08 — Step 0, researched and refuted facts, close

- **Tiger returned zero mentions across 784 entries**, but the adventure
  *topic* is among the corpus's best covered — 66 entries across the GS,
  Multistrada, V-Strom and four dual-sport files. So the backwards
  genericness test ran at full strength, and the counter-assertion
  sweeps every non-Triumph file rather than one hand-picked entry.
- **The row was wrong twice.** It omitted the **Tiger 1050**, which sits
  in neither this row's list nor row 228's — third block-opening row
  omission after the 690 Duke (222) and the 790 Bonneville (226). And it
  claimed "Ohlins on top trim", which is unsupported: no Triumph handbook
  names a suspension manufacturer, and the spec pages give Marzocchi on
  the Tiger 900 GT and Showa on the 2022+ Tiger 1200. Öhlins is not part
  of the Tiger line at all.
- **Five researched claims were refuted and none shipped.** The Tiger
  1050's front wheel is 17in not 19 — and 17 is what it *shares* with the
  Speed Triple, so the finding's prose had inverted its own point.
  "Off-Road Pro" is Rally Pro exclusive rather than part of the general
  Pro pack. The brake-pad corrosion mechanism (nickel content, porosity)
  appears nowhere in the dealer notice cited for it, so the regulator's
  own wording is used instead. The XR/XC acronym expansion is documented
  nowhere, so it is not published — the entry says what the letters do
  and declines to say what they stand for.
- **The fifth is the one a shop would have acted on.** The 18,000-mile
  valve interval widely repeated for the 2024 Tiger 900 is **false**. A
  refuter extracted the handbook's maintenance table with per-word
  coordinates and resolved the valve row to the 12,000 and 24,000
  columns; the figure traces to a misreading of a column headed "6,000
  and 18,000 Mile Service". The entry names it as wrong rather than
  quietly using the right number, because a customer arriving with the
  wrong figure needs to be told.
- **One finding went to another phase rather than into the file.** A
  refuter surfaced **P0315**, *Crankshaft Position System Variation Not
  Learned* — a Euro 5 Triumph adaption that, if not performed, stores a
  code and lights the MIL, and which **cannot be cleared with the normal
  Erase DTCs function**. That is Phase 230's scope. It is recorded on row
  230 and asserted absent here.
- **Eleven entries, all `service-manual`**, led by the **Tiger 1200
  front brake pad corrosion recall** — rated critical because a corroded
  pad can retain measurable thickness while the friction layer loses its
  bond, so a depth check passes a failing pad. Also the T-plane crank
  with its boundaries stated in both directions, "Tiger 900" naming two
  unrelated bikes thirty years apart, shaft drive being 1200-only, the
  12,000-versus-20,000-mile valve split, the 500-versus-600-mile first
  service split, early Tiger 800 and Explorer recalls, cylinder head
  bolts needing oil-lubricated threads, and a **negative finding**: the
  manifold-pressure-hose stall recall indexed under "Tiger" covers the
  660-class machines only.
- **The user raised workflow cost mid-phase**, and it is a fair concern:
  this run was 12 agents, 1.55M subagent tokens, 53 minutes, with no
  check-in from me beyond a sleep loop. From Phase 228 the standing rule
  is ~6 agents with progress check-ins during the run, cutting research
  breadth before cutting refutation.
- 784 → 795; 46 phase tests; regression 5421/0; F9 clean.
- **Key finding: a refuter's most valuable output is a claim you then do
  not ship.** Across two phases the refutation pass has removed eight
  such claims, three of which would have sent a shop to the wrong part
  or the wrong interval.
