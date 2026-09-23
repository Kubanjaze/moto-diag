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

### 2026-09-22 23:35 — Tranche 1 write: SYM (one make, one commit)

Batch `SYM_20260922_232240`: both spellings found in the maker's own
manuals (digital-native PDFs, no OCR), entry_check clean, both refute
verdicts `kept` — refute re-pulled the PDFs' own text layer with pypdf,
quotes verbatim, spec tables matching the models. `stops` empty.

| spelling | before | after | entry |
|---|---|---|---|
| Wolf Classic 150 | unknown | model-sourced, manual | alias on the existing Wolf 150 entry |
| Wolf CR300i | unknown | model-sourced, manual | new entry, aliases incl. PF30A3-EU |

Census of record: **605 → 603** unknown spellings (SYM 7 → 5). New test
`tests/test_phase257_tranche1_writes.py` (7): every new spelling resolves
model-sourced/manual, the bare `wolf` alias is unmoved, and an unseen Wolf
spelling stays unknown. 244G raw-source scan over the new file: 19 pass.
Kymco and the D7 acquisition run were still in flight when this was
written; Honda queued behind them.

### 2026-09-22 23:38 — Tranche 1 write: Kymco (one make, one commit)

Batch `Kymco_20260922_232607`: K-Pipe found in the K-Pipe 125 owner's
manual (a **scanned** PDF), entry_check clean, refute verdict `kept` on
refute's own pypdfium2 render of spec page 57 (printed 56, landscape) —
the OCR layer was corroborating, not evidence, and its artifacts
('K-PIPE 1 25', footer '5556') were read against the image. `stops` empty.

| spelling | before | after | entry |
|---|---|---|---|
| K-Pipe | unknown | model-sourced, manual | new entry, aliases incl. T300-KB25KA-A |

Census of record: **603 → 602** (Kymco 11 → 10). Tranche tests now 10
(a Kymco class: the spelling, every alias, an unseen Kymco spelling
stays unknown). 166 pass across the tranche file, 244G and the 255
axis suite. Honda still in flight when this was written.

### 2026-09-22 23:44 — Tranche 1 write: Honda (one make, one commit)

Batch `Honda_20260922_233404`: both Grom spellings kept. The plan
expected the service manual's **page images** to carry the Grom because
its text layer is OCR; the batch found a strictly better source first —
Honda's own spec pages on disk (2018/2020/2022/2023/2025, digital text,
`ocr: false`), and refute verified the quotes against the source HTML.
The service-manual OCR corroborates and is deliberately not the
citation. `stops` empty.

| spelling | before | after | entry |
|---|---|---|---|
| Grom | unknown | model-sourced, manual | one entry, canonical Grom 125 |
| Grom 125 | unknown | model-sourced, manual | same entry (MSX125 codes as aliases) |

Census of record: **602 → 600** (Honda 28 → 26); tranche total
605 → 600, five spellings, as planned in D8.

One 255 test used the Grom as its example of an unknown machine:
`test_repeated_retrievals_accumulate` (the counter test). A
model-sourced machine is deliberately absent from the withheld report,
so the fixture moved to CBR1000RR (still unknown, still a named
over-reach machine) — the assertion is untouched. Tranche tests now 14.
387 pass across the seven touched suites. **Noticed while writing, and
handed to the operator:** the Honda findings cite `./evidence/grom*.txt`
— saved copies the model rendered from the on-disk HTML — and
entry_check E3 verified the quotes against those copies, not the
originals. A model that edits its own saved copy passes E3 today.
