# Phase 232 — Aprilia Dorsoduro / Shiver / SR Max — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-08 | **Completed:** 2026-09-08
**Repos:** `Kubanjaze/moto-diag`, branch `phase-232-aprilia-dorsoduro`

---

### 2026-09-08 — Written from a paired run, close

- **This phase launched no research.** Phase 231's capped 6-agent
  workflow carried two questions, one written for each phase, and both
  findings were refuted by two lenses. Two phases from one run, with the
  cap respected on each — the second phase costs only the writing.
- **Same make as 231, different engine**, and the guard asserts it: the
  90-degree *longitudinal* V-twin here against the 65-degree V4 there.
  Cylinders are front and rear rather than left and right, so
  per-cylinder codes land on the wrong one if read with transverse
  habits; the 900 is the 750 **stroked**, so bore-following parts may
  carry across and stroke-following ones do not; and a Dorsoduro 1200
  exists on a different engine, so a model-name search can land wrong.
- **The most useful entry is a negative finding, and it needed care.**
  Chronic fuel-pump and charging failure is widely claimed for these
  machines and appears in **none of three national recall databases** —
  but stated carelessly that becomes "these bikes are fine", the mirror
  of the folklore it corrects. It is scoped to the databases consulted,
  and paired with the two campaigns that **are** real: a gearbox output
  shaft fault that can loosen the front sprocket fastening with the rear
  wheel able to lock, and a front brake master cylinder that can drag or
  self-apply showing no brake light. The frame-number check needs a
  target, so the absence is only useful next to the presences.
- **The ride-by-wire entries carry the operationally sharp facts**: the
  system **self-learns at every key-on**, so a weak battery throws a
  throttle fault before the machine moves; the twist-grip tracks are
  **not a mirrored pair**, so comparing them by the usual expectation
  gives a wrong answer; a torque-monitor layer can stop the engine while
  storing a code the dash never displayed, so "nothing on the screen" is
  not "no fault"; and the throttle body and twist-grip sensor are
  **non-serviceable assemblies**, so a component-level quote is wrong
  before it is sent and the cheap inputs are worth excluding first.
- **The scooter was separated rather than absorbed.** The SR Max is a
  maxi-scooter — single cylinder, continuously variable transmission —
  and that is a machine-class difference before it is a model one.
- **No campaign numbers appear**, carrying forward the Phase 231 decision
  taken after a cited UK reference turned out to be a Citroën recall.
- **No content pipelining this time.** Phase 231's regression failed
  because this phase's content file was written into the tree while that
  run was going, and the doc-count guard ties the documented figure to
  the **live** seed count. The file was held out until 231 was committed.
- 832 → 837; 31 phase tests; regression 5623/0; F9 clean.
- **Key finding: an absence is only useful next to the presences.**
