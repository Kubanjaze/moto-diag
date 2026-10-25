# fleet — changelog

## 2026-10-25 — the ranks that write: Science Officer, Captain, Engineer, Red Team (Phase 389)

Steps 6 and 7 of `docs/reports/2026-10-22_fleet_proposal.md`. The prompt is
`docs/prompts/389_captain_engineer.txt`; Step 0 is `389_step0.md`.

- **`scout.py`** (Haiku, K42), **`captain.py`** (Fable), **`engineer.py`**
  (Opus), **`red_team.py`** (Opus, fresh): each a script around fenced
  calls; every label moved by the dispatcher from a checked result.
- **`fleet_git.py`**: the push gate G1–G6, run outside any session because
  the push guard is a hook; the push identity (the fleet's machine user, or
  the operator's login for a planted trial only).
- **`fence.sh`**: the token on a pipe (`--token-fd`), never the environment
  (measured: in the environment a Bash tool could read it from three
  processes' `/proc/<pid>/environ`); `--venv` and `--mobile`.
- **`dispatcher.py`**: the four stages and their resumes, the model-free
  check run, the Fable gate, closed phases and operator-held issues left
  alone, the Engineer's watched session.
- **`rank_call.py`**: `tools=`, and `NO_TOOLS` for one-turn calls.
- **Fixtures**: `fixtures/push_gate/cases.json` (hand-written known-bad
  pushes, one G-id each), `fixtures/scout/` (hand-written replies, the
  known-bad ones named in its README), `fixtures/dispatcher/usage_fable_at_ceiling.txt`.
- **Decided**: for a repository file, a refute table's page is the line
  number (C4 asks for a page; a text file has none).

Not done here, and why: the master ruleset (F214's other half) changes who
may push to `master`, the operator's call; the push gate refuses `master`
meanwhile.

## 2026-10-22 — the fence on Linux and the dispatcher (Phase 388)

Steps 4 and 5 of `docs/reports/2026-10-22_fleet_proposal.md`, built on the
home desktop, the fleet's host from now on. The prompt is
`docs/prompts/388_fleet_host.txt`; Step 0 is `388_step0.md`.

- **`fence.sh`** and **`fence_net.py`**: one stage under bubblewrap, the
  clone and run directory writable, no `/home`, the rest read-only, the
  environment from nothing, the network the model API only. The
  `workspace-docs` import resolves inside: bound at the clone's sibling
  path, and the approval seeded for the fence's clone path (measured: a
  fresh clone at a new path runs with no workspace rules even with the
  sibling present). Closes F215's read confinement on this machine.
- **`dispatcher.py`**: the Executive Officer on `plan:needs-review`, the
  daily digest, the 24-hour sweep, the rate-limit pause and `--resume`, the
  70% Opus ceiling, one process by `flock`. 387's scripts are called as they
  are, with a `run=` that sends `claude` through the fence.
- **Fixtures**: `fixtures/dispatcher/` (the measured `/usage` text and
  hand-written known-bad ones; `README.md` says which is which);
  `fixtures/service/cases.json` (ten known-bad units, one rule each).
- **The service**: `ops/desktop/motodiag-fleet.service`,
  `install_fleet_unit.sh`, `motodiag-fleet-boot.xml`, installed by the
  operator.

Measured at Step 0: `claude -p "/usage"` prints the 5-hour and weekly
figures in print mode at no cost, so no ceiling file is needed.

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
