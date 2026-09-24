# Handoff — Phase 257 after the owner's-manual routes

**Written 2026-09-23** for a fresh session started **at the repository
root** (`~/Projects/moto-diag`). This file follows
`2026-09-23_257_after_honda.md`, which is still the reference for the
standing rules; this file restates only what changed and what is next.
Every fact below is a commit hash or a measured result. The full record is
`docs/phases/in_progress/257_phase_log.md`, from "Triumph: batched on
claude-opus-5-5@medium" onward.

## Start here

1. This file.
2. `docs/phases/in_progress/257_phase_log.md`: the entries dated
   2026-09-23 after the Honda handoff (Triumph batch → Triumph blocked).
3. `.claude/skills/source-transmission/SKILL.md` and `CHANGELOG.md`.
4. `2026-09-23_257_after_honda.md`: standing rules and older open items.

## Where 257 stands

| | |
|---|---|
| branch | `phase-257-orchestrator`, pushed; 83 commits ahead of `master` |
| 257 tests | 594 collected in `tests/test_phase257_*.py` |
| related suites at the last code commit (`1e35b74`) | 257 + 244G + 255D: **667 passed** |
| regression of record | 8,145 at `486e847` (255D). **257 has not run one.** |
| `COLLECTED_TEST_FLOOR` | still 8145 |
| census (unknown machine spellings) | **573**, unchanged today |
| `TRANSMISSION_LOOKUP` | 77 entries, unchanged today (50 hand-sourced, 14 Subconscious, 13 claude-opus-5-5@medium) |

Nothing was written to the lookup today. Every change was to the
procedure, and two manuals were acquired.

## Today's decisions (operator), each its own commit

| decision | commit |
|---|---|
| Triumph batch logged: 72 spellings, 15 sent, 1 found, 1 E12 rejection, 0 written. Spec pages give the gearbox only as table cells | `d1719e7` |
| **Dry run before the source call.** A spelling is sent only if an excerpt sentence passes E12 or names a non-manual mechanism; the rest are `no_evidence`, "no mechanism line in the fetched pages"; the counts are in `summary.mechanism_lines` | `34b1d76` |
| **E12: the word "manual" counts only within three words of transmission, gearbox, gear shift or a gear count.** All 28 written manual entries still pass | `fec8c3a` |
| Dry-run words added: V-belt, variator, single-speed (and "automatic", then narrowed) | `80000c2` |
| **Dry run: "automatic" counts only within three words of transmission, gearbox, belt, clutch or drive.** Triumph's tyre line, BMW's ASC and Honda's "automatic reset mode" no longer count | `f374f73` |
| SKILL.md: the fallback source route is claude-opus-5-5@medium | `8d97f24` |
| **E11 host: `library.ymcapps.net` for Yamaha**, the host seen serving its manual | `af035f1` |
| The planted V-belt case is now Yamaha's own spec rows (Vino 125, p. 8-1) | `5424baa` |
| **E11 via referrer, not host, for KTM.** `links_to` reads a JSON referrer's string values (exact URL, never resolved). The Azure CDN host is **not** a KTM host | `f760079` |
| **acquire.py POSTs, and every sidecar records its `request`** (method, headers, body). Vino 125 re-fetched through acquire.py; PDF sha256 unchanged | `1e35b74` |
| **Triumph blocked** (403, downloads switched off); the viewer is not tried; waits for the inbox | `4b439cf` |

The dry run over the real runs, under all of the above: BMW 142134 sends
14 and BMW 154333 sends 3 (every written spelling kept), Honda 155534
sends 9 (every written spelling kept), Yamaha 123945 sends **0** and
Triumph 172417 sends **0**.

## Owner's-manual routes (measured; no route code in `acquire.ROUTES` yet)

### Yamaha: the Owner's Manual Library API (JSON POST)

- The portal is linked from every acquired yamahamotorsports.com spec
  page (`acquired/Yamaha/models_*_specs.html`):
  `https://library.ymcapps.net/library/om/app/index.html?baseCode=6150&langId=02`.
- The API is `https://parts.yamaha-motor.co.jp/ypec_b2c/services/omb2c/`,
  all calls POST JSON, sending the Origin and Referer of the portal:
  1. `product_list/` `{baseCode: "6150", langId: "02"}` → `userContext`
     (destination USA, userGroupCode AL01).
  2. `model_name_list/` `{productId: "10", displacementType: "1".."10",
     baseCode, langId}` → 10 buckets, **153 names**.
  3. `model_year_list/` `{productId, modelName, nickname, userGroupCode,
     destination, destGroupCode, baseCode, langId}`.
  4. `model_list/` `{productId, calledCode: "1", modelName, nickname,
     modelYear, ...userContext, baseCode, langId, publicationLang: "02"}`
     → `pdffileURL` (protocol-relative).
- The PDF is on **`library.ymcapps.net`** (in `MAKER_HOSTS`), not on the
  API host (not added).
- Acquired: Vino 125 2009, 5YR-F8199-15,
  `https://library.ymcapps.net/library/om/contents/pdf/10/5YR-F8199-15_02.pdf`.
  88 pages, sha256 `3c14851382b799b13e58395945daee10967c2b215326e7402926f9486bcf6f66`,
  referrer the saved `model_list` response. The sidecar records the POST.
- **Exact census matches: 20 of 39.** YZF-R1, YZF-R6, Tenere 700, YZF-R7,
  YZF600R, MT-09, SR400, Vino 50, WR250R, XT250, Bolt, MT-07, V-Star 1300,
  V-Star 250, Vino 125, FZ6, FZ8, MT-03, MT-10, Vino Classic.
- Refused by the weak-spelling rule, reported and not loosened: Zuma
  (ZUMA 125/50…), V-Star 650 and V-Star 1100 (V STAR 650 CLASSIC…).

### KTM: ktm.com's bikemanuals endpoints (GET)

- Named by `https://www.ktm.com/en-us/service/manuals.html`
  (`data-suggestionsurl`, `data-manualsurl`). Base:
  `https://www.ktm.com/en-us/service/manuals/_jcr_content/root/responsivegrid_1_col/bikemanuals`.
  1. `.suggestions.json?query=<text>` → `data.bikes[].name`, as
     "<model> <year>".
  2. `.manuals.json?modelName=<model> <year>` →
     `data.manuals[] {modelName, title, link}`, one row per market. EU and
     US can be different PDFs (390 Duke 2024: `24_3214960` EU,
     `24_3214961` US).
- Links are on `azwecdnepstoragewebsiteuploads.azureedge.net`. That is
  **not** a KTM host. A PDF passes E11 because the saved ktm.com
  `manuals.json` lists its exact URL, so **the manuals JSON must be saved
  as each PDF's referrer**.
- Acquired: 390 Duke 2024 US, `…/24_3214961_en_OM.pdf`, 143 pages,
  sha256 `6bb8fc51338ed85a50bd8b5b69d8e427e7ba9694fc9f12b8f4e83f89c8d18aac`.
- **Exact census matches: 26 of 41** (plus 2 contains: 1290 Super Duke →
  1290 Super Duke R, Super Adventure S → 1290 Super Adventure S). The
  exact ones: 790 Adventure, 890 Adventure, 790 Adventure R, 890 Adventure
  R, 300 EXC, 390 Adventure, 1290 Super Adventure, 390 Duke, 790 Duke,
  1190 RC8, 1290 Super Adventure R, 1290 Super Duke R, 500 EXC-F, 690
  Duke, 690 Enduro, 890 Duke, 1090 Adventure R, 1190 Adventure, 125 Duke,
  250 EXC TPI, 390 Adventure R, 450 SX-F, 690 SMC, 890 Adventure R Rally,
  950 Super Enduro R, RC 390.
- "Not Found" for LC8, LC8c, 350 SXF, 690 Duke 4, CAN Keihin and LC8
  V-twin.

### Triumph: blocked

- The handbook list is reachable: `api.triumphtechnicalinformation.com`,
  306 model names, 32 of 52 census spellings (25 exact).
- **The download is not.** `/documents/{id}/download` returned 403;
  downloads are switched off for the public. The viewer is behind
  reCAPTCHA and is not to be tried.
- **Triumph waits for the inbox route** (`inbox/Triumph/`, then
  `acquire.py ingest`).

Probe responses are in `~/.cache/motodiag/om_probe/`, and script reads in
`~/.cache/motodiag/d7/` runs `20260923_174220`, `_175344`, `_180930`,
`_181321` and `_181419`.
The probe drivers were scratch files; the method is in the log, and the
routes still have to be written in `acquire.py`.

## Next step

1. **Bulk-fetch the matched Yamaha and KTM manuals through `acquire.py`.**
   - Write each route into `acquire.ROUTES`: Yamaha's four-call chain
     with `Fetcher.post_json`; KTM's suggestions → manuals.
   - For each **exact** census match, take the newest year's US English
     owner's manual. Save the list response first, as the PDF's
     referrer.
   - 30 fetches a run, 1 a second, robots.txt honoured, and a 403 never
     retried.
   - Fixtures and break-it for each route, as for the others. Its own
     commit.
   - Decide with the operator before fetching the 2 KTM "contains"
     matches (the 4609 rule: they source only if the manual names the
     model).
2. **Then source one make at a time:**
   `orchestrate.py batch MAKE --source-route anthropic`.
   - The dry run decides what is sent.
   - Report before writing, one make per commit.
   - For Yamaha, the MT-07 and MT-09 have Y-AMT versions: a manual naming
     both makes the machine ambiguous, not `manual`.

## Open items

- **New today:**
  - The saved list responses from the Yamaha API host and from Triumph's
    API (`acquired/Triumph/handbooks_documents.json`) fail E11 by design.
    They are records, never evidence.
  - The two real-file E11 tests skip on a machine without the library.
- **Carried from the Honda handoff, all still open:**
  - Subconscious is suspended (`--source-route anthropic` only).
  - The E-Clutch decision (CB650R, CB750).
  - Honda's 12 unsent spellings.
  - The Ducati/Piaggio inbox ingest smoke test.
  - `COLLECTED_TEST_FLOOR` must rise before the full regression, which
    257 has not run (clear `__pycache__`, `-B`, the 244G scanner over
    `tests/` first).
  - Closeout.
  - `VARIANT_TOKENS` lacks "rt".
  - `TestCensus` still plants Ducati "Panigale V4".
  - F142.

## Standing rules (unchanged; full list in the Honda handoff)

- Work on `phase-257-orchestrator`.
- One make per commit for writes, and each code change in its own commit,
  with the related suites' pass line in the message, written through a
  quoted heredoc.
- Fixtures and break-it for every change. A break that survives because
  it was not a real break is redone, and the log says so.
- Never loosen a check without an operator decision; report tightenings.
- Targeted edits only on source and tests (no `sed -i`).
- Maker documents live outside the repository; the production DB is
  read-only.
- State a result only from the tool output that shows it.
