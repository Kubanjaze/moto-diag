# Phase 244T — A hazard is told to the person holding the wrench — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-17

---

## 2026-09-17 — Plan v1.0 written

Third of the reachability phases from the Track L audit. Step 0's checker
broke the design's electric detection in both directions on one manufacturer,
and the operator set the alert threshold from a measurement rather than a
guess: CRITICAL and WARNING only.

## 2026-09-17 — Built

The wiring is small. What it found is not.

Pressing 19 never-called rules against real diagnosis text turned up two
substring false positives, both of which print a CRITICAL "do not start the
engine": `gas` inside `gasket`, and `oil` inside `coil`. A valve-cover gasket
weep — one of the most ordinary findings on a motorcycle — raised a fuel-leak
alarm. That is 22 of the 98 criticals the corpus produces, and it would have
shipped the day the panel appeared.

My first fix was worse: word boundaries as plain strings, where `\b` is a
backspace, which silenced the rules instead of narrowing them. Both directions
are pinned now.

Then Phase 241's tripwire fired in the regression, which is the best thing
that happened all phase. It had pinned "SafetyChecker has no production
caller" with a failure message listing what the day of wiring would owe:
powertrain context, the withheld HV rules, and its own deletion. Two of three
done; the HV rules are filed as F88 rather than invented, because there is no
sourceable content and inventing safety procedure is what row 245 was
rejected for.

The mutation run caught a weak assertion of mine: the warning test asserted on
the rule's title, which also appears in the ranked-diagnoses table, so it
passed with warnings suppressed.

26 tests, 9/9 mutations.

## 2026-09-17 20:37 EDT — Complete

Regression **6,914 passed, 0 failed, 30:07**. No schema change.
