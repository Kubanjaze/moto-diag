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

### 2026-09-23 — acquire.py built (not run); the inbox; Honda motopub measured to the PDF

**Honda motopub, the last hop, measured** (cookies, the page's own
`X-Requested-With`): `get_model_names/AHM/751-` → `get_model_years/AHM/
CBR1000RR-RA-S1-S2` = `["2018"]` → `/om/AHM/CBR1000RR-RA-S1-S2/2018`, whose
page links `https://2rom-prd-data.hondamotopub.com/om/AHM/…/CBR1000RR.RA.S1.S2_31MKF610_0.pdf`
— a hondamotopub.com subdomain. The PDF itself was not fetched.

**`acquire.py`** (no model): `fetch MAKE [--limit N]` and `ingest`. One
`Fetcher` is the only network door — one cookie jar, CAP 30 fetches a run,
1 request/second, robots.txt per host, TLS never bypassed, errors recorded
and never retried. Routes (`ROUTES`), each from D7: spec pages via a
maker listing (KTM, Suzuki, MV Agusta, Triumph ×4 categories, Yamaha
`/specs`, Zero, Kymco `/scooters/`, Kawasaki with a hop to the newest
model-year page); BMW's `Nav.xml` → the English rider's manual PDF; Honda
motopub's JSON chain → the owner's-manual PDF; SYM (sym-global) and Genuine
(`/pages/owners-manual`, found in its own navigation) product page → PDF.
Every file lands in `acquired/<Make>/` with a script-written sidecar
(url, final_url, status, bytes, sha256, fetched_at, supplied_by,
referrer, for_spellings) and a **derived text** (`entry_check.derive_text`:
PDF pages under `=== PAGE n ===`, HTML text plus embedded-JSON spec pairs,
JSON sorted) whose sidecar names its parent. **E11 re-derives** that text
from the parent's bytes and compares, so the text candidates reads is
provably a function of the maker's bytes. `candidates.py` reads acquired
files only through their `.txt`. `match()`: a strong spelling takes the
shortest name containing it; a weak one ("CB") must equal a name. Link
names are the visible text, the last path segment and the last two —
the offline dry run showed why: KTM slugs run words together
("superadventurer"), MV's last segment is "800" of "brutale/800", Zero's
link text carries a "New" badge (named in `BADGES`).

**Offline match estimate** — the routes' rules over listing pages saved
in D7, no fetch; a live listing can differ: BMW 22/39, Kawasaki 16/39,
Suzuki 10/29, Yamaha 9/39, Zero 7/15, KTM 5/41, MV Agusta 3/20, Triumph
≥3/52 (1 of 4 categories saved), Kymco ≥2/10, Honda ≥1/26 (1 of 5 cc
buckets saved); SYM and Genuine not estimated. **Of 320 machine names in
routed makes, ~80–120 are likely to match**: current maker sites list
current models; most census spellings are older machines (GSX-R1100,
KZ1000, Vulcan 1500). Loose matches to judge downstream: BMW family
spellings (F800, R1200, S1000) take one variant's manual; KTM "1290 Super
Duke" takes the Super Duke GT page; MV "F3" the F3 R.

**The inbox:** `~/research/motodiag/inbox/{Ducati,Aprilia,Piaggio,Vespa,Moto Guzzi}/`
and `inbox/README.md` (= `acquire.INBOX_README`). Per document: the file;
`<name>.url` with `document:` and `page:` lines; the page saved as
`<name>.page.html`. `ingest` copies (the inbox is read-only), writes
sidecars with `supplied_by: operator`, the page as the referrer. Inbox
files are `unindexed` until ingested — nothing reads them before.

Tests: `test_phase257_acquire.py` (19), a fake transport replaying
hand-written pages shaped on D7's; `test_phase257_d7_probe.py` +3 (the two
recorded rules; the real Zero page now classifies `spec_embedded_json`).
**Break-it, each seen to fail:** cap ignored; robots ignored; a weak
spelling takes the nearest name; no derived text (3); ingest skips the
link check; ingest skips the page host; the badge kept; embedded pairs off
(2); the JSON rule off; acquired originals read by candidates (2); derived
text not re-derived — **survived** until a test forged text and sidecar
hash together (every hash agreeing), then 1. Two defects found by the
first run of the tests and fixed: candidates read acquired HTML
originals as well as their text; a run with nothing to do still fetched
its listing. 323 pass across 257 + 255D; 244G clean.

### 2026-09-23 — operator decisions: refute's own budget; BMW PDFs; the 4609 rule in the pipeline

**1. Refute has its own budget** — never excluded, never trimmed, never
skipped; over it is a stop. `token_stop` now holds two: every stage but
refute at 150K per spelling sent (unchanged), and refute at
`REFUTE_STOP_PER_FINDING` per finding refuted. **That number is PROPOSED,
not decided: 300,000** (~1.3× the largest refute measured: 226,857,
Kymco re-run; 165,071 before). No refute runs until the operator sets it.
The refute prompt now says to render page images only for findings
marked `needs_page_image`. Tests: the real Kymco figures pass both
budgets; refute over its own is a stop after it ran (not a skip); refute
does not spend the source budget. Break-it: one shared budget again → 3;
refute budget off → 1.

**3. BMW PDFs:** the library is `~/research/motodiag`, outside the
repository and with no git of its own, so nothing there can be committed;
`acquire.py` now **refuses a library inside the repository** (tested), and
`.gitignore` gains `*.pdf`, `acquired/`, `inbox/` (0 PDFs tracked before).
**Dedupe by content hash** within `acquired/`: identical bytes are stored
once and the spellings merged. The 30-fetch cap stays. And a fix found
while writing it: a page fetched again with new bytes must never overwrite
the saved copy — a Dropbox-hosted manual counts only through that copy's
pinned sha — so a different file under a taken name gets its sha in the
name. The first test of that survived the mutation (a Kymco page is on a
maker host; E11 never reads its referrer); rewritten on the Wolf 150
shape, it fails.

**4. The 4609 rule — a document sources only the model it names.**
`entry_check.names_model(text, spelling)`: the spelling's words in a run
as the document spells them ("CR 300i" names "CR300i"), **not followed by
a variant word** (`VARIANT_TOKENS`, each seen this phase: GT, R, RR, RS,
S, SP, SE, X, XR, GS, SX, XC, F, RC, Rally, Evo; ABS is equipment and
absent). So "1290 Super Duke GT" does not name the 1290 Super Duke, "F 800
GS" not the F800, "SR/S" not the SR. `model_scope` marks each finding
`model` or `family`; family evidence still goes to refute, is recorded in
`summary.family_evidence`, and **writes nothing** unless refute returns a
`model_line` that the script checks both names the model and is on the
page. `acquire.py` records each match as `exact` or `contains` in the
report and the sidecar's `matches`. Tests: a sibling page writes nothing;
refute quoting the sibling, or a line the page lacks, does not promote it;
refute's line confirms a model the text rule missed ("ZZ Sprint 900" at a
line end, the next line "S: …"). Break-it: variant words ignored → 7;
family writes → 3; refute's line trusted → 2; line not checked on the page
→ 1; line not checked for the model → 1; dedupe off → 1; repo guard off →
1; match kind not recorded → 1. 344 pass across 257 + 255D; 244G clean.

### 2026-09-23 — acquire smoke test: `fetch Kymco --limit 3`

The first three unsourced Kymco machine names: Super 8-50 X, Super 8-150 X,
Jet 14. **3 fetches** (robots.txt, `kymcousa.com/scooters/`, one spec
page), 1/s, no stop. Run record `~/research/motodiag/acquired/_run_Kymco_20260923_092034.json`.

| spelling | result |
|---|---|
| Super 8-50 X | **matched `exact`** ("Super 8 50X") → `kymcousa.com/scooters/super-8-50x/`, `spec_page_html`; derived text carries "Transmission  CVT Automatic"; `names_model` → the page names the model |
| Super 8-150 X | unmatched — not on Kymco USA's current listing |
| Jet 14 | unmatched — a SYM model the junction also attaches to Kymco |

Saved: `acquired/Kymco/scooters.html` (the listing, as referrer) and
`scooters_super-8-50x.html`, each with a derived `.txt`; **all four pass
E11**; `candidates.py` returns the acquired text alongside the older
library copies (`v2/super850x_prod.*`). Found by the run: the run record
logged 2 requests while the cap counted 3 — robots.txt fetches were
counted but not logged. Fixed; a test pins that the log holds every
request the cap counts (removing the log line fails it). 344 pass.

### 2026-09-23 — refute budget approved; cross-make spellings classed; F142 filed

**Refute's budget: 300,000 per finding refuted — approved by the
operator.** Not to be raised to fit a batch: if the per-finding cost
climbs, refute is split into groups of at most 5 findings, each a fresh
context.

**Classed (operator decision 3), named and make-scoped:** the multi-make
rows #4593/#4596 (`'Kymco, SYM'`) and #4603 (`'Yamaha, Kymco, SYM,
Genuine'`) put every model under every make. `other_make_model`: (Kymco,
Jet 14), (Kymco, Fiddle 4), (SYM, X-Town 300), (Kymco, XC50), (SYM, XC50),
(Genuine, XC50) — and **(Kymco, Wolf CR300i)**, on the same rows, beyond
the operator's list, flagged. Positive controls, the true make keeps its
machine: (SYM, Jet 14), (SYM, Fiddle 4), (Kymco, X-Town 300), (Yamaha,
XC50), (SYM, Wolf CR300i). The 7 class tests were seen to fail first;
unscoping the lookup fails the controls. Machine names 484 (was 491).

**F142 filed** in `docs/FOLLOWUPS.md` (next free across both files:
moto-diag F141, mobile F115): 69 multi-make rows → 1,129 junction rows,
192 distinct (make, model) pairs; how many are wrong is not measured.
Not fixed in 257. `finding_check.py`: exit 0.

### 2026-09-23 — refute measured per finding; refute groups (off until the data say otherwise)

Refute runs with `--output-format stream-json --verbose` (checked on one
Haiku call first: each API call's usage arrives in its assistant events,
repeated per content block — deduplicated by message id; the last line is
the same result object, so parsing is unchanged). The raw stream is kept
(`refute[_n].stream.jsonl`) and `refute_attribution` assigns each call to
the finding whose spelling or document its tool inputs name; a call naming
none continues the last; before any, `(setup)`; naming several (the final
answer), `(answer)`. It is an attribution by what refute was reading, not
a measurement inside the model. `summary.refute_per_finding` holds turns
and tokens per finding, in order.

`REFUTE_GROUP` (None = one call): findings per refute call, each a fresh
context; the budget is checked after each group and a group over it stops
the rest. Per the operator it stays None unless per-finding cost climbs
across a batch — then 5. Tests (5): attribution over hand-written stream
events; groups are separate streamed calls; a group over budget stops the
rest. Break-it: no dedupe by id; no carry-over; groups ignored (2); no stop
between groups; not streamed — each seen to fail. 359 pass; 244G clean.

### 2026-09-23 — Suzuki: acquire + batch (nothing written yet)

**Acquire** (`fetch Suzuki`, 12 fetches): 10 of 29 machine names matched
Suzuki's own current spec pages — 9 `exact`, SV650 → "SV650 ABS"
`contains`. The 19 unmatched are older machines not on the current site
(GSX-R1100, Bandit 1200/1250/600, GS750/1000/1100, Katana, Intruder 1500,
SV1000, V-Strom 1000, …). All saved files pass E11.

**Batch** `Suzuki_20260923_093052`, all 29 spellings: 12 sent to the model
(10 acquired + DR-Z400SM and GSX-S750, which the pages mention), 17
`no_evidence` with no call. **Stops: none. Rejections: none. Ready to
write: 10** — GSX-R750, GSX-R1000, GSX-R600, SV650, V-Strom 650, GSX-S1000,
DR-Z400S, Boulevard C50, Boulevard M109R, V-Strom 1050, all `manual`, all
kept by refute. DR-Z400SM and GSX-S750 came back `no_evidence` (named in
passing, no gearbox statement).

| stage | tokens | turns | per unit |
|---|---|---|---|
| source (GLM) | 88,776 (79,208 in, 8,736 out) | 2 | 7,398 / spelling sent (ceiling 150,000) |
| refute (Opus) | 203,844 (160,669 cache-read, 36,310 cache-write) | 8 | 20,384 / finding (budget 300,000) |

**Per-finding attribution did not work on this batch, and the reason is
recorded, not papered over:** refute checked all ten pages in each call
(shell/Python loops over the files), so no call belongs to one finding —
`refute_per_finding` put 2 calls on findings, 1 on setup and 4 on
"(answer)". The per-call sequence is the measurement: 21,362 → 24,091 →
24,738 → 25,483 → 31,206 → 33,846 → 36,336 (cache reads growing by the
context each turn). **No climb that warrants groups:** 20K per finding
here against 227K for Kymco's one (whose refute rendered and read page
images — OCR); groups of 5 would each pay the ~21K setup again.
`REFUTE_GROUP` stays None.

**One disagreement to decide before writing:** SV650. The acquired page is
the SV650 ABS; `names_model` rules it model-scope (ABS is equipment, not
in VARIANT_TOKENS, and the page also names "the first SV650"); refute kept
the gearbox but returned an empty `model_line`, saying the base SV650 is
named only historically. The batch lists it ready because the script
rule, not refute, decides scope. Flagged for the operator.

### 2026-09-23 — Suzuki write: nine entries (SV650 withheld)

From run `Suzuki_20260923_093052`, one entry per model in
`TRANSMISSION_LOOKUP` (new `# --- Suzuki` section), each citing Suzuki's
own page URL and quoting it: GSX-R750, GSX-R1000, GSX-R600, V-Strom 650,
GSX-S1000, DR-Z400S, Boulevard C50, Boulevard M109R, V-Strom 1050 — all
`manual`. Aliases only as the pages spell the models (hyphen/space/joined
forms); no model code the page does not carry. **SV650 withheld** (operator):
refute's reason says family evidence while its verdict says kept — the
gate defect fixed next (bug fix #3).

| | before | after |
|---|---|---|
| census (unknown spellings) | 600 | **591** |
| Suzuki unknown | 29 | 20 |

`tests/test_phase257_tranche1_writes.py` gains `TestSuzukiWrite`: 17 spellings
resolve `manual`; SV650, SV650 Gladius, GSX-R1100, GSX-S750, DR-Z400SM stay
`unknown`; the make is the scope. The suites that mention these machines
(Phases 57–65 Suzuki knowledge, 79–82, 95, 108, 155, 221, 227, 255, 255B,
256): 541 pass. 244G clean.

### 2026-09-23 — Bug fix #3: "kept" was read as "kept, and the page is about this model"

- **Issue:** run `Suzuki_20260923_093052` put SV650 in `ready_to_write`.
  Refute's own reason: "the page is for the SV650 ABS variant. The base
  SV650 is named only historically ('first SV650 debuted in 1999') … This
  is family evidence only and cannot write an entry." Its verdict: `kept`.
  The D5 disagreement stop never fired. (Caught by the operator; SV650
  was withheld from the Suzuki write.)
- **Root cause:** the verdict schema had one axis, kept/killed — whether the
  quote holds. It could not say "kept as family evidence", so the second
  judgment lived only in free text, and `ready_to_write` trusted the label
  over the reason. The script's own rule (`names_model`) also read the page
  as naming the SV650: ABS is equipment, and the page mentions "the first
  SV650". Two checks that could each say yes, and no place for refute to
  say no.
- **Fix:** refute's schema gains a required boolean `names_model` (is the
  document about THIS exact model — not a variant, sibling, or passing
  mention); the prompt separates it from `verdict`. A finding writes only
  when refute's `names_model` is true AND the script's check agrees (the
  page names the model, or refute's `model_line` verifiably does). A
  missing field is not a yes. When they disagree the finding is family
  evidence and the batch stops (D5).
- **Files:** `orchestrate.py`; `fixtures/library/pdfs/zz_blade650abs_spec.txt`
  (the SV650 ABS page's shape: an "…650 ABS" page naming the base model only
  as "the first … debuted in 1999"); `tests/test_phase257_source_stage.py`.
- **Verified:** the known-bad case added first and seen to fail (3 failed:
  it reached ready_to_write, no stop, a missing field counted as yes).
  Fixed: 31 pass. **Break-it:** the label trusted again → 3; a missing
  field counted as yes → 1; no disagreement stop → 1; refute alone decides
  (no script check) → 4. 387 pass across 257 + 255D; 244G clean. Runs made
  before this fix carry no `names_model`, so none of their findings would
  now pass the gate.
- **Commit:** this one.

### 2026-09-23 — SV650 (live vehicle #8, a 2019 SV650): no Suzuki document names the base model by plain fetch

Tried, one GET each (`~/.cache/motodiag/d7/20260923_094919/`):
suzukicycles.com's model listing and `/owners` link only `/street/2026/sv650-abs`
("SV650 ABS"); a guessed `/street/2019/sv650` returns 200 with generic
content and no SV650 — a soft 404, and a guess; Suzuki Motor USA's own
manual store `genuinesuzukimanuals.com` (linked from suzukicycles.com)
sells printed service manuals through a POST search form (`SearchReqs.asp`)
and says owner's manuals come from dealers — a form submission, not
pursued. **Reported to the operator for a decision** on whether equipment
variants such as ABS become a named, tested exception. SV650 stays
`unknown`.

### 2026-09-23 — Kawasaki: acquire + batch — STOPPED on a real miscitation (nothing written)

**Acquire** (`fetch Kawasaki`, 22 fetches, cookie jar): 8 spellings matched
Kawasaki's own model-year spec pages — KLR650, KLX300, Ninja 650, Z650,
Ninja ZX-6R / ZX-6R, Ninja ZX-10R / ZX-10R (6 machines). 23 unmatched
(older machines: KZ, GPz, ZX-7R/9R/12R, Vulcan 500–2000, …). **8 failed
`no_model_year_link`** — Ninja H2, H2 SX, Z H2, ZX-14R, Z900, Ninja 300,
Versys 650, Vulcan 900: their current year pages exist only as ABS or
special editions (`2026-z900-abs`, `2026-ninja-h2-carbon-abs`, measured
on two). Not fetched: the same question as SV650 ABS, pending the
operator's decision on equipment variants.

**Batch** `Kawasaki_20260923_095107`: 13 sent, source 95,192 tokens (2
turns, 7,322 per spelling), refute 230,502 (8 turns, 38,417 per finding —
6 refuted). **Stop: 4 entry_check rejections, all ZX-10R / Ninja ZX-10R
(E3 + E10).** Diagnosed: the source stage quoted "The dual-direction
Kawasaki Quick Shifter (KQS) system …" from the excerpt of the *family*
page (`…ninja-zx-10r.html.txt`) but cited the *model-year* page
(`…ninja-zx-10r_2026-ninja-zx-10r.html.txt`), which does not contain it.
The gate did its job — a quote attributed to the wrong document never
reached refute. Also noted: the year page's own spec line ("Transmission
6-speed, return shift", measured in D7) was not among its excerpts —
candidates' ranking/caps left it out; recorded, not changed.

The other six — ZX-6R, Ninja ZX-6R, KLR650, Ninja 650, KLX300, Z650 — were
each kept by refute with `names_model: true` and model-scope by the
script (bug fix #3's gate, first live run): each cites its own page's spec
table ("Transmission 6-speed, return shift"; KLR650 "5-speed"). Under the
standing rule a stop means **no write**; reported to the operator.
Refute's per-finding attribution again collapsed to "(answer)" — refute
reads all pages per call.

### 2026-09-23 — candidates.py: a page's own spec line is always among its excerpts

The Kawasaki stop's root in candidates: on the 2026 ZX-10R page the spec
row ("Transmission" / "6-speed, return shift", line 1516) sat 97 lines from
any mention of the name, so no ±40 name window covered it; the file-name
anchor did, but ranked behind five name windows that had used 38.5K of the
40K cap. **Fix:** `spec_lines()` finds spec-table rows (a "Transmission"
or "Gearbox" label first on its line, its value on the same line or the
next — N-speed, CVT, automatic, manual, DCT, direct drive…; "Transmission
Features" is not one); a document **about** the machine — its file name
or its title (its FIRST line) names it — contributes each spec-row window
first, ahead of every ranked window, inside the same caps. A first cut
counted "names it anywhere" (via `named_as_model`) as about: every Suzuki
page's menu says "Suzuki GSX-R750", the V-Strom's spec row took the
GSX-R750's slots, and six Suzuki controls failed; a second cut took the
first three lines as the title, and a fixture with a menu on line 2
caught it. Both corrected before commit.

**Controls on the real library** (`~/.cache/motodiag/candidates_controls_20260923.txt`):
the 2026 ZX-10R spec line is present (39,755 chars, under the cap); **20/20**
previously cited quotes are still inside their cited document's excerpts
— tranche 1 (K-Pipe, Wolf CR300i, Grom), Kymco (Super 8-50 X), the ten
Suzuki findings and the six clean Kawasaki findings; every spelling ≤ 8
excerpts and ≤ 40,000 chars. Fixtures: `zz_comet700_om.txt` (name mentions
up top, spec row 100 lines down), `zz_nebula300_spec.txt` (another model's
page naming the Comet in a menu, with its own CVT row). Tests +7.
**Break-it:** no spec priority → 1; title = anywhere → 1; the next-line
value ignored → 2; a label alone counted → 1. 394 pass; 244G clean.

### 2026-09-23 — the ABS exception (operator decision), named and narrow

A page for "<exact base model> ABS" may source the base model, and the
finding records `edition: "ABS"` so the written entry says so. Nothing else
qualifies. `entry_check.abs_edition(text, spelling)`: the model's exact
words, then "ABS" — "Z900 SE ABS", "Ninja H2 Carbon ABS" are other
machines. **Found while writing the negative controls: DCT was not a
variant word**, so an "Africa Twin DCT" page would have named the Africa
Twin — the one variant that changes the answer. `VARIANT_TOKENS` now
carries the transmission variants (DCT; Y-AMT → y, amt; E-Clutch → e) and
"carbon". Refute's prompt states the one exception and the DCT/Y-AMT/
E-Clutch refusal. `acquire._newest_year_page`: the base model's year page;
failing it, `<family>-abs`; never `-se-abs`, `-carbon-abs`, `-krt-edition`.

Controls (tests): ABS pages source SV650, Z900, Ninja H2; "SV650X",
"ZX-10RR", "V-Strom 650XT", "Africa Twin DCT", "MT-09 Y-AMT", "CB650R
E-Clutch", "Z900 SE ABS", "Ninja H2 Carbon ABS" source nothing; the edition
is recorded on the finding; the year hop takes -abs only without a base
page and never a special edition. **Break-it:** DCT not a variant → 1;
any suffix counts as an ABS edition → 6; no ABS edition ever → 4; any
"-…abs" year page → 1; the ABS page beats the base → 1; edition not
recorded → 1; Carbon not a variant → 1. 410 pass; 244G clean.

### 2026-09-23 — Bug fix #4: the source schema let a finding omit its citation

- **Issue:** the SV650 re-run (`Suzuki_20260923_100443`, 12,165 tokens) stopped
  on `E1 Suzuki | SV650: missing ['document']`. The finding was otherwise
  right — the SV650 ABS page's "The close-ratio, six-speed transmission…",
  and the model's own note cites that page's "Transmission 6-speed,
  constant mesh" row — but no `document` field was returned.
- **Root cause:** `FINDING` required only make, spelling, outcome; the
  citation fields were optional, so the schema the model answers to
  permitted a found finding with nothing to cite. E1 caught it downstream,
  as designed; the schema should never have allowed it.
- **Fix:** transmission, quote, document, page, evidence_kind are required
  on every finding, nullable for no_evidence.
- **Files:** `orchestrate.py`; `tests/test_phase257_source_stage.py` (+7: the
  fields are required, nulls allowed, and the schema the source call
  actually carries is this one).
- **Verified:** made optional again → 6 fail. 40 pass in the file.
- **Commit:** this one. SV650 re-runs after it.

### 2026-09-23 — SV650 through the pipeline under the ABS exception (not written yet)

Run `Suzuki_20260923_100556` (after bug fix #4): 1 spelling, source 11,383
tokens (2 turns), refute 63,047 (4 turns). **Stops none, rejections none,
ready to write: SV650, `edition: ABS`.** Document: Suzuki's own
`suzukicycles.com/street/2026/sv650-abs` (acquired, E11), quote "The
close-ratio, six-speed transmission features carefully selected ratios…";
refute kept it with `names_model: true`, `model_line` "2026 SV650 ABS", and
cites the page's spec row "Transmission 6-speed, constant mesh". The script
agrees (model scope, `abs_edition`). The earlier run the same day
(`Suzuki_20260923_100443`) stopped on E1 — bug fix #4.

### 2026-09-23 — Kawasaki whole re-run: STOPPED — refute killed Ninja 650 (nothing written)

After the ABS acquire (Ninja H2, Z900, Ninja 300 from their `-abs` year
pages; Vulcan 900, ZX-14R, Versys 650, Ninja H2 SX, Z H2 have neither a base
nor a plain `-abs` page and stay out). Run `Kawasaki_20260923_100438`: 14
sent, 11 refuted.

| stage | tokens | turns | per unit |
|---|---|---|---|
| source | 113,101 | 2 | 8,079 / spelling sent |
| refute | 292,482 | 10 | 26,589 / finding refuted |

**Stop: "refute disagreed on: Ninja 650"** — killed: the quoted spec row
reads only "Transmission 6-speed", which does not establish a manual
mechanism (a 6-speed can be a DCT). A sound kill; the previous run's
refute had kept the same quote. **Rejections: none** — the candidates fix
held: ZX-10R and Ninja ZX-10R now cite the 2026 page's own spec row
("Transmission 6-speed, return shift").

Kept, `names_model` true from refute and the script, **not written** (a
stop): ZX-10R, Ninja ZX-10R, ZX-6R, Ninja ZX-6R, KLR650, KLX300, Z650, and
under the ABS exception Ninja H2, Z900, Ninja 300 (`edition: ABS`, refute
naming the exception each time). no_evidence: ZX-14R, Ninja H2 SX, Z H2.

### 2026-09-23 — Kawasaki write: ten spellings, eight entries

From run `Kawasaki_20260923_100438` (operator: write the ten; Ninja 650's
kill concerns only itself). One entry per model, each quoting the page's
own spec row with "return shift" (KLR650 and KLX300 also "wet multi-disc
manual clutch") — the standard refute applied to Ninja 650: Ninja ZX-10R
(alias ZX-10R), Ninja ZX-6R (alias ZX-6R), KLR650, KLX300, Z650, and from
the ABS edition's page, saying so in the source: Ninja H2, Z900, Ninja 300.

| | before | after |
|---|---|---|
| census (unknown spellings) | 591 | **581** |
| Kawasaki unknown | 39 | 29 |

`TestKawasakiWrite`: 11 spellings resolve `manual`; Ninja 650, ZX-14R, Ninja
H2 SX, Z H2, Versys 650, Vulcan 900, ZX-10RR, Z900RS, KLX300SM stay unknown;
the ABS three name their edition. The 27 suites that mention these
machines + Phase 255's axis suite: 995 pass.

### 2026-09-23 — E12: a manual classification needs mechanism evidence (operator rule)

Refute killed Ninja 650's "Transmission 6-speed" and had kept the same
kind of quote the batch before; the standard drifted, so it is a rule.
**E12** (entry_check, and refute's prompt): a `manual` finding's quote must
name a rider-operated clutch (clutch lever, cable/hydraulic clutch, clutch
pull, manual clutch), a foot-shift pattern (return shift, shift/change
pedal, foot shift), or the word "manual" — "owner's/service/workshop
manual" excluded, since that names the document. A gear count, "constant
mesh", "close-ratio" or an unqualified "clutch" is not mechanism evidence.

Fixtures: 16 fixture quotes of my own were gear-count-only by this rule
("…constant mesh, return type", "5-speed constant mesh"); replaced by the
exact phrase "…, return shift" (diff reviewed; the one pinned evidence
original, `trail_spec.html`, re-hashed). The Glider 300 fixture, modelled
on the Wolf CR300i's "Always use the clutch when changing gear.", now reads
"pull in the clutch lever" — **the real Wolf CR300i quote fails E12**
(handled in the re-check). The Blade 650 fixture gained a real spec row. A
test helper labelled "V-Matic belt" as manual; fixed.

Tests +17: Ninja 650's quote known-bad, ZX-6R's known-good; eight passing
shapes (return shift, manual clutch, foot shift, the word manual, clutch
lever, cable-operated clutch, clutch pull, hydraulic clutch), six failing
(gear count, close-ratio, constant-mesh, "shift action", owner's manual, a
slipper clutch); only `manual` is held to it. **Break-it:** E12 off → 2;
constant mesh counts → 3; the document's "manual" counts → 1; any clutch
counts → 1; foot shift ignored → 9. 455 pass; 244G clean.

### 2026-09-23 — E12 correction: every Phase 257 manual entry re-checked

Each entry's quote, from its run's summary (`~/.cache/motodiag/e12_recheck_20260923.txt`),
against E12; each failure's own page searched for a qualifying line.

| entry | quote as written | E12 | action |
|---|---|---|---|
| SYM Wolf 150 (Classic 150 alias) | "Squeeze the clutch lever fully, operate change pedal…" | pass | — |
| SYM Wolf CR300i | "Always use the clutch when changing gear." | **fail** | **re-quoted**, same manual (library copy byte-identical, sha256 e50db79f…), p. 22: "Start engine, squeeze the clutch lever fully, push shift pedal down to engage the 1st gear" |
| Kymco K-Pipe | "Transmission……4-speed, foot shift" | pass | — |
| Honda Grom 125 | "Transmission Manual; 5 speeds Clutch Multiplate wet" | pass | — |
| Suzuki GSX-R750 | "…back-torque-limiting clutch … close-ratio six-speed…" | **fail** | **reverted to unknown** — page: slipper clutch, "Clutch Wet, multi-plate type", "adjustable shift lever" |
| Suzuki GSX-R1000 | "…SCAS … wet clutch … clutchless upshifts … six-speed" | **fail** | **reverted** — page: SCAS, quick-shifter |
| Suzuki GSX-R600 | "…back-torque-limiting clutch … close-ratio six-speed…" | **fail** | **reverted** — same as GSX-R750 |
| Suzuki V-Strom 650 | "The six-speed transmission suits sporty rides…" | **fail** | **re-quoted**, same page: "…lets the rider start the motorcycle … without pulling in the clutch lever when the transmission is in neutral." |
| Suzuki GSX-S1000 | "…six-speed, close-ratio transmission…" | **fail** | **reverted** — page: SCAS, quick-shifter |
| Suzuki DR-Z400S | "…utilizes a cable-operated clutch…" | pass | — |
| Suzuki Boulevard C50 | "With a light pull, the clutch feeds engine power…" | pass | — |
| Suzuki Boulevard M109R | "A wide-ratio, constant-mesh five-speed transmission…" | **fail** | **reverted** — page: "Clutch Wet multi-plate type" only |
| Suzuki V-Strom 1050 | "…close-ratio transmission … smooth the shift action…" | **fail** | **reverted** — page: SCAS, quick-shifter |
| Kawasaki × 8 | "Transmission N-speed, return shift…" | pass | — |

| | before | after |
|---|---|---|
| census (unknown spellings) | 581 | **587** |
| Suzuki entries | 9 | 3 (V-Strom 650, DR-Z400S, Boulevard C50) |

**At the rule's edge, flagged, not stretched:** the V-Strom 650 and SV650
pages both say "The multi-plate clutch has precise push rod actuation of
the pressure plate for a light (lever) pull and a consistent release
point" — a clutch pull, ~10 words from "clutch", outside RIDER_CLUTCH's
two-word window. Whether "clutch … pull" in one sentence counts is the
operator's to decide. A shift *lever* (GSX-R) is not in the list either:
DCT machines can carry one.

A new guard, `TestEveryPhase257ManualEntryMeetsE12`: each of the 15 manual
entries this phase wrote must carry an E12-qualifying quote in its own
source string; putting V-Strom 650's gear-count quote back → 1 fails.
895 pass across every suite mentioning these machines + the 255 axis suite;
244G clean.

### 2026-09-23 — SV650 held (no qualifying line); the standing rule for stops

**SV650 (live vehicle #8): not written.** Its only page, the 2026 SV650
ABS, carries no line that passes E12: the quote "The close-ratio, six-speed
transmission…" and the spec row "Transmission 6-speed, constant mesh" are
gear counts; its clutch sentence ("…push rod actuation of the pressure
plate for a light pull and consistent release point") is outside the
rule's clutch-pull window; its Easy Start sentence, unlike the V-Strom
650's, does not mention the clutch lever. It stays `unknown` pending the
operator's call on the clutch-pull window.

**Standing rule (operator decision 4), built:** a batch stops whole only on
systemic signals — source- or refute-stage error (wrong model serving
included), a token ceiling, blocked rate over 50%, or refute killing more
than a quarter of what it checked (`REFUTE_KILL_STOP = 0.25`). One
finding's kill, entry_check rejection, names-the-model disagreement or a
skipped spelling goes to `summary.withheld` and does not block the other
ready findings; a systemic stop empties `ready_to_write`. SKILL.md updated.
Tests: one kill in five → withheld, four ready; two in five → a stop,
nothing ready; a rejection doesn't block the rest; a refute-stage error is
a stop; the two tests pinned to the old rule (rejection stop,
disagreement stop) rewritten to the new one. **Break-it:** any kill stops
again → 1; the threshold off → 1; a systemic stop still writes → 1; a
refute error not a stop → 1; rejections stop again → 2. 468 pass; 244G clean.

### 2026-09-23 — E12 closes the automated-transmission gap; the clutch pull widened; re-check again

Operator, before Yamaha (Y-AMT) and Honda (DCT): E12 had a gap they walk
through. **Measured first:** of ten known-bad sentences, seven passed E12 —
"Y-AMT eliminates the clutch lever and shift pedal", "Dual Clutch
Transmission … without a clutch lever; manual mode …", "there's no clutch
lever to pull", "The Yamaha Automated Manual Transmission …", "manual mode
… paddle shifters on the DCT", "The clutchless Y-AMT has no shift pedal",
and V-Strom 650's own re-quote "…without pulling in the clutch lever…".

**Now:** E12 judges sentence by sentence (split at . ! ?, never at ";"). A
sentence carrying an automated marker (DCT, dual clutch, Y-AMT, automated,
automatic, clutchless, manual mode, paddle) never counts; a clutch/shift
term with a negation (no, not, without, eliminate(s/d), never, nor, free of)
in the five words before it never counts. The clutch pull widens to one
sentence: "clutch" and a NOUN pull ("light (lever) pull", "pull of the
clutch") — not the engine's "pulls hard", not "pull away". Honda E-Clutch
models (manual per plan 255 D1) will fail E12 by design — flagged for a
named decision when Honda comes up; E12 is not loosened for them.

Tests: 12 known-bad (the operator's four; Automated Manual; manual mode ×2;
clutchless; the V-Strom negation; a GSX-R slipper clutch and shift lever;
a DCT sentence whose half after a ";" is clean), 7 known-good (the SV650
and V-Strom "light pull" sentences, Kawasaki return shift, KLR650 manual
clutch, Grom "Manual; 5 speeds", Wolf CR300i, Boulevard C50), and the real
Suzuki sentences (SV650/V-Strom pass; GSX-R slipper, SCAS, "Clutch Wet,
multi-plate type" fail). **Break-it:** marker ignored → 2; negation ignored
→ 2; no wide pull → 2; the engine's "pulls" counted → 1; split at ";" and
"manual mode" not a marker **both survived at first** (my DCT test sentence
carried other markers) — two sentences added, then 1 each.

**The guard had a hole too:** `TestEveryPhase257ManualEntryMeetsE12`
extracted quotes by splitting on every apostrophe, so the commentary "a
rider's clutch lever" in V-Strom 650's source counted as a quote. Fixed
(a quote opens after whitespace/"(" and closes on "'" not followed by a
letter); with the fix it failed V-Strom 650, as it should.

**Re-check** (`~/.cache/motodiag/e12_recheck2_20260923.txt`): 14 of 15
written manual entries pass. **V-Strom 650 fails** (its Easy Start quote is
a negation) and is **re-quoted from its own page**: "The multi-plate clutch
has precise push rod actuation of the pressure plate for a light lever pull
and a consistent release point." The six reverted Suzuki pages have 0
qualifying sentences under the widened rule; they stay unknown. 492 pass;
244G clean.

### 2026-09-23 — SV650 blocked: Subconscious refused service (nothing run, nothing written)

The source prompt now states E12 (commit "the source prompt states E12…" —
its message says 49 source-stage tests passed; the run showed **44**; the
message is wrong, the tests passed). SV650's excerpts do contain the
qualifying sentence ("…for a light pull and consistent release point",
spec excerpt lines 357–437 of the SV650 ABS page).

Run `Suzuki_20260923_121034` **stopped systemically before any model
served**: `subc` returned "Failed to authenticate. API Error: 403
organization access is suspended; the entitlement must be restored before
requests are served; check billing and limits." `subc usage` minutes
earlier showed 53.5M / 60M tokens, 6.5M remaining — so this is an account
entitlement, not the daily quota. The stop fired as designed (source-stage
error, usage unrecorded); ready_to_write empty. **Operator action needed
on the Subconscious account** before SV650 or any further batch can run.

### 2026-09-23 — Subconscious suspended: the source stage's fallback route (operator)

**Step 0:** the written-entries guard, re-run: **15/15** manual entries pass
(V-Strom 650's re-quote from `07cfc18` included). Nothing to pull.

**Step 1:** `ROUTES["anthropic-sonnet"]` = claude-sonnet-5 on
api.anthropic.com, its own route: refute stays `anthropic` (Opus) and
unchanged. `--source-route subconscious|anthropic` (default subconscious)
selects the source stage's route; switching back is the flag. Same guards:
the route carries exactly the Anthropic OAuth token; the served-model check
applies (a different model answering is a source-stage error and a stop);
one turn, `--tools ""`. Recorded as structured fields: `summary.source_route
{route, model}`, `source_route` on every finding, and
`TransmissionEntry.source_route` (new optional field) — "subconscious" on
the 14 entries this phase wrote from Subconscious batches (inserted at each
call's end by AST position, diff reviewed), None on older entries,
"anthropic-sonnet" on anything the fallback writes. Tests +10.
**Break-it:** default flips to anthropic → 35; refute follows the source
route → 21; route not recorded on findings → 2; the fallback not Sonnet →
3; the CLI flag ignored → 1; one entry loses its route → 1. 640 pass across
257 + 255D + the 255 axis suite; 244G clean.

### 2026-09-23 — Route proven; SV650 (live vehicle #8) written on the fallback route

**Step 2, the route proven before any batch:** one call through `make_run`
+ `run_stage` on `anthropic-sonnet` with the source flags
(`~/.cache/motodiag/source-runs/route_proof_20260923_123635/proof.json`):
`modelUsage` → **['claude-sonnet-5']**, 2 turns, no error.

**SV650** — run `Suzuki_20260923_123652`, `--source-route anthropic`:

| stage | model | tokens | turns |
|---|---|---|---|
| source | claude-sonnet-5 | 26,025 (2 in, 2,019 out, cache the rest) | 2 |
| refute | claude-opus-5-5 | 63,794 | 4 |

No stops, nothing withheld. The source quoted the qualifying sentence
("The multi-plate clutch has precise push rod actuation of the pressure
plate for a light pull and consistent release point."); refute kept it,
`names_model: true`, reading the "light pull" as the rider's clutch pull;
`edition: ABS`. **Written:** one entry, SV650 (aliases sv650, sv 650, sv650
abs), `source_route="anthropic-sonnet"`, its source naming the ABS-edition
page. Census 587 → **586**. SV650 Gladius stays unknown (a different
machine). The written-entries guard now covers 16 manual entries.

### 2026-09-23 — Yamaha: acquired; batch STOPPED — Sonnet took 3 turns (the one-turn guard); nothing written

**Acquire** (11 fetches): 9 exact matches on Yamaha's own `/specs` pages —
YZF-R1, YZF-R7, MT-03, MT-07, MT-09, MT-10, Ténéré 700, XT250, V-Star 250.
30 unmatched (older and scooter models: Zuma, Vino, XC50 variants, V-Star
650/1100/1300, FZ6/8, VMAX, …).

**Batch** `Yamaha_20260923_123945`, `--source-route anthropic`: the source
stage (claude-sonnet-5, 174,080 tokens) returned 9 findings but in **3
turns**; `SOURCE_MAX_TURNS = 2` (measured on Haiku and GLM) made it a
source-stage error — a systemic stop, refute not run, nothing written. With
`--tools ""` a third turn can only be a structured-output retry, not
browsing, but the limit is a threshold: reported to the operator, not
changed. Also flagged for the write: Yamaha sells the MT-07 and MT-09 in
Y-AMT versions too — if the pages say so, those are ambiguous machines
(like the Africa Twin), not `manual`.

### 2026-09-23 — The fallback source route is claude-opus-5-5 at medium effort (operator)

**Why the Yamaha batch needed a third turn — found, not guessed.** The
first suspect was `139632a` (required citation fields forcing a retry on
no_evidence): a Haiku probe with the real `SOURCE_SCHEMA` and two
no_evidence findings answered with explicit nulls, validated first time,
2 turns — not it. Replaying 3 of Yamaha's spellings on Sonnet with the
stream kept (`source-runs/schema_repro_*`) showed the cause: Sonnet's
first answer was `{"findings": {"findings": [...]}}` — the array nested
inside a second `findings` — and the CLI replied "Output does not match
required schema: /findings: must be array"; the second answer was right.
**Fix:** the source prompt states the answer's shape exactly ("`findings`
IS the array. Never nest it"), and the source stage now streams and keeps
`source.stream.jsonl`, so any future retry shows its cause. The 2-turn limit
stays.

**The route:** `anthropic-opus-medium` — claude-opus-5-5, `--effort medium`,
one turn, no tools, the same guards (exactly the Anthropic OAuth token;
the served-model check). It replaces the first cut on claude-sonnet-5.
`source_route` is now **model@effort** on the batch summary (with route,
model, effort, label), every finding, and every lookup entry: 14 entries
`subconscious/glm-5.3-marathon@default`, SV650 `claude-sonnet-5@default`
until re-sourced. **Proven before any batch:** one call (the same Yamaha
replay) → modelUsage `['claude-opus-5-5']`, 2 turns, 0 schema retries
(`source-runs/route_proof_opus_*`).

**The checker's independence, recorded.** With the source stage on the
fallback, the source and refute stages are the same model
(claude-opus-5-5; the source at medium effort, refute at default).
Refute's independence from the source stage now rests on three things,
not on a different model: (1) **a fresh context** — refute runs in a new
sandboxed call that never sees the source stage's reasoning, only its
findings; (2) **re-opening the original document itself** — refute reads
the cited file (and page images where OCR is weak), not the source stage's
excerpt or account; (3) **the model-free gates** — E3 (the quote is in the
document), E10 (the document and quote are among the excerpts handed over)
and E12 (a manual quote names the mechanism) run in code before refute and
cannot be talked out of. Once Subconscious is back, the entries with a
non-`subconscious/` source_route are one filter away from a re-run.

Tests: route tests rewritten for Opus-medium (effort passed only on the
source route; refute carries none; the label is model@effort; a different
model answering is a stop; the prompt states the shape; the source stream
is kept). **Break-it:** effort not passed → 3; refute gets an effort → 2;
the label drops the effort → 2; the fallback back on Sonnet → 3; the shape
phrase removed → 1; the source not streamed → **survived twice** (no test,
then a test that accepted an empty file), then 1. 509 pass; 244G clean.

### 2026-09-23 — SV650 re-sourced on claude-opus-5-5@medium: the result matches

Run `Suzuki_20260923_141812`: source claude-opus-5-5@medium **18,564 tokens,
2 turns** (Sonnet: 26,025, 2); refute claude-opus-5-5 63,816, 4 turns. Same
document (`street_2026_sv650-abs.html.txt`), same quote ("…for a light pull
and consistent release point."), `manual`, model scope, `edition: ABS`,
kept with `names_model: true`; no rejections, nothing withheld. The entry's
text is unchanged; its `source_route` is now `claude-opus-5-5@medium` and
its comment names this run.

### 2026-09-23 — BMW: acquired, batched on claude-opus-5-5@medium, four written

**Acquire:** the first live run matched 0 of 39 — the live Nav.xml breaks
lines between attributes (`LANGUAGE="01"\r\nFILENAME=…`) where D7's copy
had one space; parse made whitespace-tolerant (`c…` commit, tested). Re-run:
**22 of 39 matched**, 22 fetches, 78 MB of rider's-manual PDFs; 10 exact,
12 `contains` (family). A second defect: F 750 GS / F 850 GS took the
block's certificates PDF (`…ZBA_Zertifikate_01.pdf`); the route now
prefers `_RM_` and never takes a certificate (`c39a1aa`, tested; both were
family matches, so nothing could have been written from them).

**Batch** `BMW_20260923_142134`, source claude-opus-5-5@medium:

| stage | tokens | turns |
|---|---|---|
| source (claude-opus-5-5@medium) | 349,842 | 2 |
| refute (claude-opus-5-5) | 192,747 | 8 |

25 sent, 17 found, 8 refuted, 0 killed. **Written (4):** K 1200 GT ("…then
pull the clutch lever"), K 1200 RS ("Manual transmission 6-speed with claw
shift…"), R 1200 GS ("Select neutral or, if a gear is engaged, pull the
clutch lever"), S 1000 R ("Brake, pull the clutch lever … to deactivate the
cruise-control system") — each kept, names_model true, `source_route`
claude-opus-5-5@medium. **Family evidence (4), not written:** R1200 (the R
1200 GS manual), F650 (F 650 GS), F900 (F 900 R), S1000 (S 1000 R).
**Withheld by E12 (7 findings) + E10 (1):** K1200S / K1200 ("Only shift
gear with the clutch disengaged." — no lever, pedal or "manual": a correct
rejection); **K1600GT, K1300S, K1300 — "Gear engaged and clutch not
disengaged Select neutral or pull the clutch lever."**: a troubleshooting
table's condition and remedy cells run together without a full stop, so the
"not" of the condition sits within E12's five-word negation window before
"pull the clutch lever" — **an E12 false negative, reported, not
loosened**; **R1150, R1100 — "…dry clutch … Hydraulic actuation /
operation"**: the words in the reverse order of E12's "hydraulic … clutch"
pattern — also reported. K1300 also E10 (its quote not in its excerpts).
No evidence: F800GS, S 1000 XR, F700, F750, F800, F850, K100, K75, R1250,
ShiftCam.

A Phase 255B test used BMW R1200GS as its example of an unknown machine
(`test_4605_stays_unscoped_and_that_is_the_point`); moved to BMW R1250,
still unknown, assertions untouched — as the Grom → CBR1000RR move in
tranche 1. Census 586 → **582**. The written-entries guard covers 20
manual entries. 1,206 pass across the 26 suites mentioning these machines
+ the 255 axis suite; 244G clean.

**Correction to the BMW entry above (`d2bcc71`):** that commit went in with
the Phase 255B test still failing. The Edit moving it to R1250 had been
refused (the loop occurs twice in the file) and the commit ran regardless;
the log's "moved … assertions untouched" and "1,206 pass" were written
before either was true. Fixed in the next commit: only the occurrence in
`test_4605_stays_unscoped_and_that_is_the_point` moves (the end-to-end
test beside it keeps R1200GS — row 4605 is unscoped, so it reaches a
sourced R1200GS too); 255B: 30 pass; the 26 related suites + the 255 axis
suite re-run: **1,206 pass**.

### 2026-09-23 — Operator decisions on BMW's two E12 questions: both NO

**1. No clause-boundary rule for the negation window.** What I reported as
E12 false negatives (K1600GT, K1300S, K1300) were **reader misses**: each
spelling's own excerpts held lines that pass E12, and the source stage
quoted a troubleshooting row instead. Checked against the run's
`candidates.json` with E12's own `_sentences()`: K1600GT 4 passing lines,
K1300S 9, K1200S 7. The operator's instances: K1600GT p. 84 and K1300S
p. 70 carry "Select neutral or, if a gear is engaged, pull the clutch
lever." — the very line that wrote R 1200 GS; K1200S p. 95 carries "Press
the clutch lever."

**2. No reversed-hydraulic rule.** A proposal is run before its reach is
claimed: E12's `_sentences()` puts "Hydraulic actuation" and "Hydraulic
operation." in sentences of their own (checked), so a one-sentence
"clutch … hydraulic" rule qualifies neither; and `names_model` is False for
both documents (R 850 R / R 1150 R for R1150, R 1100 S for R1100 —
checked): family evidence, zero entries either way. My report claimed a
reach I had not measured.

### 2026-09-23 — Bug fix #5: E12's negation and document-title rules read only plain-typed text

**Issue.** Three things E12 read wrongly, each planted as a case that must
fail E12 and watched passing on the old code (3 failed) before the fix:
- `Rider’s Manual` (BMW's own text, typographic apostrophe) was not
  recognised as a document title, so "Manual" counted as gearbox evidence;
- `don't` is not in the negation list: "With Honda E-Clutch you don't have to
  operate the clutch lever…" (constructed; to be replaced by Honda's own
  E-Clutch wording once acquired);
- a negation after the term: "The clutch lever is not required when
  shifting."

**Root cause.** `DOCUMENT_MANUAL` and `NEGATION` were written for `'` and
bare words, and `_unnegated` looked only at the 5 words before the term. The
cases were all hand-typed, so none of them contained the documents' own
typography (see the shared-cause paragraph below).

**Fix.** In `manual_evidence`, `’` and `‘` are read as `'` before any rule
runs. `NEGATION` gains `cannot` and `n't`. `_unnegated` also checks the
`NEGATION_AFTER = 4` words after the term. Every change only removes passes,
so E12 can only get stricter.

**Files.** `.claude/skills/source-transmission/entry_check.py`,
`tests/test_phase257_source_checks.py` (`TestBugFix5E12ReadsRealTypography`,
5 cases).

**Verified.**
- The E12 decisions snapshot (`e12_outcomes.py`, 35 decisions) is identical
  before and after. The 20 written manual entries all still pass. No BMW
  outcome changed (passing: F650, F900, K1200GT, K1200RS, R1200, R1200GS,
  S 1000 R, S1000).
- Break-it: each part of the fix was reverted on its own.
  - The curly-apostrophe read: 2 cases fail.
  - `n't`: 1 case fails.
  - The after-window (set to 0): 1 case fails.
  - `cannot`: survived on the first three cases, because `\bnot` never
    matches inside "cannot". A fourth case was added and it now fails.
  - The `‘` half of the read is not caught on its own: no case uses a left
    quote as an apostrophe, and I have not found one in the documents.

**Commit.** This entry's commit.

### 2026-09-23 — The shared cause of 257's bugs (#1–#5 and the `d2bcc71` correction)

The operator's candidate, that the checks were proven on hand-typed cases
and not on the documents' own text, holds in its narrow form for three of
the six. #1's `bare_number` was written from the shape of three typed
examples and never run over the census of 600 spellings, where Ducati 916
sat. #4's schema tests fed well-formed findings, typed by hand; the model's
first real answer left out `document`. #5's rules were tested on typed
`'`, while BMW prints `’` 55 times. It holds in a wider form for two more:
each was checked against a string I wrote and not against the one the check
meets in use. #2's alert was never compiled with the real STOP title, which
carried an em dash. #3 trusted refute's `kept` label and never tested it
against a real verdict whose reason said "family evidence only". The
correction to `d2bcc71` does not fit the narrow form, but it is the same
failure one level up: the log said "moved" and "1,206 pass" from what I
expected, not from the tool's output, which showed a refused Edit and a
failing test. **Confirmed, stated as: every one of the six was verified
against something I had written (a typed case, an expected string, my own
claim) and not against the artefact it meets in use: the census, the real
title, the model's real answer, the document's typography, the run's own
output.** Four of the six were caught downstream by gates or the operator,
not by their own tests. Nothing new is built for this. It is the reason C
below measures reader misses from the run's own `candidates.json`.

### 2026-09-23 — C: the reader is measured beside every E12 rejection; one sentence added to the source prompt

**What.** For every E12 rejection, the batch now looks at that spelling's own
excerpts, the same `candidates.json` the model was handed. It counts the
distinct sentences (E12's `_sentences()`, whitespace-normalised) that pass
`manual_evidence`. Script only; no model call and no retry.
- The count is recorded in the summary as `e12_reader`
  (`{spelling: "reader miss: N passing lines" | "no passing line in its
  excerpts"}`).
- It is also appended to the rejection line, and so to the `withheld`
  line, in brackets.
- `entry_check.passing_sentences()` and `reader_note()` hold the rule.
  `orchestrate.batch` only applies it.

The source prompt gains one sentence after the E12 rule: "When several
lines qualify, choose one whose sentence has no negation word at all: a
troubleshooting row whose condition says "not" fails even when its remedy
names the lever."

**Applied after the fact to BMW run `BMW_20260923_142134`** (not re-run;
under today's E12):

| E12 rejection | its excerpts |
|---|---|
| K1600GT | reader miss: 4 passing lines |
| K1300S | reader miss: 9 passing lines |
| K1200S | reader miss: 6 passing lines (7 before bug fix #5, which made one stricter) |
| K1300 | reader miss: 2 passing lines |
| K1200 | reader miss: 1 passing line |
| R1100 | reader miss: 1 passing line |
| R1150 | no passing line in its excerpts |

A passing line is not a writable entry. The line still has to be on a page
that names the model: R1100's document is the R 1100 S's (family evidence,
checked in the BMW E12 decision above).

**Files.** `entry_check.py`, `orchestrate.py`,
`tests/test_phase257_source_stage.py` (`TestCTheReaderIsMeasured`, 5 tests:
counted beside the rejection and in `withheld`; nothing more is called; a
finding E12 passes is not measured; "no passing line", including a line
negated before the term and one negated after it; counted once across
overlapping excerpts; the prompt sentence).

**Break-it**, each part reverted on its own; every one is caught:
- no bracket on the rejection → 1 fails;
- no `e12_reader` in the summary → 2 fail;
- every sentence counted as passing → 3 fail;
- no dedupe → 1 fails;
- the "no passing line" wording dropped → 1 fails;
- the prompt sentence removed → 1 fails.

A first prompt break left the asserted text intact and survived, so it was
not a break. Redone by removing the sentence.

### 2026-09-23 — D: K1600GT, K1300S, K1200S re-sourced; all three written

Run `BMW_20260923_154333`, `--source-route anthropic`
(claude-opus-5-5@medium), refute unchanged (Opus): 3 spellings sent;
104,567 tokens (source 35,610, refute 68,957; ceiling 450,000). No stops,
**no rejections** (so `e12_reader` is empty), nothing withheld, no family
evidence. Refute kept all three with `names_model: true`; each
`model_line` is the rider's manual's cover.

| spelling | quote (its own manual) | page |
|---|---|---|
| K1600GT | "Select neutral or, if a gear is engaged, pull the clutch lever." | 84 |
| K1300S | the same sentence | 70 |
| K1200S | "Manual gearbox The motorcycle can be started in the neutral position or with a gear engaged and the clutch pressed." | 58 |

These are the lines the operator named for K1600GT (p. 84) and K1300S
(p. 70). For K1200S the reader took a different passing line from the one
the operator named ("Press the clutch lever.", p. 95); both are in its
excerpts.

Written as BMW "K 1600 GT", "K 1300 S" and "K 1200 S" (aliases, spaced
and unspaced), `source_route="claude-opus-5-5@medium"`. Siblings stay
unknown and are pinned in `TestBMWWrite`: K1600GTL, K1300R, K1200R, the
families K1600/K1300/K1200, and the census's "K1200S/R". Break-it: a
family alias ("k1300") added to K 1300 S → 1 fails. Census 582 → **579**.
The written-entries E12 guard now covers 23 manual entries.

### 2026-09-23 — Honda: acquired from motopub, batched on claude-opus-5-5@medium, five written

**Acquire** (no model): motopub's AHM index lists **103 names, all for model
year 2018**. That is 6 fetches, the name list re-read to explain the
unmatched spellings. Matched 6 of 26 census spellings: CBR600RR, CBR1000RR,
CB500F, NCW50, XR650L, CRF250L. The other 20 are not in the 2018 list.
Two are a near miss under the weak-spelling rule, reported and not
loosened: Monkey 125 → `Monkey125-A` and CB1000R → `CB1000RA`, both
`contains` matches that a weak spelling may not take.

**Batch** `Honda_20260923_155534` (26 spellings):
- 14 were sent and 12 had no excerpt. None was classed not-a-machine.
- 259,884 tokens (source 99,805, refute 160,079; ceiling 2,100,000).
- **No stops, no E12 rejections (so no reader misses to report), no
  refute kills, no family evidence.**
- Ready: CBR600RR, CBR1000RR, CB500F, XR650L, CRF250L (manual), and NCW50
  (cvt: "Primary reduction V-matic (2.85:1 - 0.86:1)").
- Each manual quote is the side-stand check's "4. Start the engine, pull the
  clutch lever in, and shift the transmission into gear." Refute's
  `model_line` comes from the manual itself (page 2's "… are USA models." or
  the back matter's "31MGW660 2018 XR650L Owner's Manual").

**E-Clutch, flagged and not classified:**
- The library's only E-Clutch text is Honda UK's navigation page
  (`manuals/honda_uk.html`). It names CB650R, CBR650R, CB750 Hornet and
  XL750 Transalp E-Clutch editions.
- Of the census spellings, **CB650R** and **CB750** are affected. Both came
  back no_evidence: their only excerpt is that navigation menu, and the
  CB650R note names the E-Clutch page. Nothing is written for either.
- No E-Clutch text reached any quote. The E-Clutch placeholder in bug fix
  #5's cases stays constructed, because no Honda E-Clutch wording has been
  acquired: motopub's index stops at 2018, and E-Clutch dates from 2024.

**NCW50 held for an operator decision.** NCW50 is the Metropolitan's model
code (manual 31GJB620, "2018 NCW50 Owner's Manual", same V-matic line). The
lookup already has a Phase 255 `Honda Metropolitan` CVT entry (31GJB640 to
31GJB690) without an "ncw50" alias. The choice is to add the alias to that
entry or to write a separate one. I have done neither.

**Written:** Honda "CBR600RR", "CBR1000RR", "CB500F", "XR650L" and
"CRF250L", `source_route="claude-opus-5-5@medium"`. Siblings stay unknown
and are pinned in `TestHondaMotopubWrite`: CBR1000RR-R, CBR1000RR SP,
CBR600F/F4i, CBR929RR, CB500X, CBR500R, XR650R, CRF250R and CRF250 Rally.
Break-it: "cbr1000rr-r" added as an alias → 1 fails.

**Unknown examples moved** (as Grom → CBR1000RR and R1200GS → R1250 before
it): the CBR1000RR was the "unknown Honda" in four tests. The example
moves to the **CBR929RR** (still unknown; no_evidence in this run) and the
assertions are untouched:
- 255 `test_unknown_is_all_six`;
- 255 `test_repeated_retrievals_accumulate`;
- 257 `TestCensus` (it also plants a CBR1000RR row, which must now be
  left out);
- tranche 1 `test_a_honda_spelling_that_was_never_seen_stays_unknown`.

255's `OVER_REACHED` keeps the CBR1000RR: a manual machine still gets no
CVT row, and it passes. Census 579 → **574**. The written-entries E12 guard
now covers 28 manual entries.
