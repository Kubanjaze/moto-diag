# Phase 374 — Check-in with an intake (F189)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-06

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

- [ ] `check_in` with `--intake`, `--mileage` and `--problems`; automatic linking under the operator's condition
- [ ] `create_intake` stamps `intake_at` from Python's clock (UTC)
- [ ] `work-order show` prints the intake's date, mileage and problems
- [ ] the packet: the mileage at intake, "not recorded", the reported problems
- [ ] Gate 16 walks both orders; `test_f189_…` inverted; the F189 plant
- [ ] `tests/test_phase374_check_in_intake.py`
- [ ] a mutation file, the regression, the close-out; F189 closed
