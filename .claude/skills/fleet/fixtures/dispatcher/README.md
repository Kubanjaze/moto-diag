# The dispatcher's fixtures

Read by `tests/test_phase388_dispatcher.py`.

| file | what it is | where it came from |
|---|---|---|
| `usage_measured.txt` | the good case: three lines, 7%, 8%, 13% | measured: `claude -p "/usage" --output-format json` on the home desktop, 2026-10-22 (`388_step0.md` S0-4), the `result` field's first lines |
| `usage_at_ceiling.txt` | weekly all-models at exactly 70%: an Opus stage is refused | hand-written in the measured shape; a reset with minutes (`3:30am`) |
| `usage_limited.txt` | session and Fable at 100%: the reset is the later of the two | hand-written in the measured shape |
| `usage_unparseable.txt` | no line in the measured shape: an Opus stage is refused, and a limit waits an hour | hand-written, known-bad |
| `rate_limited.json` | a claude result that ended on a usage limit | **hand-written**: no limit was hit to measure one. The text follows the CLI's own wording seen in the operator's sessions ("limit reached", "resets"); the dispatcher matches a usage, rate, session or weekly limit, "limit reached" or "limit exceeded", or "hit your limit" |
