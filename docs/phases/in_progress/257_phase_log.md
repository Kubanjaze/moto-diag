# Phase 257 — The orchestrator and `/source-transmission` — phase log

**Status:** 🔄 In progress
**Opened:** 2026-09-22

---

### 2026-09-22 23:30 — v1.0 committed before any code

Step 0 (`257_step0.md`) measured the census of record, acquisition (0 of 10
makes yield the maker's word in one fetch), and proved the write boundary
with planted attempts — including with `claude -p` itself sandboxed and all
permissions bypassed. Operator decisions folded in: Claude Code throughout
(no GLM), 257 keeps its number and the carb row moves to 353.

### 2026-09-22 23:45 — Build slice 1: the boundary and the guards, both tests; v1.1

`sandbox.sb.tmpl`, `orchestrate.py`, and two tests:
`test_phase257_sandbox_boundary.py` (12 — planted writes, a push into this
repository, the token file, the keychain credential with a live control
that it exists outside) and `test_phase257_orchestrator_guards.py` (30 —
every D3 guard with a planted violation, including the real 2026-09-22
bracketed-token file). Break-it: route guard disabled → 10 fail; keychain
denial removed from the profile → the keychain test fails. Restored: 42 pass.

v1.1 records the Subconscious route (operator's intent, measured before
adopting).

### 2026-09-22 23:55 — Build slice 2: census and entry_check, the two no-model steps

`census.py` reproduces the figure of record on the live database: **605**
unknown spellings. `entry_check.py` rejects eight evidence classes (E1–E8),
each checked against the document text rather than the model's account —
E3 catches a quote altered from 5-speed to 6-speed that reads perfectly.
Hand-written fixtures: the bad set fires every class, the good set passes.
`test_phase257_source_checks.py`: 13. Break-it: E3's document check
disabled → 2 fail. All 257 tests: 55.

**Noticed, not acted on:** SYM's unknowns include Jet 14, Fiddle 4 and
SYMBA 110, whose owner's manuals are already on disk — CVT and centrifugal
machines. Tranche 1 stays as the operator defined it (manual gearboxes); a
make-level SYM batch picks these up.
