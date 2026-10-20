# Known-bad (F206): a failing run recorded under the prefix of record

382's run on the desktop, as `regression.sh` printed it before Phase 383
(`382_phase_log.md` line 654 carries it with the prefix removed). The old
A5 parsed it: it read the count, the hash and the command, never the "5
failed" or the "exit 1".

Regression of record: 10832 passed, 5 failed, 33 skipped, 0 errors at `ac4cc3e` (9 min 16 s wall, `python -m pytest -n auto --dist load`, exit 1)
