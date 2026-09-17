# Phase 209C — Closing a session updates what the shop remembers

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-17

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

- [ ] `POST /v1/sessions/{id}/close` compiles the session's vehicle, visible through `recall`
- [ ] `PATCH /v1/sessions/{id}` with `status: "closed"` compiles too, and sets `closed_at`
- [ ] Leaving `closed` by PATCH clears `closed_at`
- [ ] The CLI `diagnose` flow's close compiles the vehicle
- [ ] Reopen → edit diagnosis → close: the old diagnosis fact is superseded, the new one is live, recall shows only the new one
- [ ] Reverting the edit and closing again revives the original fact
- [ ] A removed symptom's fact is superseded at the next close
- [ ] Facts of other vehicles, and of origin tables compile doesn't read, are never superseded
- [ ] A compile that raises: the close still returns 200, the session is closed, a warning is logged
- [ ] A session with no vehicle closes without compiling
- [ ] Closing twice inserts nothing the second time
- [ ] An AI-authored diagnosis, edited, compiles as `model-generated` on close
- [ ] `motodiag memory compile` reports superseded/revived counts when non-zero, and its existing output is unchanged otherwise
- [ ] The reachability gate (209B) still passes; the new functions have callers
- [ ] A production-copy compile supersedes 0 facts (S0-6 still holds)
- [ ] Mutations: remove the hook; remove the PATCH routing; drop the supersede step; drop the revive step; let the refresh raise; widen supersede to all origin tables — each caught
- [ ] Full regression green

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
