# Phase 226 — Triumph Bonneville family (Hinckley) — Phase Log

**Status:** ✅ Complete — opens the Triumph block
**Started:** 2026-09-08 | **Completed:** 2026-09-08
**Repos:** `Kubanjaze/moto-diag`, branch `phase-226-triumph-bonneville`

---

### 2026-09-08 — Step 0, researched and refuted facts, provenance change, close

- **Triumph had zero entries**, so this opens a block. Step 0 found the
  topic near-empty too: `W800`/`W650` and `XSR` **0 files**, `CB1100` 1,
  `360-degree crank` **0**. "Modern classic" matched five files but every
  hit was "retrofit" — a false positive I checked rather than counted.
- **The row omitted a generation.** It read "865/900/1200cc". The
  Hinckley Bonneville launched at **790cc** in 2001, and the base
  Bonneville and America stayed 790 into MY2006 — a generation in neither
  this row's list nor row 229's. Same shape as the 690 Duke at 222.
- **First phase whose entries are not `model-generated`.** Ten are
  `service-manual` — Triumph owner's handbooks, the T120 service manual,
  and recall records filed with national road-safety regulators — and one
  is `forum`, saying so in its own prose because the shop conversation it
  implies is different: there is no campaign to quote.
- **That required re-scoping Gate 2, and the bug is a repeat.** Its
  forum-tip rule excluded by **denylist** (`!= "model-generated"`),
  assuming the corpus would only ever hold two populations; a third makes
  it demand forum tips from service-manual entries, fabricating exactly
  the provenance the column exists to record. It now names the population
  it measures (`unverified` + `forum`), and the sibling assertion was
  widened the same way. Third time in six phases that a guard written as
  "everything except X" has been broken by a Y.
- **The vocabulary does not have a value for what these actually are.**
  The CHECK set offers no "official regulator recall record";
  `service-manual` is the closest honest bucket and the lost precision is
  carried in each entry's prose. Worth a future `regulator` value;
  inventing one here would have broken the constraint.
- **12/12 research agents returned, 0 died.** Two findings survived both
  refuters; two were partially refuted, and **all three corrections
  changed shipped content**: the 790-vs-865 engine-number breakpoint is
  the **T100's changeover only** (the base Bonneville and America stayed
  790 with numbers well beyond it, and their breakpoint is not
  established), so the entry scopes the rule and admits the gap rather
  than publishing the figure; a forum line saying Triumph advises no
  parts commonality between generations was **contradicted in its own
  thread**, so the entry keeps the documented rim that would not lace and
  labels the wider claim disputed; and a refuter searching for
  contradictions found a **third carburetted-era recall the research had
  missed** — a starter cable chafing the oil cooler return pipe, fire
  risk — which is now an entry in its own right.
- **My own plan got the crank angle wrong**, and the research caught it.
  The America, Speedmaster and Scrambler are **270-degree** engines while
  air-cooled; only the Bonneville, T100 and Thruxton are 360. So an
  offset beat on an air-cooled bike is not evidence of anything.
- **Eleven entries**, led by a **live Do-Not-Drive campaign**: the 2024
  alternator-connector recall's clip remedy failed in service and was
  superseded in February 2026, so a completed earlier recall is not
  reassurance — that remedy is the thing that failed.
- **Eighth phase in which my own selector confused mention with use**: it
  treated the entry titled "faults that never got a **recall**" as a
  recall entry and demanded a document for it. Fixed with a negation
  check, plus a guard-on-the-guard asserting that entry is excluded. A
  second selector bug: `America` as a designation matched "North America"
  in a Kawasaki entry, so the corpus-wide counter-assertion now uses only
  unambiguous designations.
- 773 → 784; 44 phase tests; regression 5375/0; F9 clean.
- **Key finding: research does not only add facts, it removes them.** The
  most valuable output of this phase's refuters was three claims that do
  not appear in the shipped file.
