# Phase 374 — Check-in with an intake (F189)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-07 (v1.0 2026-10-06)

---

## Goal

Row 374: "Give check-in a way to link or create the intake, so book →
intake → work order holds in either order." It closes F189: `shop
appointment check-in` without `--wo` opens a work order with no intake,
and nothing can attach one afterwards, so the intake's mileage and
reported problems never reach that work order or its warranty claim
packet.

The operator's choices at Step 0 (verbatim in the phase log):
1. **Both (1c):** check-in links an open intake, or creates one.
2. **No intake details (2b):** check-in creates an intake with the
   mileage unknown.
3. **The command line only.** No API model changes, so no mobile stop.

And two conditions:
- **Automatic linking:** only when exactly one open intake matches the
  shop, customer and bike, and it was taken within a day of the
  appointment. Otherwise check-in asks for `--intake`. The linked
  intake's date and mileage are always printed.
- **The claim packet:** while an intake's mileage is unknown, the packet
  says "not recorded", and does not fall back to the bike's recorded
  mileage.

## Logic

### `check_in` (`scheduling/booking.py`)

`check_in(appt_id, work_order_id=None, intake_id=None, mileage=None,
problems=None, ...)`. It returns the work order, whether check-in opened
it, the intake (or none) and whether check-in created it.

- **`--wo`** links a work order exactly as today. It cannot be combined
  with `--intake`, `--mileage` or `--problems`: the work order keeps the
  intake it was created with. The output names that intake's date and
  mileage, or says the work order has no intake.
- **`--intake ID`** links that intake. It must be open, with the
  appointment's shop, customer and bike. Its date is not checked, because
  staff chose it. It cannot be combined with `--mileage` or `--problems`:
  the intake already exists, and `shop intake update` changes it.
- **Neither:** the candidates are the open intakes with the appointment's
  shop, customer and bike.
  - **None:** check-in creates an intake: the shop, customer and bike
    from the appointment, the mileage from `--mileage` (else unknown),
    the reported problems from `--problems` (else the appointment's
    notes), and the taker is the check-in's user. The output names the
    intake and, while the mileage is unknown, the command that records
    it.
  - **Exactly one, taken within a day of the appointment** (|taken −
    scheduled start| ≤ 24 h, both on the shop's clock): linked. With
    `--mileage` or `--problems` given, it is refused instead, naming the
    intake and `shop intake update`.
  - **Otherwise** (two or more, or one taken further away): refused. The
    message lists each candidate's id, date and mileage, and asks for
    `--intake ID`, or for the ones that are not this visit to be closed
    with `shop intake close`.
- **The work order** opened by check-in carries `intake_visit_id`, set at
  creation through `create_work_order`'s existing consistency check. The
  rule that a work order's intake cannot be changed afterwards stands.

### The intake's time

`intake_visits.intake_at` is UTC: its default is SQLite's
`CURRENT_TIMESTAMP`, and `priority_scorer` reads a naive value as UTC.
An appointment's times are the shop's clock time, with no offset
(`booking.py`'s module docstring).
- **`create_intake` stamps `intake_at` from Python's clock**, in UTC and
  in the same format (`YYYY-MM-DD HH:MM:SS`), when none is given. The
  meaning is unchanged, and a frozen clock now reaches the stamp.
- **For the one-day comparison and for display**, `intake_at` is
  converted to the shop's clock through the machine's zone. Check-in's
  `actual_start` already uses the same clock.

### The work order

`get_work_order` also selects the intake's mileage. `shop work-order
show` prints the intake's id, date, mileage and reported problems where
it printed only the id.

### The claim packet

When the claim's work order has an intake:
- the packet prints "Mileage at intake: N mi", or "not recorded";
- it prints "Reported at intake: …" when the intake has reported
  problems;
- the coverage verdict uses the intake's mileage. When that is unknown,
  the verdict reads "cannot tell", never the bike's recorded mileage.

When the work order has no intake (the 6 live work orders, or one linked
with `--wo` that has none), the packet is unchanged.

### Gate 16, both orders

- **Job A (the covered job), check-in first.** `book` → `check-in` (which
  creates the intake, mileage unknown) → `intake update --mileage` → the
  estimate (`work-order update --set estimated_hours=…`) → the warranty
  check.
- **Job B, intake first.** `intake create` → `check-in` (which links it
  automatically) → the estimate.
- **Each job's work order** carries its intake, at the job's mileage.
- **Job A's packet** prints the mileage at intake, and the reported
  problems from the appointment's notes.
- **`test_f189_…` is inverted:** each work order holds its intake in its
  order, and the check-in printed the intake's date and mileage.
- **An eighth plant, F189 itself:** check-in's work order is opened
  without the intake. It must turn the inverted test red.

## Decisions

- **D1. The intake keeps UTC.** That is the column's convention, and
  `priority_scorer` relies on it. Only the source of the stamp changes.
- **D2. A closed intake is never a candidate,** and `--intake` refuses one:
  the visit it records is over.
- **D3. No new flag to force a fresh intake.** When an open intake stands
  in the way, staff link it with `--intake` or close it.
- **D4. When check-in creates the intake,** the reported problems default
  to the appointment's notes, the problem the customer booked with.
- **D5. An intake for the same bike with another customer or shop** is
  not a candidate. It does not stop check-in creating one, which prints
  the same warning `intake create` gives.

## Non-goals

An API route for appointments or check-in. Changing the 6 live work
orders. Attaching an intake to an existing work order (option 1d). Closing
intakes automatically.

## Planned items

- [x] `check_in` with `--intake`, `--mileage` and `--problems`; automatic linking under the operator's condition
- [x] `create_intake` stamps `intake_at` from Python's clock (UTC)
- [x] `work-order show` prints the intake's date, mileage and problems
- [x] the packet: the mileage at intake, "not recorded", the reported problems
- [x] Gate 16 walks both orders; `test_f189_…` inverted; the F189 plant
- [x] `tests/test_phase374_check_in_intake.py`
- [x] a mutation file, the regression, the close-out; F189 closed

## Deviations from Plan

- **`work-order show` reads the intake in the CLI panel.** The plan put
  the mileage in `get_work_order`'s query. The API's work-order routes
  return that dict as it is, so a new key would have reached the app's
  payloads. Reading it in the panel keeps the change on the command line
  (choice 3).
- **Gate 16 is 87 → 89, not 88:** the inverted F189 test runs on both card
  walks, where the old one ran once on its own database.
- **The intake's time (D1) came from reading the code after the
  operator's answer**, not from Step 0's own reading. It is recorded in
  the log as a decision: no stored value changes meaning.
- **F191 was not planned.** It was found while reading `intake_at`'s
  clock and filed, not fixed: `--since` mixes the shop's clock and UTC,
  and this phase does not touch `--since`.
- **No bug fix, no migration, no deploy, no refute pass.**

## Results

| | |
|---|---|
| Check-in | `shop appointment check-in APPT [--intake ID \| --mileage N --problems TEXT \| --wo WO]`. It links the named intake, or the one open intake for the shop, customer and bike taken within a day of the appointment; with none open, it records one (mileage unknown unless given, problems from the booking's notes); otherwise it refuses and lists them. It prints the intake's id, date and mileage. |
| Either order (Gate 16) | Job A: `book` → `check-in` (intake recorded, mileage not recorded) → `intake update --mileage 31200` → claim; packet "Mileage at intake: 31,200 mi", "Reported at intake: Front brake squeals and pulls left", the verdict at 31,200 of 40,000 mi. Job B: `intake create` → `check-in` (intake linked, 22,400 mi). Both work orders carry their intake; no `work-order create` in the walk. |
| Unknown mileage | The packet says "Mileage at intake: not recorded" and the verdict "cannot tell", where the bike's 52,000 mi would have read as over the limit (`test_phase374`) |
| Test files | `tests/test_phase374_check_in_intake.py` (26); `tests/test_phase292_gate16.py` 87 → 89 |
| Mutations | 20/20 red (`374_mutate.py`) |
| Findings | F189 closed; F191 filed |
| Migration | none; live unchanged (0 appointments, 0 intakes, 6 work orders without an intake) |
| Floor | 10556 → 10584 |
| Regression of record | **10584 passed, 0 failed, 0 skipped, 0 errors** at `15d16db` (26 min 2 s wall, `python -m pytest -n auto --dist load`, exit 0) |

## Risks

- **The shop's clock is the machine's zone.** Check-in already uses it
  for `actual_start`. A server in another zone from the shop would shift
  the one-day test by the difference. The shop records no zone.
- **An intake recorded before this phase** carries SQLite's UTC stamp, in
  the same format, so it reads the same. Live has none.
- **F191:** `--since` lists and counts can be off by the UTC offset.
- **Neither the API nor the app can check in** (choice 3). A route would
  need appointment routes and a mobile stop.
