# Phase 205 — Gate 11: End-to-End Integration (Desktop + Mobile)

**Version:** 1.0 | **Tier:** Gate | **Date:** 2026-09-07

## Existing-code audit (Step 0 — run 2026-09-07, before this plan)

**The house style for a gate here is strict, and this phase inherits it:**
one new test file, **zero production code**, one long single-scenario
walk on a shared DB, plus a surface-breadth class and an anti-regression
class that subprocess-re-runs earlier gates. Gates 5 (`test_phase133_
gate_5.py`), 6 (`test_phase147_gate_6.py:832,851`) and 7
(`test_phase159_gate_7.py:540,553`) all follow it literally.

**Finding 1 — Gate 8 is weaker than its roadmap row claims.**
`tests/test_phase174_gate8.py` makes **3** `runner.invoke` calls
(`:127,:142,:166`) against **54** direct repo calls with `db_path=cli_db`.
Track G's 13 shop subgroups and ~96 subcommands were therefore gated
**through the repo layer, not through the CLI**. The shop CLI — the
exact surface a desktop shop owner touches — is the least-exercised
desktop surface in the repo. That is this gate's target.

**Finding 2 — a desktop-only shop cannot finish a job.** The CLI has no
verb for four things the API does:
- **install** a received part (already filed as F59)
- **log actual labour hours** — `motodiag.shop.time_entries` is reached
  only from `api/routes/time_tracking.py:39`; there is no CLI at all, so
  `actual_hours` must be hand-typed at completion
- **render a PDF** — `motodiag.reporting` is reachable only from
  `api/routes/reports.py:41`; `cli/shop.py` has zero reporting references
- **mint a customer share link** — `api/routes/share.py`, no CLI

That asymmetry IS the headline finding, and per the scope decision below
this gate **documents** it rather than fixing it.

**Finding 3 — the OpenAPI snapshot is unguarded.** Mobile's
`api-schema/openapi.json` is refreshed by a manual script
(`scripts/refresh-api-schema.js`) and `src/api-types.ts` is generated
from it. **No test asserts the snapshot still matches the live spec.**
The app therefore compiles against a contract the server may no longer
honour, and the failure is silent until a device session. The audit
calls this the single most likely silent-drift seam; it is in scope
because a test is not production code.

**What is NOT drifting (worth recording):** the API routes import the
same domain modules the CLI does — `motodiag.shop.*`,
`crm.customer_repo`, `core.session_repo`, `advanced.parts_repo`,
`knowledge.*` — over one DB at `SCHEMA_VERSION = 48`. There is little
duplicated logic in the domain layer. Drift lives at the EDGES, where
one surface has no counterpart, which is exactly Finding 2.

**Integration-shaped debt already filed** (all open, cross-repo ledger
at `moto-diag-mobile/docs/FOLLOWUPS.md`): F14, F21/F22, F26, F27, F37,
F38, F44, F50, F54, F55, F57, F58, F59, F61, F62, F64. This gate should
cite rather than re-file them.

**Explicitly out of scope — Phase 204 covered it.** The mobile
film → upload → ffmpeg → vision → report → share-link path on real
hardware, and the five bugs 204 found; `tests/test_phase204_gate10.py`
already guards those.

**User decisions (2026-09-07):** document CLI gaps rather than fix them
(preserving the zero-production-code rule every prior gate kept) · pin
the OpenAPI snapshot against the live spec.

## Goal

Walk a shop owner's entire job **through the CLI**, on one database,
then re-read the same records **through the API** and assert the two
surfaces agree. Where the CLI cannot do what the API can, the gate
records the gap loudly instead of quietly routing around it.

Run: `pytest tests/test_phase205_gate11.py`

Outputs:
- `tests/test_phase205_gate11.py`, in the Gate 5/6/7 shape:
  - **`TestDesktopEndToEnd`** — one long CLI walk on a shared DB:
    `db init` → shop profile → member → customer → vehicle → work order
    → issue → parts add/order/receive → labour → complete → invoice →
    analytics. Every step a real `runner.invoke`, never a repo call —
    that distinction is precisely where Gate 8 was weak.
  - **`TestCrossSurfaceAgreement`** — re-read the CLI-created records
    through `TestClient` and assert field-level agreement: the work
    order, its parts and their statuses, the customer, the invoice
    totals. A disagreement here is drift between the two front doors of
    one database.
  - **`TestDesktopCannotFinishTheJob`** — assert, as executable
    documentation, that the four missing verbs are absent. These tests
    are expected to PASS today and to FAIL the day someone adds a verb,
    at which point the ticket gets closed and the test updated. A gap
    asserted is a gap that cannot be forgotten.
  - **`TestContractSnapshot`** — the committed `openapi.json` matches
    the spec `create_app()` generates: same paths, same methods, same
    operation ids. Guards the seam that silently breaks mobile.
  - **`TestRegression`** — subprocess re-runs of Gates 5/6/7/9/10 plus a
    `SCHEMA_VERSION` pin, mirroring `test_phase159_gate_7.py:540`.
- Findings written to the ledger, with new F-tickets only for gaps not
  already filed.

## Logic

1. Fixture builds a temp DB and runs `db init` through the CLI — the
   gate starts from nothing, as a new shop would.
2. The walk proceeds strictly through `runner.invoke`. Where a step is
   impossible from the CLI, the walk records it in a
   `missing_verbs` list and continues via the API so the rest of the
   scenario can still run — the list is asserted at the end.
3. Cross-surface reads use `TestClient` against the SAME db path.
4. The contract test compares the committed snapshot with the live spec
   structurally (paths/methods/operation ids), not byte-wise — a
   description edit should not fail the build.

## Key Concepts

- **A gate reports; it does not build.** Every prior gate shipped zero
  production code. Breaking that here would bury the findings under a
  feature build, and the findings are the deliverable.
- **Asserting an absence is legitimate documentation.** A test that
  pins "the CLI cannot do X" fails the day X arrives, which is the
  cheapest possible reminder to close the ticket.
- **Through the CLI, not through the repos.** Gate 8's weakness was
  calling repo functions and calling it a CLI gate. Every step here goes
  through `runner.invoke`.
- **Structural contract comparison.** Byte-comparing OpenAPI would fail
  on prose edits and get muted; comparing paths, methods and operation
  ids catches what actually breaks a generated client.

## Verification Checklist

- [ ] `db init` through the CLI produces a schema-48 database
- [ ] The full shop-owner walk completes through `runner.invoke` only
- [ ] Cross-surface: CLI-created records read identically via the API
- [ ] The four missing verbs are asserted absent, each citing its ticket
- [ ] Committed `openapi.json` matches the live spec structurally
- [ ] Gates 5/6/7/9/10 still pass as subprocesses
- [ ] Backend regression green; **zero production files changed**
- [ ] Findings recorded; new tickets filed only for unfiled gaps

## Risks

- **Scope creep into fixing.** The audit names this as the biggest risk
  and the user decision settles it: document. If a gap turns out to be a
  BUG rather than a missing feature, that is a different matter and gets
  its own fix commit outside the gate file.
- **A green, information-free suite.** Re-running Gates 5–10 without the
  new CLI walk would be slow and prove nothing new. The regression class
  is a guard, not the point.
- **The walk may not complete.** If the CLI cannot get from work order
  to invoice at all, the gate fails loudly and that IS the finding —
  the same posture Gate 10 took.
- **Snapshot staleness at authoring time.** If `openapi.json` is already
  stale, the contract test fails on arrival. That is a true positive and
  gets recorded, not worked around by regenerating first.
