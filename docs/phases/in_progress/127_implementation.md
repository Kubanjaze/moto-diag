# MotoDiag Phase 127 — Session History Browser

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Turn Phase 123's basic `diagnose list` into a proper history browser. Adds richer filtering (make/model/date-range/text search/limit), session reopen (closed → open for continuing a diagnosis), and annotation (append timestamped notes post-hoc without destroying the original diagnosis). One small migration for a `notes` TEXT column on `diagnostic_sessions` — append-only semantics preserve annotation history.

```
motodiag diagnose list                               # all sessions, newest first
motodiag diagnose list --make Honda --since 2026-04-01
motodiag diagnose list --search "stator"             # diagnosis LIKE search
motodiag diagnose list --vehicle-id 42 --limit 5
motodiag diagnose reopen 42                          # closed → open
motodiag diagnose annotate 42 "Follow-up: verified regulator fault"
```

Outputs: extended `cli/diagnose.py` (+~150 LoC), extended `core/session_repo.py` (+~20 LoC), migration 014 (notes column), ~25 new tests.

## Logic

### 1. Migration 014 — `notes` column
- `ALTER TABLE diagnostic_sessions ADD COLUMN notes TEXT`
- Nullable; existing rows get NULL.
- No index (free-text search uses LIKE; Phase 128's knowledge browser may add FTS later).
- Schema version 13 → 14.
- Rollback is a no-op documented as "column retained" (SQLite pre-3.35 ALTER TABLE DROP COLUMN limitation — same pattern as migration 005).

### 2. `session_repo.py` extension
- Extend `list_sessions()` with new optional filters: `vehicle_id`, `search` (LIKE on diagnosis), `since` (ISO date), `until` (ISO date), `limit`.
- New function `reopen_session(session_id, db_path) -> bool` — sets status = 'open', clears closed_at. Returns True if anything was updated.
- New function `append_note(session_id, note_text, db_path) -> bool` — prepends `[YYYY-MM-DD HH:MM] ` to note_text, concatenates onto existing `notes` with `\n\n` separator. Returns True if anything was updated.
- New function `get_notes(session_id, db_path) -> Optional[str]` — returns the notes column or None.

### 3. CLI extension in `cli/diagnose.py`

**`diagnose list`** — add options:
- `--vehicle-id INT`
- `--make TEXT` (already has via existing arg? check — current uses vehicle_make in sql, so expose as --make)
- `--model TEXT`
- `--search TEXT` — LIKE substring match on `diagnosis` column
- `--since YYYY-MM-DD` — sessions created on or after
- `--until YYYY-MM-DD` — sessions created on or before
- `--limit INT` default 50 (prevents terminal-spam on large histories)

Preserves existing `--status` option. All filters ANDed together. Empty result prints a yellow "No sessions match the filters" message.

**`diagnose reopen <session_id>`** — new command:
- Calls `reopen_session()`
- If missing session → ClickException
- If already open → yellow warning "Session N is already open; nothing to do"
- On success → green "Session N reopened"

**`diagnose annotate <session_id> <note>`** — new command:
- Calls `append_note()` with current timestamp
- If missing session → ClickException
- On success → green "Note added to session N" plus prints the full notes column (shows accumulated history)

**`diagnose show <id>`** — add `notes` field to every formatter (Phase 126 update):
- Terminal rendering: new Panel section "Notes" below "Result" when `session["notes"]` is non-empty
- `_format_session_text`: add `## Notes\n...` section (if notes)
- `_format_session_json`: include `notes` key in output (already would if using `dict(row)`)
- `_format_session_md`: add `## Notes\n...` section (if notes)

### 4. Testing (~25 tests)

- **`TestMigration014`** (3): migration exists, column present on fresh init, SCHEMA_VERSION >= 14 forward-compat.
- **`TestSessionRepoExtensions`** (8): list_sessions new filters (vehicle_id, search, since, until, limit), reopen_session happy + missing + already-open, append_note appends with timestamp + preserves prior notes + missing session.
- **`TestCliList`** (5): `--make` filter, `--search "stator"` finds session, `--since` date filter, `--limit 5`, empty-result message.
- **`TestCliReopen`** (3): happy path, missing session errors, already-open warning.
- **`TestCliAnnotate`** (4): happy path + prints accumulated notes, missing session errors, multiple annotations accumulate, special-character note handling.
- **`TestShowIncludesNotes`** (2): terminal rendering includes Notes panel when present, markdown formatter includes ## Notes section.

All tests use the `cli_db` fixture pattern. Zero AI calls. Zero live tokens.

## Key Concepts
- **Append-only notes**: annotations preserve history. `[YYYY-MM-DD HH:MM] text` prefix gives every note a provenance line mechanics can scan chronologically.
- **Reopen is just a status flip**: nothing magical — sets `status='open'` and clears `closed_at`. Diagnosis, confidence, repair_steps stay put. Mechanic continues from where they left off.
- **No new notes table**: a single `notes` TEXT column is enough for v1. Phase 175 (REST API) might upgrade to a real `session_notes` table with per-note user_id + timestamp rows if customer feedback demands structured history. For now, append-with-prefix is the YAGNI choice.
- **LIKE search is cheap**: no FTS index in this phase — Phase 128's knowledge browser can add FTS5 covering DTCs + known_issues + sessions if the search gets slow. At the projected session volumes (hundreds per mechanic per year), LIKE is fine.
- **Date filters on `created_at`**: the most intuitive field. `--since`/`--until` use ISO date strings which sort lexicographically against ISO timestamps.
- **Default `--limit 50`**: prevents a 500-session dump from spamming the terminal. Explicit `--limit 0` (or a future `--all`) can override if needed — for Phase 127, we just cap.
- **`notes` column retrofit plays well with existing formatters**: Phase 126 formatters take `dict`; adding a new field to the dict means the JSON formatter picks it up automatically, text/md formatters get one-line additions each.

## Verification Checklist
- [ ] Migration 014 creates `notes` column on `diagnostic_sessions`
- [ ] Fresh init produces notes=NULL for new sessions
- [ ] `list_sessions(vehicle_id=N)` filters correctly
- [ ] `list_sessions(search="stator")` finds sessions with "stator" in diagnosis
- [ ] `list_sessions(since="2026-04-01")` includes sessions from that date forward
- [ ] `list_sessions(until="2026-04-15")` excludes sessions after that date
- [ ] `list_sessions(limit=5)` returns at most 5 rows
- [ ] `reopen_session(id)` flips status to `open` and clears closed_at
- [ ] `reopen_session(missing_id)` returns False
- [ ] `append_note(id, "text")` prepends timestamp and concatenates
- [ ] `append_note(id, "note2")` preserves prior notes separated by `\n\n`
- [ ] `get_notes(id)` returns the raw notes string
- [ ] `diagnose list --make Honda` CLI filters correctly
- [ ] `diagnose list --search "stator"` CLI shows matching sessions
- [ ] `diagnose list --since 2026-04-01` CLI filters by date
- [ ] `diagnose list --limit 5` CLI limits output
- [ ] `diagnose list` with no matches prints yellow "No sessions" message
- [ ] `diagnose reopen <id>` CLI happy path + prints confirmation
- [ ] `diagnose reopen MISSING` CLI errors cleanly
- [ ] `diagnose reopen <already_open_id>` CLI prints warning
- [ ] `diagnose annotate <id> "text"` CLI appends + prints notes
- [ ] `diagnose annotate MISSING "x"` CLI errors cleanly
- [ ] `diagnose show <id>` terminal rendering includes Notes panel when present
- [ ] `diagnose show <id> --format md` markdown includes `## Notes` section
- [ ] Schema version assertions use `>= 14`
- [ ] All 2179 existing tests still pass (zero regressions)
- [ ] Zero live API tokens

## Risks
- **Annotation is append-only with no delete**: mechanic who typos a note can't delete it — only add corrections. Acceptable for v1; audit trail is a feature for shop-tier use cases.
- **Timestamp format in notes**: using local machine time. `datetime.now().isoformat(timespec="minutes")` gives `YYYY-MM-DDTHH:MM` without timezone. Multi-timezone shops (Phase 118's `appointments` table already has this concern) will need a timezone column later. Accepted.
- **`--search` LIKE is case-sensitive by default in SQLite**: use `LIKE` with `LOWER(diagnosis) LIKE LOWER('%...%')` for case-insensitivity. One extra `LOWER()` is free at this scale.
- **Forward-compat on existing Phase 123 tests**: `list_sessions` signature gets new kwargs. All must be keyword-only with defaults, and every existing caller must work unchanged. Tests will catch any break.
- **Migration 014 rollback is a no-op** (same pattern as migration 005's user_id column). Documented in the migration's `rollback_sql` as a comment; Gate R-style tests already handle this gracefully via "rollback drops retrofit tables" assertion (won't regress because Phase 127's migration doesn't add a table, just a column).
