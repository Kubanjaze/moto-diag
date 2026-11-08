# ZZZ log

Known-bad, Phase 398 (F251): the only line holding the prefix is a row of
a Red Team table that quotes a whole regression line, command and exit
code included. A quote is not the record, so A5 must fail this log.

## Refuter pass

| claim | source | verdict | quote | round · kind · outcome |
|---|---|---|---|---|
| Regression of record: 12186 passed, 0 failed, 0 skipped, 0 errors at `c2b0767` (35 min 23 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) | Results | kept | "Regression of record: 12186 passed" | 1 · fact · kept |
