# Phase 244Y — Dead code leaves with its evidence — phase log

**Status:** 🚧 In progress
**Opened:** 2026-09-18

---

## 2026-09-18 — Plan v1.0

The instrument is finished; this is the first phase that acts on what it
reports. Step 0 was gathered read-only while 244X's regression ran: every
`superseded` entry across the three allowlist tables, plus the two engine
modules the audit named for deletion with no dissent. Seven modules and ten
defs, 1,846 source lines, each with a table entry naming its live
replacement and its line count printed in the plan before anything moves.

Two things Step 0 changed. The recall repo 244X had called a duplicate is
delegated to by the live one for a single function — the four orphaned
functions go, the file stays, and 244X's entries were corrected before they
were committed. And two one-line wrappers in `memory/compile.py` stay,
reclassified rather than deleted, because forty-five tests call one of them
and a one-line wrapper is not worth forty-five rewrites.

Three gate tests depend on candidates. Gate 3's definition was written when
the modules it imports were the track; the six tests that assert a dead
module is importable come out with a docstring saying so, and the plan says
so up front, because a gate test being edited is something to hear before
rather than after.
