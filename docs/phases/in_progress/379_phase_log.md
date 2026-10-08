# Phase 379 — Small fixes from the open-findings triage — phase log

**Status:** 🚧 In progress (2026-10-08)
**Branch:** `phase-379` (Opus session, main checkout)

---

### 2026-10-08 — Opened

The operator, in this session: "approved: close the 11 now. 379 = the nine
small fixes. then 380 = F129 + F142, then the content batch. D, E and F stay
as the triage says." Section A was done first, on master (`0220fdf`): 11
closed, with their evidence re-measured, and F198 filed for the Filly,
which F119 still held. The prompt is `docs/prompts/379_small_fixes.txt`.
Row 379 went 🚧 before Step 0; `roadmap_check.py` exit 0.

### 2026-10-08 — Step 0 and v1.0

`379_step0.md`. Every finding re-measures. Three add to the triage:
- F176's delete is blocked by five tables, not two;
- a Fiddle 50 service manual is on disk, its cover rendered with Quick
  Look;
- `VehicleContext` is not in the mobile snapshot, so F144 should need no
  mobile session.

No fork, so no stop. The decisions are in S0-2.

The first fast run before v1.0's commit went red on B2: v1.0 and Step 0
cited F199 before it was filed. F199 was then filed with the finding
skill, before any commit. Rule 6's "file before citing", caught by B2,
which is the check working.

### 2026-10-08 — The build

Each finding with its fix and its test (`379_implementation.md` names
them):
- **F197:** `verify-live` exits 3 on a mismatch, naming a later migration
  when live's schema is past the phase's. Check 8 fails verify_phase on 1
  or 3. On live, `verify-live 375` exits 0, and `verify-live 376` exits 3:
  "live is at schema 84, past this phase's 83".
- **F176:** `vehicle_dependents` reads the blocking tables from the
  schema, and `garage remove` names them and exits 1. The API's delete
  already answered 409, so it was left as it was.
- **F193:** `core.timestamps.column_cutoff`, used by `list_recordings`,
  `compute_trend` and the drift chart. Both drift commands' window check
  now parses instead of comparing the typed text.
- **F154:** a `SYM Fiddle 50` lookup entry, cited to its own service
  manual.
- **F155:** `_singular` in `relevance_tokens`.
- **F131:** resolution matches each entry's canonical name; all 122
  resolve to themselves (the control: exactly F131's six did not).
- **F140:** a check over a built database, with a planted row.
- **F173:** `wholetree.py` keeps the whole output.
- **F144:** `VehicleContext.powertrain`.

**Decisions taken while building, not stops:**
- **D1. F155's wider effect.** Measured over 22 machines and 6 symptoms
  (`379_f155_measure.py`, the moved rows in `379_f155_swaps.txt`): 51 of
  132 prompts change by one or two rows in the slots kept for the rider's
  words.

  Read title by title, about 19 swaps are better, 16 neutral and 5 worse:
  - Road King charging loses the voltage-regulator row ("lights" now meets
    "warning light");
  - the CBR600RR and Ruckus leak prompts take a shaft-drive row;
  - the CBR1000RR cold start loses its enrichment row;
  - the PCX150's stall prompt loses its fuel-pump row.

  The operator approved the fix, and the net is positive, so it shipped.
  The scorer's word-sense noise is filed as **F200**, so it is tracked, not
  absorbed.
- **D2.** Gate 14's six F154/F155 pins were inverted to what was measured:
  - the Fiddle 50 fills its prompt (9 → 12; 7 CVT rows, the naming row
    among them, the recall-index row now outranked);
  - the LX 50 keeps its carburettor row (CVT 10 → 9, CARB 0 → 1).

  No other machine's census moved under gate 14's belt symptom.
- **D3.** Two other pins moved with the change:
  - 250B's token test, "overheats" → "overheat" (F155, as intended);
  - 256's dynamic-table pin, `core/timestamps.py:214` → `229`, the same
    082 query moved by `column_cutoff`.
- **D4.** F131's pin
  (`test_the_canonical_name_gap_is_recorded_not_silently_worked_around`)
  no longer exists anywhere in `tests/`, so there was nothing to invert.
  The new guard covers every entry.
- **D5.** F144's new query absorbs only `sqlite3.OperationalError`, where
  257B's transmission query absorbs any exception.

**Checks:**
- mutations 16/16 red (`379_mutate.out`; F140's check is a test with its
  own planted control);
- 244G scanner 0 hits, its control reported;
- `COLLECTED_TEST_FLOOR` 10723 → 10769, by a diff of collected ids against
  `0220fdf`;
- every test file touching retrieval, the lookup or composition (35
  files): 2198 passed, 2 failed before D3, then both passed;
- the sensor and drift files: 1703 passed.
