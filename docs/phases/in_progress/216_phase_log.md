# Phase 216 — Ducati Monster / Streetfighter — Phase Log

**Status:** 🔨 In progress
**Started:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-216-ducati-monster`

---

### 2026-09-07 — Plan v1.0 + Step 0 audit (four-agent workflow)

- **The roadmap row is wrong on two counts, and both premise checkers
  agreed without seeing each other.** (1) "Trellis frame" is false for
  the current Monster: the 2021+ 937 uses a cast-aluminium Front Frame
  bolted to the heads — the first Monster since 1993 without a trellis
  — and the 890 V2 continues aluminium. (2) "Testastretta evolution"
  does not cover the air-cooled line at all (every 2V Monster is a
  Desmodue), and the S4/early S4R are **Desmoquattro**, not
  Testastretta.
- **The Streetfighter V4 does not belong in this phase.** It is a 1103
  Desmosedici Stradale V4 on the Panigale's aluminium Front Frame with
  the Panigale's electronics; the refuting checker "failed on every
  axis" to justify keeping it here. It goes to **Phase 217**, and the
  roadmap is annotated so 217 picks it up.
- **The guardrail inverts against the BMW block, not the last phase.**
  Three BMW entries cover dry clutches. A refuter that learned "dry
  clutch is boxer hardware" would kill every correct Ducati entry. The
  overlap reader drew the seam exactly: BMW is a *single-plate* clutch
  contaminated by seal leaks, diagnosed at a bellhousing weep hole,
  repaired by an 8–12 h engine/gearbox split; Ducati is an *exposed
  multi-plate stack* in an aluminium basket behind a vented cover with
  a hydraulic slave on the left case — basket-finger and plate-ear
  wear, warped steels, slave-seal weep, stack out through the cover in
  under an hour, and an idle rattle that is **normal**. Attribution
  permits the hardware; duplication polices the mechanism.
- **Deferrals mirror the BMW block.** 219 owns desmo valve service
  (intervals, opener/closer shims, cost); 220 owns Marelli ECU, DDA+,
  Ducati CAN, the DDS tool and every fault code (`dtc_codes` stays
  `[]`). **Cam belts are in scope here** — row 219 lists intervals,
  shims and cost, not belts, and belt age is a real Monster failure
  mode.
- **Generation traps recorded**: S4R 996 Desmoquattro vs S4R 998
  Testastretta; 695 vs 696; 796 vs 797 vs 795 (all 803 cc, three
  bikes); 1100 dry vs 1100 EVO wet; SF 1098 dry vs 848 wet. Badges lie
  throughout — 900 = 904 cc, 1000 = 992 cc.
