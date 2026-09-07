# Phase 205 — Gate 11: End-to-End Integration — Phase Log

**Status:** 📋 Planned
**Started:** 2026-09-07 | **Completed:** —
**Repos:** `Kubanjaze/moto-diag` (gate lives here) +
`Kubanjaze/moto-diag-mobile` (ledger), branch
`phase-205-e2e-integration`. **Track J opens.**

---

### 2026-09-07 12:26 — Plan written (Step 0 audit + v1.0)

- **The gate's target is the DESKTOP half**, because Phase 204 just
  verified the mobile path on real hardware and re-running it would be
  slow, green and information-free.
- **Step 0's sharpest finding: Gate 8 did not gate what it claimed.**
  `test_phase174_gate8.py` makes 3 `runner.invoke` calls against 54
  direct repo calls — Track G's ~96 shop subcommands were exercised
  through the REPO LAYER, not the CLI. The shop CLI is the least-tested
  desktop surface in the repo, and it is the one a shop owner uses.
- **Second finding: a desktop-only shop cannot finish a job.** No CLI
  verb exists to install a received part (F59), log actual labour hours
  (time-tracking is API-only), render a PDF, or mint a share link.
- **Third: the OpenAPI snapshot is unguarded.** Mobile's committed
  `openapi.json` is refreshed by a manual script and nothing asserts it
  still matches the live spec — the app can compile against a contract
  the server no longer honours, silently, until a device session.
- **Reassuring non-finding:** the API and CLI import the SAME domain
  modules over one DB at SCHEMA_VERSION 48. Little duplicated logic;
  drift lives at the edges where one surface has no counterpart.
- **User decisions:** document the CLI gaps rather than fix them,
  preserving the zero-production-code rule every prior gate kept · pin
  the OpenAPI snapshot against the live spec (a test, not production
  code).
- **Next milestone:** write `tests/test_phase205_gate11.py` in the Gate
  5/6/7 shape — CLI walk, cross-surface agreement, asserted-absence
  documentation, contract snapshot, regression subprocesses.
