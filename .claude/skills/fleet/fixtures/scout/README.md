# The Science Officer's fixtures

Read by `tests/test_phase389_scout.py`. All hand-written in the shape the
schemas in `scout.py` ask for; none is a measured model reply.

| file | what it is |
|---|---|
| `terms_good.json` | four terms, one repeated: the repeat is dropped |
| `terms_not_strings.json` | known-bad: terms that are not strings, a stop |
| `assess_good.json` | the judgement, with no counts in its prose |
| `assess_counts_in_prose.json` | known-bad: a count with no query ("14 files"), so P3 would fail; one corrective call, then a stop ("3 times" is not a count to P3: `plan_check.NOT_COUNTED`) |
| `assess_bare_phase_number.json` | known-bad, **measured**: the reason the trial's first Science Officer wrote on 2026-10-25 ("No row for 385 exists in docs/ROADMAP.md…"), quoted from the dispatcher's log; the checker reads "385 exists" as a count (Phase 389, bug fix #1) |
| `assess_no_classification.json` | known-bad: a classification that is none of the three, a stop |
