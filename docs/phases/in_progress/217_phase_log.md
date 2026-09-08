# Phase 217 — Ducati Panigale superbike line — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-217-ducati-panigale`

---

### 2026-09-07 — Step 0, hand-drafted content, close

- **Lean mode: no workflow.** Content hand-drafted; the refuters'
  checks reproduced as a mechanical validator and encoded in the test
  file. The missing piece — an independent reader — is stated plainly
  in the plan's Risks rather than glossed.
- **Step 0 found a guardrail I wrote one phase ago is wrong.** Phase
  216's test file asserted "Ducatis are belt driven". Verified by
  search: the Superquadro uses a chain to a gear train between the
  camshafts — adopted specifically to remove belt service — and the V4
  Desmosedici Stradale is chain driven as well. 216's rule was scoped
  to its own file so nothing broke, but the comment was a false
  generalisation and is corrected in place.
- **So this phase asserts the opposite of its predecessor**: no entry
  may claim a cam belt on a Panigale, with a counter-assertion that the
  Monster file still legitimately owns belts. Second inversion inside
  the Ducati block, third in six phases.
- **My validator was wrong a third consecutive time.** It flagged the
  symptom "quoted for cam belts on a panigale" as a belt claim. It is
  not — it records the wrong quote a shop gives, which is the complaint
  the entry answers. Claim checks now run on title, description, causes
  and fix_procedure, never on `symptoms`, because a symptom is a report
  and may contain a mistaken belief.
- **Ten entries**, each naming Panigale hardware — chain-and-gear cam
  drive, monocoque construction with no frame to straighten, V4
  rear-bank deactivation misread as a misfire, counter-rotating crank
  misread as bad geometry, Öhlins Smart EC settings versus a failed
  strut, side-mounted radiators, the Streetfighter V4 booked in as a
  naked bike, the wet slipper clutch that has no dry-clutch rattle, and
  the 899/959 not being small 1199s.
- 716 → 726; 20 phase tests; regression **5100 / 0**; F9 clean.
- **Key finding: a guardrail can be wrong against the very next phase
  in the same block, by the same manufacturer** — and the checker needs
  as much scepticism as the content.
