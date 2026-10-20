# Known-bad (F206, 1C): the named skips do not add up to the count

Regression of record: 10870 passed, 0 failed, 2 skipped, 0 errors at `74e3599` (27 min 21 s wall, `python -m pytest -n auto --dist load`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
