# code_checks — the Quartermaster's Q10, Q11 and Q12, by hand (Phase 393)

Each folder is a pull request: `base/` is `master`, `head/` the branch.
`tests/test_phase393_code_checks.py` commits them into a throwaway
repository with `pyproject.toml` here, and runs `scripts/code_quality.py`.

| folder | what it holds | must |
|---|---|---|
| `good` | `average()` added, typed, every line run (`coverage.json`) | pass Q10, Q11, Q12 |
| `q10_bad` | an unused `import os` and `label()` returning a str as an int | fail Q10: 1 ruff, 1 mypy, 0 on master |
| `q11_bad` | `refund()` imported, never called: 1 of 8 lines run | fail Q11 at 12.5% |
| `q12_bad_complex` | `reason()` taken from McCabe 20 (19 branches) to 22 | fail Q12 |
| `q12_bad_size` | `catalogue.py`, 790 bytes on master, 858 on the head | fail Q12 at a limit of 800 and of 700; pass at 1,000 |

The size limit is K54's 100 KB everywhere but this test, which passes a
small one so the fixture stays small.
