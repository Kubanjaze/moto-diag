"""The code's own counts, pinned ONCE (Phase 393, K54).

The way `integration_gaps_counts.py` holds the allowlist sizes: one literal
per count, one assertion each, in `tests/test_phase393_quality_ratchet.py`
(the whole-tree command's fast mode runs it, so the push guard holds it).
Every other test and script imports the constant; that test fails on any
other file in `tests/` assigning one of these names.

The ratchet (the operator's, K54): a count above its pin fails; a count
below it fails too, until the pin is lowered in the same commit, so a gain
is locked in. Coverage works the other way: it may not fall below its pin
(`regression.sh`, through `scripts/code_quality.py coverage-gate`).

Each count's rule is `scripts/code_quality.py`'s, never a list. Append to
each history; never rewrite it.
"""

from __future__ import annotations

#: `ruff check src` with pyproject's rules (E, F, I, W). 1409 at Phase 393's
#: Step 0 (on a38a36b; 1093 of them E501, left alone) → 1108 (393: ruff's
#: safe fixes, 297 import-order, unused-import and f-string findings fixed;
#: four E501 went with them).
RUFF_FINDINGS = 1108

#: `mypy` with `[tool.mypy]` (no site-packages). 204 at Step 0 → 202 (393 bug
#: fix #1: the PDF renderer's `_escape`, rebound by `html.escape`, gave two).
MYPY_ERRORS = 202

#: Functions over McCabe 20 (`ruff check src --select C901`). 25 at Step 0.
COMPLEX_FUNCTIONS = 25

#: Files in src/ over 100,000 bytes. 5 at Step 0: core/migrations.py,
#: cli/shop.py, cli/advanced.py, core/migration_086_rows.py, cli/hardware.py.
BIG_FILES = 5

#: Private functions named `_money`, `_now` or `_now_iso`. 19 at Step 0 (7,
#: 6, 6). F235: one module each for money and time would take it to 0.
PRIVATE_HELPERS = 19

#: `except Exception` handlers whose body is only `pass`. 25 at Step 0 → 22
#: (393 bug fix #2: memory/erase.py's three). F234 holds the rest.
SWALLOWED_EXCEPTIONS = 22

#: Total line coverage, percent, from the regression of record, which may not
#: fall below it. Measured at Step 0 in the fence on a38a36b, twice: 87.597%
#: both times. Pinned at 87.5, the measure cut to one decimal, before the
#: regression of record (393's log): a pin is code, so it cannot follow the
#: run that tests it, and a pin above the run's own total would refuse it.
COVERAGE_PERCENT = 87.5
