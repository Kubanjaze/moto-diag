# fleet — changelog

## 2026-10-22 — created (Phase 387)

Steps 2 and 3 of `docs/reports/2026-10-22_fleet_proposal.md`: the
Executive Officer and the Yeoman, both read-only. The prompt is
`docs/prompts/387_xo_and_yeoman.txt`.

- **`plan_check.py`**: the checklist, P1–P8, no model. Reuses
  `roadmap_check.rows`/`ACTIVE` and `wholetree.CONTENT_PATHS`. `--rev`
  reads a plan as its commit held it. A good tree and 21 hand-written
  known-bad cases (`fixtures/bad/cases.json`), one edit each, each failing
  on its own item and no other.
- **The pin** (K41, the operator: "Pin them (Recommended)"): 384 and 386's
  v1.0 are not held to P4, P7 and P8, which they predate. Without it each
  fails on exactly its pinned items; the test holds that equality.
- **`xo.py`**: the checklist, then one read-only Fable call with a fixed
  verdict schema; the label set by the script; two back-to-captain rounds;
  a stop leaves the label.
- **`yeoman.py`**: `decide` (K40 and K41 were its first rows) and
  `digest`.
- **`rank_call.py`**: the fence and the stops, shared by the two ranks.
- **`fence_probe.py`**: the planted Bash call and its control.
- **`labels.py`**: the eleven labels, made 2026-10-22 under the operator's
  login (K40).

Measured at Step 0 (`387_step0.md`): `claude -p` serves
`claude-fable-5-1`, `claude-opus-5-5` and `claude-haiku-5-5` on this
login; one XO call on 386's v1.0 read 148,263 tokens (input, cache write
and cache read) and wrote 7,347, in 11 turns and 100 s.
