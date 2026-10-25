# Dry runs against real artefacts

Phase 389's rule after its three bug fixes (`SKILL.md`): no rank goes live
on a new check until it has run once against a real artefact in the real
place, its output kept here. **Measured**, both on 2026-10-25, in the
real fence, on the trial's branch `phase-389A-385s-roadmap-row`:

| file | what it is |
|---|---|
| `engineer_result.json` | the `engineer.json` a fenced Haiku session wrote with the Engineer's own flags (`bypassPermissions`, no web tools), through `FencedRunner.session`'s real Popen, token pipe and watch loop |
| `recommend_hold.json` | the Captain's recommendation (Fable) on the trial's approved plan before any build: hold, three lines |

Read by `tests/test_phase389_engineer.py` and `tests/test_phase389_captain.py`.
