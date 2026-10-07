# Phase 377 — Times stored in UTC across the shop's tables (F186, F191) — phase log

**Status:** 🚧 In progress
**Branch:** `phase-377` (Opus session, main checkout)

---

### 2026-10-07 — Opened

The operator's prompt is `docs/prompts/377_times_in_utc.txt` (merged
`4f47832`). The last session's state is
`docs/handoffs/2026-10-07_374_closed.md`. Row 377 went 🚧 before Step 0
(`991d54c`):
- 377 is the next free number;
- `roadmap_check.py` passed;
- `wholetree.sh` fast exited 0 (1523 passed);
- pushed.

### 2026-10-07 — Step 0, and the stop

The record is `377_step0.md` (`a92fe1e`). Every measured fact in the prompt
re-verifies. The prompt asks for three questions at Step 0. They were put
with options, recommending 1B, 2A and 3A:
1. the format and how comparisons are done;
2. the live rows;
3. the app.

**The operator's answer, verbatim:** "1B, 2A, 3A. Two conditions: "the
shop's day" is the server's zone today, since shops carry no timezone, so
say so in the log and file a finding for a per-shop timezone; the product
is meant for every state. And turnaround must not drop a work order
silently on a caught TypeError: make it fail loudly, or test that it can't
happen."

**Condition 1, recorded:** "the shop's day" in this phase is the server's
zone, because `shops` has no time-zone column. That covers every local
display, every day or month window, and every typed date read as local. It
is `astimezone()` with no argument in Python and `TZ` in tests. Filed as
**F192**, a per-shop time zone, before this entry cites it.

**Condition 2:** both, in v1.0 Logic step 5:
- turnaround and mechanic performance parse both times by one rule, so the
  mixed pair cannot raise;
- the catch-and-skip is removed, so a value that cannot be parsed raises,
  naming the work order;
- a test covers each.

**What 2A approves, read literally:** the choice to convert the 40 shop
fields with migration 082 and to leave known_issues. It does not approve a
diff. The deploy's exact dry-run diff, with 082's `schema_version` row, goes
to the operator before `apply-live`.

### 2026-10-07 — v1.0

`377_implementation.md` v1.0: the operator's choices and conditions, the
format, Logic steps 1–9 and the checklist.
