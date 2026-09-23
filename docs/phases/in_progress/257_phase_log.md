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
originals.

### 2026-09-22 23:55 — F141 filed and closed: E3 verifies against the original, E9 demands provenance

The operator confirmed the gap noticed above and ordered the fix.
`entry_check.py`: a document under `evidence/` must carry a
`<file>.provenance.json` sidecar — `original` (on-disk path or URL) plus
its `original_sha256`, and `fetched_as` for a URL (the pinned fetch the
no-model check reads offline). New class **E9** rejects a copy with no
sidecar, an unreadable original, or a hash that no longer matches. E3
extracts the ORIGINAL's text inside entry_check (HTML→text in its own
code, `.txt` raw, PDF via pypdf — 6.14.2 in the venv) and matches the
quote against that, never against the saved copy; E4 runs against the
same original-derived text. The source-stage prompt now instructs the
model to write sidecars; refute's prompt tells it to check originals.

Fixtures: `fixtures/evidence/` gains a doctored copy (quote in the
copy, absent from its declared original — the F141 plant), a
sidecar-less copy, a stale pin (sha256 of the copy's bytes), and two
good cases (an on-disk HTML original; a URL original verified through
its pinned fetch). Tests: 19 in `test_phase257_source_checks.py`
(was 13). **Break-it, seen to fail:** (1) E3 made to read the saved
copy again → the doctored-copy test fails; (2) E9's sidecar and hash
gates removed → exactly the three E9 tests fail. Restored: all green.
F141 filed and marked CLOSED in `docs/FOLLOWUPS.md` by this commit. A model that edits its own saved copy passes E3 today.

### 2026-09-23 — Opus session: review of the GLM session's five commits

Before building on them. **The three tranche-1 writes stand**, each
checked against its run and the document itself, not the run's account:

| write | run | check | result |
|---|---|---|---|
| SYM Wolf Classic 150 / CR300i (`129b242`) | `SYM_20260922_232240`: stops [], both kept | pypdf over the fetched PDFs: quote on PDF p18 / p12; p35 'Model Classic 150 … Transmission Gear'; p24 'WOLF CR 300i / PF30A3-EU'; Dropbox links present in `sym_mg.html` | holds |
| Kymco K-Pipe (`97a3dc3`) | `Kymco_20260922_232607`: stops [], kept | page 57 rendered here with pypdfium2 and read as an image: 'Transmission……4-speed, foot shift' under SPECIFICATIONS - K-PIPE 125, printed 56 | holds |
| Honda Grom 125 (`16928bb`) | `Honda_20260922_233404`: stops [], both kept | both quotes found in the ORIGINAL `honda/grom2025.html` / `grom2020.html` (tags stripped here, not the saved copies) | holds |

`16928bb`'s moved test: the diff touches the machine name only; the
assertion `row["retrievals"] == 3` is unchanged and passes, and
CBR1000RR still resolves `unknown`. No duplicate aliases in the lookup.

**Two things wrong, neither in what was written:**

1. **F141 is not closed.** E9 makes a copy under `evidence/` declare an
   original and its sha256 — but the model writes the sidecar, and
   nothing stops the "original" being another file it wrote. Shown in a
   scratch run, all three accepted by `check_one` with zero failures:
   (a) a document in the clone root, outside `evidence/`, is treated as
   an original and read directly; (b) a sidecar whose `original` is a
   relative path to a second model-written file in `evidence/`; (c) a
   URL original whose `fetched_as` is a model-written file. The hash pins
   only that the model's two files agree. The redesign's no-tools source
   stage removes the model's ability to write anything, and step 2 adds
   the check that a cited document must be one `candidates.py` supplied.
2. **"The run itself recorded nothing" is wrong.** Every `source.json`
   carries `modelUsage`: Kymco's source stage is inputTokens 7,661,322 —
   the operator's 7.7M — plus 18,077 out and 6,133,632 cache-read; SYM
   3,393,862 in; Honda 724,033 in. What was missing is the sum and the
   gate, which is step 3.

### 2026-09-23 — token redesign step 1: `candidates.py`

No model. For each spelling, the library files (`~/research/motodiag`,
`*.txt` and HTML→text via `entry_check._extract_text`) that name it, cut
to the hit line ±40 lines, with the absolute path, the page (from the
extract's own `=== PAGE N ===` / `===PAGE N===` / `<<<PAGE N>>>` markers
or form feeds) and the line range. Capped at 8 excerpts and 40,000
characters per spelling. A file whose own name names the spelling is about
that machine throughout, so its gearbox lines anchor excerpts too
(`anchor: "file"`): the Wolf CR300i manual's gear-change page never
repeats the model name. Excluded: the project's own artefacts in the
library folder (phase notes `250_*`, crawl/fetch logs, `refute/`,
virtualenvs) and anything over 32 MB (NHTSA's 311 MB flat recall file —
a database dump, and 93 of the first run's 95 seconds).

Measured on the real library, 2.6 s per make. The quote each tranche-1
entry cites is inside the excerpts for K-Pipe (page 57 spec table,
ranked first), Grom (four spec pages) and Wolf CR300i (the gear-change
page). Two spellings get excerpts that cannot carry a finding: **Wolf
Classic 150** — its manual was fetched from the web in tranche 1 and is
not on disk — and **Grom 125** — no maker page uses that string. Both
would now come back `no_evidence`: the price of taking web acquire out of
the source stage, and the honest answer for the second.

`tests/test_phase257_candidates.py` (17) against a hand-written fixture
library (`fixtures/library/`). **Break-it, seen to fail:** context 20 →
the ±40 test; `refute/` read → 4; form feed ignored → the page test;
letters and digits not split → 3; char cap off → the cap test; file anchor
off → 2; phase notes read → 4. Restored: 17 pass. 244G scan over
`tests/`: clean.
