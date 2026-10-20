# Known-bad (F206, 1C): the expected reason, from a file it is not pinned to

The operator: "pin each expected skip by its test file and its reason, not
the reason alone."

Regression of record: 10870 passed, 0 failed, 1 skipped, 0 errors at `74e3599` (27 min 21 s wall, `python -m pytest -n auto --dist load`, exit 0)
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:58: no production database on this machine
