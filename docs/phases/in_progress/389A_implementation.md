# Phase 389A — 385's ROADMAP row

**Version:** 1.1 | **Date:** 2026-10-25

## Goal

Add row 385 to `docs/ROADMAP.md`, not started, naming the finding it closes.

## Logic

One table row after 384's, status 🔲, naming its prompt and its finding.

## The change log's three newest entries

- 2026-10-22, `fleet` joins the procedure folders: no check (text only).
- 2026-10-20, rule 6, plain English to the operator: no check (text only).
- 2026-10-19, live is on the home desktop: `tests/test_phase382_live_location.py`.

## Rule-1 stops anticipated

- None expected.

## Tests

`tests/test_roadmap_continuity.py` runs the ledger check.

## Non-goals

Phase 385 itself.

## Planned items

- [ ] the row

## Deviations

None.

## Results

Row 385 added after 384's, not started. It names its prompt,
`docs/prompts/385_the_push_tokens_own_write.txt`, and the finding it
closes, F213: the API's own write of `device_tokens.last_seen_at`, which
`SERVER_WRITES` does not name.
