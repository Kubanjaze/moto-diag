# Phase 205 — Gate 11: End-to-End Integration (Desktop + Mobile)

**Version:** 1.1 | **Tier:** Gate | **Date:** 2026-09-07 (plan → as-built same day)

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

- [x] `db init` through the CLI produces a schema-48 database
- [x] The full shop-owner walk completes through `runner.invoke` only —
      shop → customer → bike → work order → parts add/order/receive →
      start → complete → invoice → paid → analytics
- [x] Cross-surface: a CLI-created work order reads identically over
      HTTP (id, title, customer_id, shop_id, status)
- [x] The missing verbs are asserted absent — **five, not four**: the
      walk turned up one the audit had not predicted (`open`)
- [x] Committed `openapi.json` matches the live spec structurally, in
      BOTH directions. **Currently in sync** — a true negative worth
      recording, since this seam had never been checked at all
- [x] Gates 5/6/7/8/9 still pass as subprocesses (21s)
- [x] Backend regression **4799 passed, 0 failed** (8:40)
- [x] **Zero production files changed** — `git status --short src/`
      returned nothing, the constraint that defines a gate here
- [x] Findings recorded; tickets filed for the unfiled gaps

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

## Deviations from Plan

- **Five asymmetries, not four.** The plan listed install-part, labour,
  PDF and share link. Walking the CLI turned up a fifth: the API's work
  order transition accepts an `open` action while the CLI has only
  `start`. Harmless today, but two vocabularies for one lifecycle is
  how the F37 enum-drift family starts, so it is pinned.
- **The contract test passed on arrival.** The plan anticipated that a
  stale snapshot would be a true positive and get recorded. It was
  already in sync. Recorded anyway, because "we checked and it was
  fine" is a different claim from "nobody has ever checked", and this
  seam was the latter until now.
- **Two authoring corrections, both about testing behaviour rather than
  wording.** Ids are read from the database rather than parsed out of
  CLI output — `Added vehicle #1` is a sentence, not a contract, and a
  copy edit should not fail a gate. Absence tests interrogate click's
  command registry rather than grepping `--help`, after the first
  version failed because "time" appears inside "AI labor time
  estimation". Both were my errors, and both would have made the gate
  fragile in a way that eventually gets it muted.
- **The gate drives the REAL cli root.** Gate 8 built a partial root
  from `register_shop`, which structurally cannot catch a command that
  fails to register on the real one.

## Results

| Metric | Value |
|--------|-------|
| New tests | 16 (`test_phase205_gate11.py`) |
| Production files changed | **0** |
| Backend regression | 4799 passed, 0 failed (8:40) |
| Earlier gates re-run | 5 (Gates 5/6/7/8/9) in 21s |
| Asymmetries pinned | 5 |
| Contract snapshot | in sync, both directions |
| New tickets | F65 (labour CLI), F66 (report/PDF CLI), F67 (share CLI), F68 (`open` verb vocabulary) |

**Key finding: the desktop and the phone are not the same product.** A
phone-equipped shop can measure labour, print a report and text a
customer a link. A desktop-only shop can do none of those — it can only
*assert* hours, and hand over nothing. Every individual gap was known or
knowable, but nobody had walked the job end to end and seen that they
compose into a coherent hole rather than four scattered TODOs. That is
what an integration gate is for, and it is the same lesson Gate 10
taught from the other direction: the value is in running the whole thing
as a user would, not in testing the parts more thoroughly.

A secondary finding worth its own line: **Gate 8 did not gate what its
roadmap row claims.** Three CLI invocations against fifty-four repo
calls means Track G's shop commands were verified through the layer
underneath the surface they were supposed to prove. This gate is the
first time those commands have been driven as a user drives them.
