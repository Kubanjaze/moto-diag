# Known-good (Phase 359, bug fix #1): two regression lines, and A5 reads the last

The first run, superseded because code changed after it, recorded with no command:

Regression of record: 9636 passed, 0 failed, 0 skipped, 0 errors at `aaaaaaa` (28 min 26 s wall, exit 0)

The re-run the close-out rests on:

Regression of record: 9639 passed, 0 failed, 0 skipped, 0 errors at `bbbbbbb` (25 min 49 s wall, `python -m pytest -n auto --dist load`, exit 0)
