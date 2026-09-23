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

### 2026-09-23 — token redesign step 2: one turn, no tools; E10

`orchestrate.batch` now runs `candidates.py` first and writes
`candidates.json` into the run. A spelling with no excerpt gets a
`no_evidence` finding and **no model call**. The rest go to the source
stage in ONE call with `--tools "" --strict-mcp-config
--disable-slash-commands`; the prompt carries the excerpts as JSON and no
browsing, web or `evidence/` instructions. A no-tools call with
`--json-schema` reports `num_turns` 2 (measured once on Haiku, local
login, not Subconscious); more than `SOURCE_MAX_TURNS = 2` is a source
error and a stop. `summary.json` gains `sent_to_model`.

`entry_check` **E10** (given the excerpts): the finding's document must be
one of the excerpts supplied for its spelling and the quote must sit
inside them. E3 reads a library original through `_extract_text`, so a
cited HTML page is matched as the text the stage saw. F141 reopened and
re-closed in `docs/FOLLOWUPS.md` (see the review entry above).

Tests: `test_phase257_source_stage.py` (7) drives the real `batch` with
`subprocess.run` faked — no model; `test_phase257_source_checks.py`
19 → 25 (E10 plants in the hand-written `fixtures/excerpts.json`, a
library-HTML case). **Break-it, seen to fail, one test each unless
noted:** tools flags removed; model called without excerpts (2); findings
not bound to excerpts; turn limit off; E10 document check off; E10 quote
check off; library read raw instead of as text. Restored: 158 pass across
255D contracts + 257. 244G scan: clean.

### 2026-09-23 — token redesign step 3: token accounting and the 150K stop

`orchestrate.usage(out)` sums each stage's `modelUsage` (input, output,
cache-read, cache-creation) into `summary.json` → `tokens`: per stage,
total, the number of spellings sent, the ceiling, the stop. The stop,
`TOKEN_STOP_PER_SPELLING = 150_000` — the operator's ceiling, a constant,
no CLI option — is checked after the source stage (**over budget →
refute is not spent**) and again after refute, and added through
`stops()`. The ceiling is 150K × spellings *sent to the model*: a
`no_evidence` spelling costs nothing and must not lend its 150K to the
rest. A stage with no recorded usage is a stop (cannot show it is under).

Caveat recorded in the code: the total adds cache reads to input. For
Anthropic they are separate; the Subconscious gateway's `inputTokens` may
already include them, so the total can overcount there — early, never
late. **The before figure, from the run's own record**
(`fixtures/kymco_source_usage.json`, copied from Kymco's `source.json`):
7,661,322 input + 18,077 output + 6,133,632 cache-read = 13,813,031 by this
count; 7,661,322 by input alone (the operator's 7.7M). Either is ~51× the
ceiling for one spelling.

Tests: `test_phase257_source_stage.py` 7 → 15. **Break-it, seen to fail:**
ceiling ×10 → 4; refute not counted → 2; ceiling per spelling asked
instead of sent → 1 (a first version of that test survived it: it did not
check refute was skipped — tightened); unrecorded usage accepted → 1;
refute run over budget → 1; stop not passed through `stops()` → 4; cache
tokens not counted → 1 (survived at first too — no test fed cache
tokens; added). Restored: all pass.

Handoff step 4 (fixtures + break-it) was done inside steps 1–3, each
against its own hand-written fixtures. Step 5, the Kymco re-run, waits for
the Subconscious reset.

### 2026-09-23 — three leaks in what reaches the model, closed (operator's review of step 1)

The operator measured real `candidates.py` output: Yamaha "Bolt" → eight
excerpts from Yamaha's own Zuma 125 / YZ125 service manuals (the fastener
word, one excerpt with "V-belt"); Harley-Davidson "One" → `cp.html`,
`makes_raw.txt`; Ducati "1000" → SYM/Kymco scooter manuals, "Clutch
Centrifugal type". A spelling matched as a word in ANY file; the make only
ranked. Nothing behind it stopped the Bolt case — same make, a Yamaha
manual (E2), "V-belt" (E5), the quote on the page (E3), inside the excerpt
(E10); E4 passed on the fastener. Only refute stood between a GLM answer
and a `cvt` entry for a manual cruiser. **My "220 of 600 have an excerpt,
98 with a gearbox word" count from this morning was built on exactly this
and is withdrawn** — the F139 trap in code.

1. **The make is a filter.** `candidates.py` reads a document only if it
   names the make (`entry_check.MAKE_NAMES`: full names where the bare one
   is an ordinary word — "Genuine" is every manual's "genuine parts").
2. **Strict E4 for weak spellings** — no token mixing letters and digits
   and fewer than two real words (Bolt, One, 1000, RS, Monster 821,
   K-Pipe): the document must name it AS A MODEL — right after the make
   ("Yamaha Bolt"), as a strong alias of a lookup entry it already belongs
   to, in the document's first three non-marker lines (its title), or in
   its file name. `candidates.py` applies the same rule before paying the
   model to read — the make filter alone cannot stop Bolt, which is the
   make's own manual.
3. **E2 from an index.** New `library_index.py`: an ordered, hand-written
   table of path rules, first match wins; unmatched is `unindexed` and is
   not evidence. Every library file was read and classed:
   maker_site_page 697, maker_manual 579, crawl_artefact 54, recall 28,
   maker_spec_page 26, third_party 4, regulation 2, **unindexed 0**. For a
   library file E2 uses the index's kind and never consults the model's
   `evidence_kind`; `candidates.py` reads maker kinds only.

**Controls on the real library, after:**

| | spelling | before | after |
|---|---|---|---|
| negative | Harley-Davidson "One" | cp.html, makes_raw.txt | **0** |
| negative | Ducati "1000" | SYM/Kymco scooter manuals | **0** |
| negative | Yamaha "Bolt" | 8 (Zuma/YZ125) | **0** |
| positive | Kymco K-Pipe | cited excerpt (p57) | cited excerpt |
| positive | SYM Wolf CR300i | cited excerpt (gear change) | cited excerpt |
| positive | Honda Grom | grom2025 spec | grom2025 spec |
| positive | SYM Wolf Classic 150 | **not present** | not present |
| positive | Honda Grom 125 | **not present** | not present |

The last two were not present before these fixes either (measured at step
1): no library text contains "Wolf Classic 150" (the manual's spec page
says "Model Classic 150" under "WOLF SERIES") or "Grom 125". The agent loop
reached both by reasoning across names. A string rule should not, so a
from-scratch re-run of those two would now be `no_evidence` — the price
of not letting a model browse, recorded, not fixed.

Tests: candidates 17 → 23, source checks 25 → 45 (index rules pinned
against real paths without reading the library). **Break-it, each seen to
fail:** make filter off (1); index filter off (5); strict E4 off (1); title
window 15 lines (1 — the fixture had first been too short to tell, and
was given real front matter); make-adjacency off (5); E2 trusts the
model's kind (3); unindexed defaults to maker (2); Cyclepedia rule removed
(2); the weak rule off in candidates (2). 199 pass across 257 + 255D
contracts; 244G clean.

### 2026-09-23 — census classes: spellings that cannot be a machine (fix 4); coverage re-measured

`census.not_a_machine(make, spelling)` by named lists: `bare_number`
(digits, optionally `cc`), `other_marque` (starts with another marque's
name — `MARQUES`: the junction's makes plus Gilera, Husqvarna, Moto
Morini, Cagiva, Benelli, Bimota), `marque_name` (the make's own name, MV
Agusta `MV`), `prose` (F135: `PROSE_WORDS`, each seen in the junction).
The census count stays the figure of record (600); `census.py` prints the
classes per make. `batch` gives a classed spelling `no_evidence` with its
class in the note, **searches nothing and calls nothing**, and lists it
under `not_a_machine` in the summary.

**Classed: 116 of 600** — bare_number 46, other_marque 39, prose 30,
marque_name 1. **Operator decision needed:** `bare_number` takes real
machines — Ducati's superbikes are *named* by number (916, 748, 749, 848,
851, 888, 899, 959, 996, 998, 999, 1098, 1198, 1299) and Vespa/Piaggio
`946` is a model. Built as specified; a named per-make exception list
would return them to `machine`, where strict E4 already demands
"Ducati 916" (make-adjacent) before anything counts.

Tests: source checks 45 → 70, source stage 15 → 16. **Break-it:** bare
numbers off (6); own marque as other (2); prose off (5); batch ignores
the classes (1); marque matched as a prefix, not a word — **survived**
until a test used Honda `MVX250F` (a real Honda that begins "MV"); then 1.

**Coverage, re-measured with the classes separated and every filter
above in place** (raw output `~/.cache/motodiag/coverage_20260923.txt`).
"excerpt" = candidates.py returns at least one; "gearbox" = at least one
excerpt carries a gearbox word. Both are upper bounds on what a model
could be SENT, not findings — several Honda hits are model-list pages.

| make | total | classed | names | excerpt | gearbox |
|---|---|---|---|---|---|
| Ducati | 76 | 29 | 47 | 0 | 0 |
| Triumph | 72 | 19 | 53 | 0 | 0 |
| KTM | 63 | 20 | 43 | 1 | 0 |
| BMW | 49 | 9 | 40 | 4 | 0 |
| Kawasaki | 39 | 0 | 39 | 0 | 0 |
| Yamaha | 39 | 0 | 39 | 4 | 0 |
| Aprilia | 37 | 13 | 24 | 0 | 0 |
| MV Agusta | 30 | 15 | 15 | 1 | 0 |
| Suzuki | 29 | 0 | 29 | 0 | 0 |
| Piaggio | 28 | 1 | 27 | 4 | 2 |
| Honda | 26 | 0 | 26 | 11 | 9 |
| Vespa | 22 | 1 | 21 | 2 | 1 |
| Harley-Davidson | 17 | 1 | 16 | 0 | 0 |
| Zero | 16 | 1 | 15 | 0 | 0 |
| Moto Guzzi | 15 | 5 | 10 | 0 | 0 |
| Energica | 11 | 1 | 10 | 0 | 0 |
| Kymco | 10 | 0 | 10 | 3 | 3 |
| LiveWire | 8 | 1 | 7 | 0 | 0 |
| Genuine | 5 | 0 | 5 | 0 | 0 |
| SYM | 5 | 0 | 5 | 3 | 2 |
| Damon | 3 | 0 | 3 | 0 | 0 |
| **total** | **600** | **116** | **484** | **33** | **17** |

**The library can at most answer 17 of 484 machine names (3.5%).** The
other ~467 — every Ducati, Triumph, Kawasaki, Suzuki, Aprilia — need a
document the library does not have. Acquisition is the bottleneck.

### 2026-09-23 — Bug fix #1: `bare_number` was a shape rule and dropped real machines

- **Issue:** `db920bb`'s `census.not_a_machine` classed any spelling
  matching `re.fullmatch(r"\d+\s*(cc)?")` as `bare_number` — never
  searched, never sent. Measured on HEAD (by the operator, then here):
  Ducati 916, 996, 998, 999, 1098, 1198, 1299, 848, 749, 959, 899; Vespa
  and Piaggio 946; MV Agusta 675, 910, 982, 1078 — all `bare_number`. Also
  Ducati 748, 851, 888 and MV Agusta 750, 998 (the same #1325 "model
  numbers" row as 910/982/1078).
- **Root cause:** an exclusion with no positive control. The workspace
  rule "An exclusion is a claim and needs a control" was not loaded in
  this repo (see the CLAUDE.md commit that follows), and the class was
  written from the shape of the first examples (`06`, `20`, `1000`) — a
  number is often exactly what a maker calls the machine.
- **Fix:** `NOT_A_MODEL_NUMBER`, a named list of 24 `(make, spelling)`
  entries, each with the junction rows (`known_issues.id`) that show it is
  a year fragment, a slash-list fragment of another name, or a
  displacement badge. A number not on the list is a machine name; strict
  E4 then demands "Ducati 916" before a document counts.
- **Files:** `.claude/skills/source-transmission/census.py`;
  `tests/test_phase257_source_checks.py` (22 positive controls in
  `test_a_machine_name_is_not_classed`); `tests/test_phase257_source_stage.py`
  (its not-a-machine case now uses a prose spelling — a ZZ "1000" is no
  longer classed, correctly).
- **Verified:** the 22 controls added first and **seen to fail on the old
  rule (22 failed)**; with the list, 246 pass across 257 + 255D. Break-it:
  shape rule restored → 22 fail; the `06` entry removed → 1 fails.
  Classes now: bare_number 24 (was 46), other_marque 39, prose 30,
  marque_name 1 — **94 classed, 506 machine names**.
- **The coverage figure is re-measured** (`~/.cache/motodiag/coverage_20260923_bugfix1.txt`)
  and **supersedes the "17 of 484" table above, which excluded these
  machines**: of **506** machine names, 33 get any excerpt and **17** an
  excerpt with a gearbox word — the same 17 spellings. The restored 22 add
  none: the library holds no Ducati, MV Agusta or Vespa 946 document.
  Figure of record: **17 of 506 (3.4%)**, an upper bound on what a model
  could be sent, not findings.
- **Commit:** this one.

### 2026-09-23 — D7 measured: one plain fetch per maker URL, no model

`d7_probe.py` replaces `~/.cache/motodiag/d7_subc.py` (an open-ended
agent loop). A fixed, hand-written list of 43 URLs over all 21 makes in
the census — the owner's-manual portal, a spec page for a census model,
and a known document endpoint where one exists — one GET each, Step 0's
browser UA, no cookies, no JavaScript, no retries, no following of
discovered links. Each response is classified by a rule in the file and
saved with its sha256, URL, final URL and fetch time. Run
`~/.cache/motodiag/d7/20260923_002937/` (`d7.json` raw; `d7_reclassified.json`
after the classifier fix below — same saved bodies, no second fetch).

**The first classification was wrong in three rows, by my rule, not by the
makers:** Kawasaki's 302s were "needs_browser" (they are the S0-2 redirect
loop — a cookie wall); Damon's Cloudflare 522 was "needs_browser" (the
origin is down). Fixed: `redirect_loop` for a 3xx urllib abandons, 5xx is
`unreachable`. `tests/test_phase257_d7_probe.py` (13), one hand-written
response per method shaped on a real one; break-it: 5xx branch, 3xx
branch and the spec-line branch each removed → 1 fails each.

**Measure what produced the number: most `not_found` rows are my guessed
URLs being wrong, not a maker without a page.** Suzuki redirected to its
own `/404?item=…`, Harley and MV Agusta to their own not-found pages,
Zero and Yamaha 404'd the paths I wrote. They say "this URL", nothing
about the maker. SYM's `sym-usa.com` now redirects to
`lancepowersports.com/404.html` — the US distributor changed.

| make | machine names | portal | spec page | doc endpoint | method, measured |
|---|---|---|---|---|---|
| Ducati | 61 | 403 | 403 | — | **blocked** |
| Triumph | 53 | 200, no PDF links, no spec line | 404 (my URL) | — | unresolved: readable HTML, right spec URL unknown |
| KTM | 43 | 200, no evidence | 200 → redirected to a listing | — | unresolved |
| BMW | 40 | 200, JS shell (22 chars of text) | timeout | — | **needs browser** (portal) |
| Kawasaki | 39 | 302 loop | 302 loop | — | **redirect loop** (cookie wall) |
| Yamaha | 39 | 403 | 404 (my URL) | — | **blocked** (portal) |
| Suzuki | 29 | home 200, no evidence | → own /404 (my URL) | — | unresolved |
| Piaggio | 28 | 403 | 403 | — | **blocked** |
| Honda | 26 | 403 | 403 | hondamotopub: 200, JS (797 chars) | **blocked** / needs browser |
| Aprilia | 24 | 403 | 403 | — | **blocked** |
| Vespa | 22 | 403 | 403 | — | **blocked** |
| MV Agusta | 21 | 200, no PDF links | → own /404 (my URL) | — | unresolved |
| Harley-Davidson | 16 | → not-found (my URL) | → not-found (my URL) | serviceinfo: 200, JS (77 chars) | needs browser (doc) |
| Zero | 15 | 404 (my URL) | 404 (my URL) | — | unresolved |
| Moto Guzzi | 10 | 403 | 403 | — | **blocked** |
| Energica | 10 | TLS: **certificate expired** (curl agrees) | same | — | **unreachable** |
| Kymco | 10 | 404 (my URL) | **200, "Transmission CVT Automatic"** | — | **spec page HTML** |
| LiveWire | 7 | 200, no evidence | 200, no evidence | — | unresolved |
| Genuine | 5 | 404 (my URL) | — | **200, PDF, 2,931,891 B** | **document endpoint** (byte-identical to the library's Buddy 125) |
| SYM | 5 | → lancepowersports 404 | same | — | distributor moved |
| Damon | 3 | 522 (origin down) | — | — | **unreachable** |

**By machine names (506):** a plain fetch works for **15** (Kymco 10,
Genuine 5); **blocked 210** (Ducati, Yamaha, Piaggio, Honda, Aprilia,
Vespa, Moto Guzzi — Aprilia, Piaggio, Vespa and Moto Guzzi share one
Piaggio-group wall); redirect loop 39 (Kawasaki); needs browser /
unreachable 69 (BMW, Harley, Energica, Damon); **unresolved 173** —
Triumph, KTM, Suzuki, MV Agusta, Zero, LiveWire, SYM — readable HTML or my
URL wrong, where a correct spec URL has not been tried.

## Acquire — design (not built)

**Goal:** put maker documents INTO `~/research/motodiag` with provenance
the script records, so candidates → one-turn source → entry_check →
refute can use them. No model anywhere in acquire.

1. **`acquire.py MAKE`**, no model. A committed table `ROUTES[make]` holds
   only methods measured to work: `document_endpoint` (explicit PDF URLs)
   and `spec_page_html` (explicit spec-page URLs, or a URL pattern plus
   ONE listing page whose links matching that pattern are taken — one hop,
   never a crawl). A make with no measured route has no entry: its
   outcome is its D7 method, reported, never guessed past. Per run: at most
   N fetches (proposed 30), 1 request/second, robots.txt honoured, TLS
   never bypassed (Energica stays unreachable).
2. **Where it writes:** `~/research/motodiag/acquired/<make>/<file>` plus
   `<file>.acquired.json` — `url`, `final_url`, `http_status`,
   `content_type`, `bytes`, `sha256`, `fetched_at`, `route`, `probe_run` —
   written by `acquire.py` only. Text for candidates is derived beside it
   (`<file>.txt`, via `entry_check._extract_text` / pypdf) and its sidecar
   records the source sha256. The sandbox already denies model writes
   outside the run's clone (`sandbox.sb.tmpl`), so no model stage can
   write into `acquired/` — the property E9 lacked (F141).
3. **Kind from the host, not the filename:** `library_index` gains
   `^acquired/`, whose kind comes from the sidecar: a maker kind only when
   the final URL's host is on a named `MAKER_HOSTS` list (kymcousa.com,
   genuinescooters.com, …) — so a redirect to a mirror or a distributor's
   404 is not a maker document.
4. **entry_check E11** for an acquired file: the sidecar exists, the file's
   sha256 matches it, the host is a maker host. No network in the check.
5. **Blocked / redirect loop / needs browser (318 of 506) are out of
   scope** until the operator decides. Options, none built: (a) an
   operator-supplied inbox — the operator downloads by hand into
   `~/research/motodiag/inbox/` with the URL written beside it and the
   script ingests it with provenance `operator-supplied`: a person, not a
   model; (b) a headless browser for the JS shells (BMW, hondamotopub,
   serviceinfo) — a new dependency, and **not** for the 403 walls, which
   are refusals, not rendering problems; (c) leave them `unknown`.
6. **The next measurement before building:** the 173 unresolved — one
   correct spec URL per maker, found by hand from its own listing page,
   probed the same way — so the route table is built from measured
   routes, not from the Kymco and Genuine cases alone.
7. **Tests (when built):** a local `http.server` fixture serving a PDF, a
   spec page, a 403, a 302 loop, a redirect to another host, a 522; a
   positive control (the Kymco Super 8 50X page is fetched, indexed as a
   maker spec page, and returned by `candidates("Super 8-50 X",
   make="Kymco")`); negatives (a redirect to a non-maker host is not
   indexed as maker; a tampered file fails E11); break-it per the house
   rule.

### 2026-09-23 — D7 round 2: the unresolved makers, Kawasaki with cookies, the JS shells; E11

Operator's decisions: measure before building; a cookie jar is ordinary
HTTP (Step 0 got Kawasaki's 200 that way — "redirect_loop" was the
probe's no-cookie policy, the same lesson as the wrong-URL rows); check
each JS shell's own source for a JSON endpoint before any browser; an
operator inbox for the 403 walls; cap 30 fetches/run, 1 req/s;
MAKER_HOSTS with referrers for makers that host manuals elsewhere.

`d7_probe.py` gains `--targets FILE` (a hand-written URL list), `--cookies`
(one session cookie jar), an optional per-row header dict (what the
maker's own page script sends), 1 request/second, and records headers and
cookies in each row. URLs came from links in the makers' own saved pages
(round 1's bodies), with one listing fetch where a page linked only to
categories (Triumph, Zero). Runs: `~/.cache/motodiag/d7/20260923_0042*`,
`_0043*`, `_0044*`, `_0045*`.

| make | URL, found on the maker's own site | result |
|---|---|---|
| KTM | ktm.com …/2024-ktm-1290-superadventurer.html | **spec page**: "Transmission 6-speed" |
| Suzuki | suzukicycles.com/sportbike/2027/gsx-r1000 | **spec page**: "…cassette-style, six-speed transmission" |
| MV Agusta | mvagusta.com/us/en/product/brutale/800 | **spec page**: "Transmission Cassette style; six speed" |
| Triumph | …/roadsters/street-triple/street-triple-765-rs-2023 (the family page has no spec) | **spec page**: "Gearbox 6-Speed" |
| Kawasaki (cookies) | …/ninja-zx-10r/2026-ninja-zx-10r (the family page has no spec) | **spec page**: "Transmission 6-speed, return shift" |
| Yamaha | yamahamotorsports.com/models/yzf-r1/specs | **spec page**: "Transmission 6-speed" — **not walled**; round 1's 403 was the manual library only, and its spec 404 was my URL |
| Zero | zeromotorcycles.com/model/zero-srs | spec in the page's **embedded JSON**: `"entry_label":"Transmission" … "Clutchless direct drive"` — plain fetch; the probe's text rule missed it |
| SYM | sym-global.com/jet14-e5 → its own PDF link | **document endpoint**: JET14_MANUAL.pdf, 1,173,227 B, on sym-global.com |
| LiveWire | livewire.com/bike-comparison/s2-alpinista | readable, **no drive/transmission statement** in text or source (1 page tried) |
| BMW | manuals.bmw-motorrad.com — its bundle builds `…/manuals/BA-Extern/IN/BA-INTERNET-COM/01/Nav.xml` | **static XML index**, 14,691 PDF references, "S 1000 RR" 46 times, PDFs under `…/BA-INTERNET-COM/PDF/<FILENAME>` — no browser needed |
| Honda | hondamotopub.com/AHM — its page script calls `/ajax/get_model_names/AHM/<cc>` | **JSON endpoint**: empty without, and a model list with, the `X-Requested-With` header the page's jQuery sends (+ session cookie). The PDF hop is not measured |
| H-D | serviceinfo.harley-davidson.com — its bundle | **login wall**: `service/oauth2/authorize`, `access_token`. Not pursued |

**No headless browser is needed** for any maker measured: BMW and Honda
motopub expose static/JSON endpoints in their own source; H-D is a login
wall, not a rendering problem. The probe's classifier needs two new
rules before acquire uses it — embedded-JSON specs (Zero) and JSON
responses (Honda) — recorded, not built.

**Machine names by measured route (506):** spec page or document by
plain HTTP — Triumph 53, KTM 43, BMW 40, Kawasaki 39, Yamaha 39, Suzuki
29, Honda 26 (motopub), MV Agusta 21, Zero 15, Kymco 10, Genuine 5, SYM 5
= **325**; **walled (403) 145** — Ducati 61, Piaggio 28, Aprilia 24,
Vespa 22, Moto Guzzi 10; login 16 (H-D); unreachable 13 (Energica
expired certificate, Damon 522); no statement found 7 (LiveWire). A
route is one page proving the method, not coverage of every model.

**Library recall limit, measured:** Piaggio's machine names find the
library's Vespa/Piaggio manuals no better under "Vespa" (4 as Piaggio, 3
as Vespa, none only as Vespa). The miss is the strict name rule: the LX
manual titles itself "Vespa LX 125 - 150", which is not "LX 150".
Recorded, not changed.

**E11, built and tested on the Wolf 150 case.** `library_index`: an
`acquired/` rule and `MAKER_HOSTS` (each make's own domains; a host
matches itself or a subdomain, never a suffix string). `entry_check.E11`
reads `<file>.acquired.json` (url, final_url, sha256, fetched_at,
referrer {url, path, sha256}): the file must still hash to its sha256;
it counts when `final_url` is a maker host, or — for Dropbox and the like
— when its referrer is a maker-host page, itself in the library,
unchanged, and linking to the file's URL. `candidates.py` applies E11
before the model reads. The real facts behind the fixture: SYM's
maintenance-guide page (`sym_mg.html`) links
`https://www.dropbox.com/s/cnzzt4veh3p7ra9/Wolf150 Owner Manual.pdf?dl=0`,
and that PDF is byte-identical (sha256 728b0055…) to
`v2/sympdf/Wolf150_Owner_Manual.pdf`; `sym_mg.html` itself carries no
canonical URL — its origin was never recorded, which is why acquire.py
must record it. Fixtures `fixtures/library/acquired/`: the traced copy
passes; no referrer, a forum referrer, an unlinked Dropbox URL, a stale
referrer hash, tampered bytes and a missing sidecar each fail with their
own message; SYM's page does not vouch for a Kymco finding; a Genuine
document on genuinescooters.com passes without a referrer. **Break-it,
each seen to fail:** any host passes (7); referrer host unchecked (3);
link unchecked (2); referrer hash unchecked (2); file hash unchecked (2);
E11 not called (9); host matched as a substring (3); candidates skips E11
(1 — a first version of that test was itself wrong: it failed at
baseline because SYM's own page, correctly, is read too; corrected, then
the mutation re-run). 275 pass across 257 + 255D; 244G clean.

### 2026-09-23 — census: engine families and other makes' machines, named (operator decision 1)

`census.NOT_A_MACHINE_NAMED`, make-scoped, one reason and its junction
rows each, never by shape. `engine_family` (7): Ducati Testastretta,
Desmoquattro, Superquadro, Desmodue, Desmoquattro 16-valve, Testastretta
MY2010, 998 Testastretta (the S4RS's engine, #819). `other_make_model`
(8): "S 1000 XR" under Ducati, Aprilia, Moto Guzzi **and Triumph and KTM**
— all five from the one row #912 ("BMW S 1000 R, S 1000 XR, S 1000 RR by
type code; Ducati generally") — and "Testastretta MY2010" under KTM, BMW
and MV Agusta (row #886, a Ducati engine). Triumph, KTM and the #886
entries go beyond the operator's named list on the same evidence;
flagged for review. Not classed, and scoped out by the decision: KTM
LC8 / LC8c / LC8 V-twin, BMW Boxer / ShiftCam / Oilhead / hexhead — also
engine families.

Positive controls: (BMW, "S 1000 XR"), Ducati Panigale V4, Multistrada
1200, Monster S4R stay machines. The 15 class tests were seen to fail
before the entries existed (15 failed). Break-it: the lookup unscoped
from the make → 4 fail, including the BMW control. Classed now 109 (was
94); **machine names 491** (was 506). 294 pass across 257 + 255D.

### 2026-09-23 — Kymco re-run under the one-turn source stage (token redesign step 5)

`subc usage` first: 53.2M of 60M used today, 6.8M left — headroom for
one spelling. `batch Kymco "K-Pipe"`, run `Kymco_20260923_083848`:

| stage | before (`Kymco_20260922_232607`, agent loop) | after |
|---|---|---|
| source (GLM, Subconscious) | 7,661,322 in + 18,077 out + 6,133,632 cache-read, 37 turns | **6,260 in + 2,967 out, 2 turns = 9,227** |
| refute (Opus, tools) | 16 in + 1,904 out + 149,963 cache-read + 13,188 cache-write = 165,071 | 20 in + 3,373 out + 194,668 cache-read + 28,796 cache-write = **226,857** |
| batch | — | **236,084 → STOP** (ceiling 150,000 × 1 sent) |

The source stage fell ~830× (input) and returned the same finding: the
page-57 spec line, `needs_page_image` set because the excerpt is OCR.
entry_check passed it; refute kept it, rendering page 57 itself. **The
batch stopped anyway, on refute's cost** — which the redesign left with
its tools, as specified. Refute alone is 1.5× the ceiling, and before
the redesign it was already 165K, so **no batch that reaches refute can
pass the 150K-per-spelling stop as written.** Nothing was written. The
ceiling is the operator's; not changed.

### 2026-09-23 — Bug fix #2: every STOP alert was silent

- **Issue:** the re-run's log shows `osascript` failing: `syntax error:
  Expected """ but found unknown token (-2741)`.
- **Root cause:** `alert()` quoted the title with `json.dumps`, which
  writes the STOP title's em dash as `—`; AppleScript has no `\u`
  escape. `check=False` swallowed the failure. Since `a8e236e`, every
  STOP alert failed and every success alert (no em dash) worked.
- **Fix:** `notification_script()` quotes with `ensure_ascii=False`.
- **Files:** `orchestrate.py`; `tests/test_phase257_orchestrator_guards.py`.
- **Verified:** reproduced with `osacompile` before the fix (exit 1). New
  test compiles the real STOP title and a quoted/backslash message with
  `osacompile` (nothing is displayed); the old escaping restored → 1
  fails; fixed → 32 pass.
- **Commit:** this one.
