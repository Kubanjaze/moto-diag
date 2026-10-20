# Known-bad (F206, 1C): a named skip that is not in EXPECTED_SKIPS

The 2026-09-19 case: the packaging suite skips when its wheel build cannot
reach the network, so a broken run looks clean.

Regression of record: 10849 passed, 0 failed, 21 skipped, 0 errors at `74e3599` (27 min 21 s wall, `python -m pytest -n auto --dist load`, exit 0)
Skipped in the regression of record: [21] tests/test_phase209_packaging.py:58: wheel build failed
