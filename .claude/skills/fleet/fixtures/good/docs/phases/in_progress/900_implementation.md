# Phase 900 — The phase under review

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-04

---

## Goal

Add a widget check, as Step 0 (`900_step0.md`) found no such check.

## Logic

### 1. The check

A script reads each widget and fails on one with no owner.

### 2. Its test

A test plants a widget with no owner and watches the check fail.

## The change log's three newest entries

- **2026-10-03, a plain-language rule.** No check: the entry says it is
  text only.
- **2026-10-02, the deploy order.** The check it became:
  `checks/deploy_order_check.py`.
- **2026-10-01, live moves house.** The check it became:
  `checks/live_location_check.py`.

## Rule-1 stops anticipated

- A test that cannot be made green: the new check's own test.
- A login or a credential, if one is asked for.
- None expected from a live-database change: nothing reads live.

## Non-goals

- No path under `data/`, no seed data, no train/test split and no eval
  protocol: this section is not read for those.

## Planned items

- [ ] the check
- [ ] its test
