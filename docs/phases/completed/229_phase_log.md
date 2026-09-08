# Phase 229 — Triumph vintage (Meriden + early Hinckley) — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-08 | **Completed:** 2026-09-08
**Repos:** `Kubanjaze/moto-diag`, branch `phase-229-triumph-vintage`

---

### 2026-09-08 — Step 0, capped research, close

- **The most saturated topic in the corpus — and the audit found its
  shape rather than just its size.** Four vintage files hold **40
  entries**, ten each, plus twenty cross-platform carburettor and
  ignition entries. Reading their titles side by side showed they are
  not sixty different entries but the **same ten topics written four
  times**: cam chain, charging, carb rebuild, points, petcock, forks,
  brakes, oil leaks, harness, chain. And `cross_platform_ignition`
  already owns points-versus-electronic conversion **and names Boyer
  Bransden for British twins specifically** — the single most obvious
  Triumph-vintage entry was already written, by another file.
- **That reframed the phase.** The question stopped being "what is left
  to say about old Triumphs" and became "what axis do forty
  Japanese-vintage entries not have". Every British-specific term
  returned **zero**: Whitworth, BSF, Cycle thread, positive earth,
  oil-in-frame, Amal, modular, 360-degree crank, dynamo. So the file is
  built on Britishness rather than age, with a counter-assertion
  sweeping all six existing files for zero.
- **Thirteen entries**, split across both eras. Meriden: mixed thread
  standards on one machine, with the near-misses that do the damage —
  3/16 Whitworth measuring about 11.3mm against an 11mm spanner, and
  quarter-inch Cycle at 26tpi starting in an M6 hole before it strips;
  **positive earth through 1978**, where assuming otherwise is
  documented as damaging a modern regulator; **oil-in-frame, where a
  crack is an oil leak and a structural failure at once**; no oil filter
  but a crankshaft sludge trap that starves the big ends if a rebuild
  skips it; the **Amal pilot screw being an AIR screw**, inverted from a
  Japanese pilot fuel screw; and vibration as a designed-in cause rather
  than a symptom. Hinckley: the **badge not being the capacity** (every
  900 is 885, every 1200 is 1180), the **T-number trap** (T595 is a 955,
  and Triumph renamed it for exactly that reason), carburetted and
  injected machines sharing model years, the 1994–95 Speed Triple being
  a five-speed and possibly a 750, early recalls including a frame
  headstock weld and a **fuel connector that fractures following
  in-service handling**, and metric fasteners as the clean 1991 break.
- **The best entry is a deduction, not a fault.** On a 360-degree twin
  both plugs fire every revolution, so one cylinder with spark and one
  without cannot be the ignition module or the trigger — it has to be
  local to that cylinder. That removes the expensive part from the list
  before it is bought.
- **Refutation removed six claims, and one was self-contradicting.** The
  research asserted Whitworth disappeared after the last pre-units while
  its own cited source documented Whitworth nuts on 1963–67 unit
  engines — a refuter that only checked whether sources existed would
  have passed it. Also removed: an inverted oil-in-frame seat height,
  valve and balancer specifications attributed to a source containing
  neither, a recall year range narrower than the regulator's, a polarity
  symptom set extrapolated past its source, and the five-speed framed as
  retro-only when it also covers the 1994–95 Speed Triple, which changes
  a gearbox quote. All six are asserted absent.
- **Cost: 6 agents, 661K subagent tokens, 23 minutes** — the cheapest
  run of the block, with progress reported during it.
- 806 → 819; 48 phase tests; regression 5515/0; F9 clean.
- **Key finding: when a topic is saturated, the phase's job is to find
  the axis the corpus lacks.** Counting entries said the ground was
  covered; reading their titles said it was covered along one axis only.
