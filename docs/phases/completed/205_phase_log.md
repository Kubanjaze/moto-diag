# Phase 205 — Gate 11: End-to-End Integration — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
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

---

### 2026-09-07 12:41 — Gate 11 built and green; the desktop cannot finish a job

- **16 tests, ZERO production files changed** (`git status --short src/`
  empty). Regression **4799 passed, 0 failed**. Gates 5/6/7/8/9 re-run
  as subprocesses in 21s.
- **The finding, stated plainly: the desktop and the phone are not the
  same product.** A phone-equipped shop can measure labour, print a
  report and text a customer a link. A desktop-only shop can do none of
  those — it can only *assert* hours at completion, and hand over
  nothing. Five asymmetries, now executable documentation that fails the
  day each gap closes: no CLI verb to install a received part (F59), log
  labour (**F65**), render a PDF (**F66**), mint a share link
  (**F67**), or `open` a work order (**F68** — the API's transition
  accepts it, the CLI has only `start`).
- **Every gap was individually known or knowable. Nobody had walked the
  job end to end and seen they compose into one coherent hole** rather
  than four scattered TODOs. That is what the gate bought, and it is
  Gate 10's lesson from the other direction: run the whole thing as a
  user would.
- **Gate 8 did not gate what its roadmap row claims.** Three
  `runner.invoke` calls against fifty-four direct repo calls — Track G's
  ~96 shop subcommands were verified through the layer UNDERNEATH the
  surface they were meant to prove. Gate 11 drives the real `cli` root,
  so a command that failed to register would actually be caught.
- **The contract snapshot passed on arrival**, checked both directions.
  Recorded as a result rather than skipped: "we checked and it was fine"
  is a different claim from "nobody has ever checked", and this seam —
  the one that silently breaks the mobile app's generated types — was
  the latter until today.
- **Two authoring corrections, both mine, both about testing behaviour
  instead of wording.** Ids now come from the database rather than
  regexing `Added vehicle #1` out of CLI output; absence tests
  interrogate click's command registry after the first version failed
  because "time" appears inside "AI labor time estimation". A gate that
  fails on copy edits is a gate that gets muted.
- **Docs:** impl → v1.1, ledger closed, both moved to `completed/`;
  ROADMAP 205 ✅; four tickets filed.
