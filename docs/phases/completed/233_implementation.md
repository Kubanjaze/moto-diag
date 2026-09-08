# Phase 233 — MV Agusta 3-cylinder

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Cover MV Agusta's 675 and 798 triples — F3, Brutale, Dragster, Turismo
Veloce, Rivale — with the counter-rotating crankshaft as the anchor.

Guard: `pytest tests/test_phase233_mv_agusta_triple.py`.

Outputs: `known_issues_mv_agusta_triple.json`, its test, roadmap row 233,
count 837 → 842.

## Existing-code audit (Step 0)

**1. MV Agusta has zero entries** and no adapter rows; row 235 owns the
tooling gap for both this make and Aprilia, so the absence stays guarded.

**2. `counter-rotating` returned one file across the corpus and `radial
valve` zero** — so the two MV phases sit on genuinely uncovered ground,
unlike the Aprilia pair where the V4 topic was saturated.

**3. Research was paired with Phase 234** in one capped 6-agent run, the
second pairing in this block.

**4. The roadmap row's phrase "known reliability quirks" is not
something to write from.** It invites folklore, and Phase 232 showed
what folklore is worth against regulator data. Everything here is either
a campaign, a manufacturer bulletin, or explicitly labelled as owner
report.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 837 → 842 |
| Entries | 5 — 4 `service-manual`, 1 `forum` |
| Research runs launched by this phase | 0 (paired with 234) |
| Refutation verdicts | both refuted, on the same claim |
| Phase tests | 30 |
| Backend regression | 5653 passed / 0 failed |

**Both refuters caught the same error and it was a dangerous one.** The
research reported the Dragster's loose-rear-spoke recall as UK-only with
no US campaign, and advised checking spoke tension. Both refuters found
it in the US database, found it flagged **do-not-ride**, and found the
published remedy is **replacement of the rear wheel** — the spoke
nipples' surface treatment is out of specification, so the tightening
torque cannot hold and re-tensioning does not restore them. Acting on the
original guidance would have left a defective wheel on a machine under a
do-not-ride campaign. The shipped entry says the obvious repair is the
wrong one, and says why.

**The counter-rotation entry declines to state the direction.** That
these triples counter-rotate is well sourced from MV's own material, and
the shop-relevant consequence is real: "turn the engine in its direction
of rotation" means the opposite of the reflex, and turning it the wrong
way can let the one-way cam-chain tensioner slacken the chain. But MV's
stated direction — clockwise or anticlockwise, viewed from where — could
not be opened from any manufacturer document, so the entry sends the
mechanic to the machine's own timing marks instead of guessing. That is
the Phase 224 discipline applied to a rotation rather than a cylinder,
and a test asserts no direction word appears.

**Key finding: the obvious repair can be the wrong one, and only the
campaign's own mechanism tells you.** Re-tensioning a loose spoke is
what any competent wheel person would do, and here it leaves the fault in
place because the failure is in the nipple's surface, not its torque.
