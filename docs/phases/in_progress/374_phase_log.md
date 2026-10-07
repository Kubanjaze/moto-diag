# Phase 374 — Check-in with an intake (F189) — phase log

**Status:** 🚧 In progress
**Branch:** `phase-374` (Opus session, main checkout)

---

### 2026-10-06 — Opened

The operator's prompt is `docs/prompts/374_check_in_with_an_intake.txt`
(merged `cdc6e07`). The last session's state is
`docs/handoffs/2026-10-06_373_closed.md`. Row 374 went 🚧 before Step 0
(`bda4a67`): `roadmap_check.py` exit 0, `wholetree.sh` fast exit 0 (1523
passed), pushed.

### 2026-10-06 — Step 0, and the stop

The record is `374_step0.md`. Every measured fact in the prompt
re-verifies, including live at 23:09 on a copy: schema 81, 0
appointments, 0 intakes, and 6 work orders, none with an intake. Two
findings of the reading:
- the packet uses the intake's mileage only in the coverage verdict, and
  prints neither it nor the reported problems;
- no option needs a schema change, so there is no migration 082 and no
  deploy.

The prompt asks for a stop at Step 0 with three questions. They were put
with the options in `374_step0.md` S0-3, recommending 1c, 2b and the
command line only.

**The operator's answer, verbatim:** "1c, 2b, 3 command line only. Two
conditions: link an open intake automatically only when exactly one
matches the shop, customer and bike and it was taken within a day of the
appointment; otherwise ask for --intake, and always print the linked
intake's date and mileage. And while an intake's mileage is unknown, the
claim packet says "not recorded" instead of falling back to the bike's
recorded mileage. Carry on."

**How "exactly one … within a day" is read:** exactly one open intake
matches the shop, customer and bike, and that one was taken within 24
hours of the appointment's start, either side. Two matching intakes are
refused even if only one of them is within the day. Of the two readings,
this is the stricter.

**The clock, found after the answer:**
- `intake_at` defaults to `CURRENT_TIMESTAMP`, which is UTC;
  `priority_scorer` reads it as UTC;
- an appointment's times are the shop's clock time with no offset;
- Gate 16's frozen clock does not reach `CURRENT_TIMESTAMP` (292 D2).

The comparison converts the intake's time to the shop's clock, and
`create_intake` takes its stamp from Python's clock in the column's own
UTC format (v1.0 D1). This is a decision, not a stop: live holds 0
intakes, and no stored value changes meaning.

### 2026-10-06 — v1.0

`374_implementation.md` v1.0: the operator's choices and conditions, the
logic, decisions D1–D5, and the planned items.

### 2026-10-06 — The build

- **`check_in`** (`scheduling/booking.py`) returns a `CheckIn`: the work
  order, whether it was opened, the intake, and whether check-in recorded
  it. `_intake_for_check_in` applies the operator's rule. `shop
  appointment check-in` gains `--intake`, `--mileage` and `--problems`.
  It prints `Intake recorded:` or `Intake linked:` with the intake's id,
  its date on the shop's clock, and its mileage or "not recorded". With
  `--wo` it prints the work order's intake, or says it has none.
- **`create_intake`** stamps `intake_at` from `datetime.now(timezone.utc)`
  in `CURRENT_TIMESTAMP`'s format (D1).
- **`work-order show`** prints the intake's label and reported problems.
  The intake is read in the CLI panel, not added to `get_work_order`,
  because the API's work-order routes return that dict as it is: the
  change stays on the command line (choice 3).
- **The packet** prints "Mileage at intake" and "Reported at intake".
  When the work order has an intake, the verdict uses the intake's
  mileage, unknown included.
- **Gate 16:** job A checks in first, then `intake update --mileage`; job
  B takes the intake first, and check-in links it. Both set the estimate
  with `work-order update`. `test_f189_…` is inverted. An eighth plant
  (F189 as it was: `create_work_order` called without the intake) is red
  on `assert j["wo_row"]["intake_visit_id"] == j["intake"]`, which was
  read from the traceback of a walk run by hand. The gate is 87 → 89
  collected tests (master measured in a scratch worktree). The old F189
  test ran once on its own database; the inverted one runs on both card
  walks, which adds two, and the plant adds one. With 275's booking and
  calendar tests, 128 passed.
- **`tests/test_phase374_check_in_intake.py`:** 26 passed. The one-day
  boundary is tested on both sides through UTC stamps: 24 h is linked,
  24 h and 1 min is refused. Without the zone conversion, the "a day
  either side" cases fail (mutation L4).
- **Mutations:** `374_mutate.py`, 20/20 red.
- **244G's scanner** over all of `tests/`: 0 hits.

**F191 filed** (finding skill; `next_f_number.sh` gave F191, and
`finding_check.py` exits 0). `_since_cutoff` compares a local-time
cutoff with UTC stamps in another format. Measured on a scratch
database at 23:26 EDT:
- an intake three hours old is listed under `--since 30m`;
- on a UTC clock, an intake made that minute is not.

It predates this phase, which does not touch `--since`, so it is not
fixed here. Live holds 0 intakes.
