# Phase 209C — Closing a session updates what the shop remembers

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-17 (built 2026-09-17)

---

## Goal

F79, decided by the operator on 2026-09-17 (209B → *Decisions §6*):
**recompile a machine's memory when a session closes.** Today per-machine
memory (Phase 244M) compiles only when someone runs `motodiag memory
compile`, so on a live server the history behind the vision prompt goes
stale.

The ticket reads as a one-line call. Step 0 found that making the call is
the easy half. Two things already in the code would turn "compile on every
close" into a steady source of wrong history, and those two are most of
this phase.

Numbered **209C**, after 209B, whose decisions it carries out. Phase 210
stays gated on the operator.

## Step 0 — findings

**S0-1. The hook point.** `compile_vehicle(vehicle_id, db_path)`
(`memory/compile.py`) is idempotent: a fact's identity is a hash of its
vehicle, kind, subject text, origin table and origin id, and inserts use
`ON CONFLICT(fact_key) DO NOTHING`. Its only caller is
`motodiag memory compile`. It takes **4–6 ms per vehicle** on a copy of
the production DB, so running it inside the close request is affordable.

**S0-2. 🚨 Editing and re-closing would leave the old text live.** Because
the subject text is part of a fact's identity, a changed diagnosis
compiles as a *new* fact, and the old one stays. `facts.py` describes the
fix — *"a later fact supersedes an earlier one by setting
`superseded_at` on it"* — and `list_facts` already hides superseded rows
from recall. **But nothing anywhere sets `memory_facts.superseded_at`.**
The only `superseded_at` writer in `src/` is for `video_analyses`.

So with compile-on-close, the operator's own flow from 2026-09-17 (reopen,
edit the diagnosis, close) would leave both the model's original prose and
the edited version in recall. The same applies to a removed symptom, a
superseded video analysis, and a deleted session: sessions 8 and 9 needed
their facts deleted by hand for exactly this reason.

**S0-3. There are two ways to close a session, and only one is the
function.** `close_session()` (`core/session_repo.py`) sets `status` and
`closed_at`, and every caller I found goes through it:

- the API route `POST /v1/sessions/{id}/close`, via `close_session_for_owner`
- the CLI's `diagnose` flows (`cli/diagnose.py` lines 350 and 446), which
  close the session when the diagnosis is done

But `update_session()` lists `status` among its allowed fields, and the
API's `PATCH /v1/sessions/{id}` accepts `status: "closed"`. That path
writes the status directly: **it never sets `closed_at`**, and it would
bypass any hook placed in `close_session`.

**S0-4. The CLI has `reopen` and no `close`.** `motodiag diagnose reopen`
exists (line 1184); there is no standalone close command. The CLI closes
sessions only at the end of a diagnosis. F79's "the CLI close" means those
two call sites.

**S0-5. Compile includes open sessions.** `_session_facts` reads every
session for the vehicle, whatever its status. All six production sessions
are `open`, and five of the 37 facts come from them. Restricting compile to
closed sessions would change what the manual compile produces and empty
today's session history. Not done here (see Non-goals). With S0-2 fixed, an
open session's facts follow its edits at the next compile anyway.

**S0-6. Production has nothing stale today.** On a copy of the production
DB, a full compile inserts 0 facts, and 0 of the 37 live facts would be
superseded. The reconciliation below changes nothing in the live data when
it first runs.

**S0-7. Memory is fed by more than sessions.** Feedback
(`diagnostic_feedback`, the only path to `mechanic-verified` for an
AI-involved session), video analyses that finish after the close, and
completed work orders all produce facts. Under the decided cadence, those
reach memory at the vehicle's next session close, or a manual compile.
Recorded rather than changed.

## Scope

1. **Supersede what compile no longer produces** (`memory/compile.py`,
   `memory/facts.py`).
   - After inserting, a vehicle's compile marks as superseded every live
     fact from a compiled origin table whose key it no longer produces.
   - A superseded fact whose key is produced again is revived (its
     `superseded_at` is cleared), so reverting an edit restores the fact
     rather than hiding it for good.
   - Only facts from the tables compile reads are touched, so nothing
     written by another path can be superseded by this one.
   - `compile_vehicle` keeps returning rows inserted; a new
     `compile_vehicle_detailed` returns inserted, superseded and revived.
     `motodiag memory compile` reports the extra counts when they aren't
     zero.
2. **One hook, at the one write path** (`core/session_repo.py`, new
   `memory/refresh.py`).
   - `close_session()` calls `refresh_after_close(session_id, db_path)`
     after its UPDATE commits.
   - The refresh is **best-effort**: any exception is logged with the
     session and vehicle ids and swallowed, so a compile failure never
     fails a close.
   - It skips sessions with no `vehicle_id`.
   - The memory module is imported inside the function, as this codebase
     does elsewhere, so `core` keeps no import-time dependency on
     `memory`.
3. **PATCH closes through the same function** (`update_session`). A
   `status: "closed"` update is routed through `close_session()`, so it
   sets `closed_at` and refreshes memory like every other close. Moving a
   session out of `closed` by PATCH clears `closed_at`, as
   `reopen_session()` already does. The 244N override capture on this
   route is left as it is.
4. **Tests through the entry points** (CLAUDE.md gate item 6), not the
   function:
   - `POST /close`, `PATCH status=closed`, and the CLI `diagnose` flow
   - the edit → re-close supersede, and revive on revert
   - a failing compile that still closes
   - a session without a vehicle
   - idempotence across repeated closes
   - the provenance rule: an AI-authored diagnosis stays
     `model-generated` after an edit

## Non-goals

- **F78** — shop attribution and the $25 cap. It's the next phase, with
  its two decisions recorded (mobile `cee05c7`).
- **Compile on other events** (feedback submitted, an analysis finishing, a
  work order completing). The decided cadence is session close. S0-7
  records the lag.
- **Excluding open sessions from compile** (S0-5). That would change what
  memory contains, which is a product call.
- **A CLI `close` command** (S0-4). Adding a command is feature work
  outside F79.
- **Background or async compile.** At 4–6 ms per vehicle it isn't needed.
- **No schema change.** `memory_facts.superseded_at` already exists.

## Verification Checklist

- [x] `POST /v1/sessions/{id}/close` compiles the session's vehicle, visible through `recall`
- [x] `PATCH /v1/sessions/{id}` with `status: "closed"` compiles too, and sets `closed_at`
- [x] Leaving `closed` by PATCH clears `closed_at`
- [x] The CLI `diagnose` flow's close compiles the vehicle
- [x] Reopen → edit diagnosis → close: the old diagnosis fact is superseded, the new one is live, recall shows only the new one
- [x] Reverting the edit and closing again revives the original fact
- [x] A removed symptom's fact is superseded at the next close
- [x] Facts of other vehicles, and of origin tables compile doesn't read, are never superseded
- [x] A compile that raises: the close still returns 200, the session is closed, a warning is logged
- [x] A session with no vehicle closes without compiling
- [x] Closing twice inserts nothing the second time
- [x] An AI-authored diagnosis, edited, compiles as `model-generated` on close
- [x] `motodiag memory compile` reports superseded/revived counts when non-zero, and its existing output is unchanged otherwise
- [x] The reachability gate (209B) still passes; the new functions have callers
- [x] A production-copy compile supersedes 0 facts (S0-6 still holds)
- [x] Mutations: remove the hook; remove the PATCH routing; drop the supersede step; drop the revive step; let the refresh raise; widen supersede to all origin tables — each caught
- [x] Full regression green

## Risks

- **A memory write inside the close request.** Mitigated: best-effort,
  4–6 ms, and the close's own UPDATE commits first, so a compile failure
  can't roll it back.
- **Superseding is a new kind of write to `memory_facts`.** Mitigated: it's
  scoped to the vehicle and to compiled origin tables, the facts' own
  documentation already defines it, and recall already honours it.
- **The PATCH route changes behaviour** for `status` updates: it now sets
  `closed_at`, which it silently didn't before. Any client relying on a
  PATCH-closed session having no `closed_at` would see a difference; none
  was found.

## Deviations from v1.0

**1. The close is guarded at the call site too.** v1.0 put the whole
"never raises" promise inside `refresh_after_close`. The PATCH route's own
comment records why that isn't enough: the override capture there is
guarded at the call site as well, because a promise kept only by the callee
is *"one refactor -- or one failed import -- away"* from failing the
request. `close_session` now wraps the import and the call. A test makes the
module unimportable (`sys.modules[...] = None`) and the close still returns
200.

**2. That guard could hide a broken refresh, so the refresh is tested
directly.** With two layers, removing the refresh's own `try` changes
nothing a route test can see: the outer guard catches the exception and the
close still succeeds. The first run of mutation M5 would have passed
silently. The route test now asserts the refresh's **own** log line
(`(vehicle N) failed; the close stands`), and three tests pin
`refresh_after_close` itself: it returns what changed, it never raises, and
an unknown session is a no-op.

**3. A PATCH to `closed` on a session already closed.** v1.0 said a move
*into* closed goes through `close_session`. Taken literally, a PATCH that
repeats `status: "closed"` does nothing, `update_session` returns False, and
the route answers **404**. The status is now rewritten in place: 200, and
`closed_at` kept rather than bumped. Pinned by a test, and by mutation M10.

## Results

| | |
|---|---|
| Close paths that refresh memory | **all of them**: `POST /close`, `PATCH status=closed`, and the CLI `diagnose` flows (2 call sites), through the one function |
| `closed_at` on a PATCH close | now set. It never was before. Leaving `closed` clears it. |
| Superseding | implemented for the first time (`reconcile_facts`): edited text, removed symptoms and deleted rows are retired; a reverted edit revives the original row |
| Scope of a supersede | the compiled vehicle, and only the six tables compile reads (`COMPILED_ORIGIN_TABLES`, held to the source by a test) |
| Failure behaviour | best-effort at two layers; a failing compile or an unimportable module leaves the close at 200 |
| Cost | 4–6 ms per vehicle, inside the request |
| Production copy | full compile: **0 inserted, 0 superseded, 0 revived** across 10 machines; still 37 facts, none superseded |
| `motodiag memory compile` | reports superseded/revived counts, and only when they're non-zero; unchanged output otherwise is pinned |
| Schema | unchanged (v60) |
| Tests added | **31**, all through the API routes or the CLI except the scoping and contract checks |
| Mutations | **15 of 15 caught** |
| Regression | **6,657 passed, 0 failed, 25:32** |

**Mutations**

| | mutation | caught by |
|---|---|---|
| M1 | `close_session` no longer calls the refresh | `test_the_close_route_compiles_the_machine` |
| M2 | PATCH writes `closed` directly | `test_a_patch_to_closed_compiles_and_sets_closed_at` |
| M3 | nothing is superseded | `test_reopen_edit_close_supersedes_the_old_diagnosis` |
| M4 | nothing is revived | `test_reverting_the_edit_revives_the_original_row` |
| M5 | the refresh lets exceptions out | the route test's refresh-specific log line, and `test_it_never_raises` |
| M6 | no call-site guard | `test_a_refresh_module_that_will_not_import` |
| M7 | supersede ignores the origin table | `test_a_fact_compile_does_not_own_is_never_retired` |
| M8 | supersede ignores the vehicle | `test_another_machines_facts_are_untouched` |
| M9 | leaving `closed` keeps `closed_at` | `test_leaving_closed_by_patch_clears_closed_at` |
| M10 | a repeated PATCH to closed bumps `closed_at` | `test_a_patch_to_closed_on_a_closed_session_keeps_its_closed_at` |
| M11 | status written before the edited fields | `test_a_patch_to_closed_writes_the_edited_fields_first` |
| M12 | a compiled table missing from the tuple | `test_the_compiled_tables_are_exactly_the_ones_compile_writes` |
| M13 | the CLI always prints retire counts | `test_an_unchanged_compile_reads_as_before` |
| M14 | the refresh compiles a session with no vehicle | `test_a_session_without_a_machine_closes_without_compiling` |
| M15 | the compile stops inserting | `test_it_returns_what_the_compile_changed` |

**Still as recorded in S0-7:** feedback, analyses finishing after the close
and completed work orders reach memory at the machine's next session close
or a manual compile. That is the decided cadence, not a defect.
