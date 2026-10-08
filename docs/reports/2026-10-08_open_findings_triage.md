# Open findings triage: moto-diag backend, 2026-10-08

2026-10-08. Covers every backend finding open on `master` at `5563e53`: 47 entries (F115–F197), plus the open part of F158. This copy in the repository is the canonical one. moto-diag-mobile's own FOLLOWUPS has 15 open findings, which this triage does not cover.

Every claim below was measured on 2026-10-08 from:
- `docs/FOLLOWUPS.md`, each open entry read in full;
- the code on `master` at `5563e53`;
- the phase documents in `docs/phases/completed/`;
- a backup-API copy of the live database, for F115.

When the triage was written, nothing in it had been changed. Your decision goes above the triage when you give it.

---

## The recommendation

1. **Close 11 now, docs only** (A below). Nine are already fixed or closed but their headings still read open. Two are records with nothing left to fix.
2. **Phase 379, small fixes** (B): nine items, code and tests only, no live rows. One may move the API snapshot.
3. **Phase 380, row identity, then a content batch** (C): F129 first, because five content findings were left unfixed for want of it; then the content edits, each a live-row change with your approval.
4. **Shop features when a shop needs them** (D): F185 (tax-exempt sales) before the first exempt customer is invoiced; F192 before a shop in a second time zone.
5. **Sourcing and design calls stay parked** (E, F) until the reference-data track, or until you decide.

## What the open list looks like

- **47 open**, the oldest F115 (2026-09-21).
- **30 are knowledge-base items** from the September content phases (254–260 and 353–359): retrieval, the transmission axis, rows' wording and sourcing.
- **9 are process items:** the guards, the test suite and the rules' own documents.
- **8 touch what a shop does:** the garage, invoices, sensors, video, scan adapters and taxes.
- **9 of the 47 are stale**: they are fixed, or closed in their own text, but their heading was never marked.

---

## A. Close now (11), docs only

**Already fixed or closed (9):**

| finding | why it can close | evidence |
|---|---|---|
| F115 | A Harley or BMW owner now reaches row 4605 | measured on a live copy: `Harley-Davidson Road King` and `BMW R1200GS` reach 4605 through `known_issues_for_vehicle` and `rows_for_machine`; `Yamaha Bolt` and `Honda PCX 150` reach it too. 255B added the makes |
| F119 | closed in its own text | "CLOSED-UNOBTAINABLE, operator's decision 2026-09-21" |
| F122 | the option it asked for was built | 256's D7: a corrupt row is excluded and logged, and its count persisted; diagnosis no longer stops (`retrieval.py:96–124`) |
| F123 | closed in its own text | "CLOSED 2026-09-21 by Phase 256" |
| F124 | closed in its own text | "CLOSED 2026-09-21", guard `tests/test_f124_schema_pin_discipline.py` |
| F125 | its closing check exists | `roadmap_check.py` R5, "the two copies of ROADMAP_AUTHORITY.md are identical", run with every suite and on every push since 2026-09-24 |
| F126 | all three defects fixed | the column and the bare `except` in `8e7db70`; the substring match went with 256's chokepoint (`priority_scorer.py:318` calls `rows_for_machine`) |
| F128 | what 255B owed was done | 4609 dropped the Filly and 4615 was split, as the 256 guard's own comments record; Beverly 250 and Vespa 946 are closed-unobtainable under F119; the guard `TestNoRowExcludesAMachineItNames` stays |
| F139 | its closing condition is met | 257's census is built on the figures of record (`257_step0.md` S0-1; 605 pairs reproduced) |

**Records, with nothing left to fix (2):**
- **F120:** Piaggio's "direct drive" means a CVT. In its own words this is "a documentation hazard rather than a runtime one", since nothing reads document text to classify.
- **F136:** "every consumer" was counted over `src/` only. The seventeenth consumer was found by 255C's regression. The lesson, that a search's scope is part of its claim, is now in the working-rules index.

---

## B. Phase 379: small fixes, code and tests only (9)

| finding | the fix | note |
|---|---|---|
| **F197** | `verify-live` exits non-zero when live does not equal the approved diff, and says when the cause is a later migration; check 8 fails on it | found this morning |
| **F176** | `garage remove` refuses a bike that work orders or saved runs name, says which, and exits 1, instead of an `IntegrityError` traceback | what a mechanic sees |
| **F193** | sensor and drift `--since` and `--until` converted by 377's `utc_cutoff` and written in the column's own shape | keeps the index |
| **F154** | `fiddle 50` added to the Fiddle entry in `TRANSMISSION_LOOKUP`, evidenced by the manual the entry already cites | one line; Gate 14 pins it |
| **F155** | plurals stemmed in `relevance_tokens`, so a belt symptom cannot cost the LX 50 its own row | Gate 14 pins it |
| **F131** | each of the six lookup entries' canonical names resolves to its own entry | one is a name riders type |
| **F140** | an assertion over a built database that no row declares `{manual}`, with a planted row that fails it | the live table holds 0 today |
| **F173** | `wholetree.py` stops truncating pytest's output to the last 1500 characters (`wholetree.py:259`); then close on the run count | it has passed in every regression since 359 |
| **F144** | video `/ask` passes the vehicle's powertrain to retrieval | `VehicleContext` is an API model (`media/vision_types.py:262`, used by `api/routes/videos.py`); if the snapshot moves, a mobile session |

**Size:** small, with no live-row change. F144 is the only item that might need a mobile session.

---

## C. Phase 380: row identity, then a content batch

**The keystone, F129:** a row's identity is its make, model and title. Correcting any of those duplicates the row instead of updating it. F149, F151, F152 and F153 each say they were left unfixed because of it.

**With it, F142:** multi-make rows put every model under every make in the junction (192 pairs at most). The fix rebuilds the junction per model's own make.

**Then the content edits.** Each changes live rows, so each is a stop for your approval:
- **F152:** one sentence of the CHF50 row, made to say what the cover shows;
- **F153:** SYM's own spellings on the CVT rows, so a SYM query reaches them;
- **F156:** a 2002–2006 Metropolitan bridged to the CHF50 rows, and a 2018 one not;
- **F149:** three Honda `model = All` charging rows narrowed or sourced;
- **F164 and F171:** three wordings left by earlier refutes;
- **F158:** the build references its patterns do not match.

**Size:** medium for the identity, plus one content migration.

---

## D. Shop features, when a shop needs them (4)

- **F185, tax-exempt sales.** A customer or an invoice marked exempt, with the certificate's kind and number. Needed before the first exempt customer is invoiced. Business rules decide it, as in 373.
- **F192, a time zone per shop.** It changes nothing for one shop on a server in its own zone. Needed before a second zone.
- **F180, rotary and diesel engines.** No live bike needs them; it moves the API, so it needs a mobile session.
- **F195, tax on parts given away.** It needs the shop's accountant first, then sources and a cost basis.

## E. Needs sources first (5)

These wait for the reference-data track, or for a sourcing batch with the Subconscious plan (K11):
- **F150:** a SYM document tying "model ABA" to the Symply 125;
- **F170:** a Triumph document for the Street Triple 675's engine management;
- **F157:** adapter vendors' coverage lists for the scooter makes;
- **F127:** OCR for four unreadable manuals;
- **F143:** transmission coverage, with 528 spellings still unknown.

## F. Your call, or park (10)

- **F167, F168 and F169: the guards' reach.**
  - F167: the signing key is readable by an agent.
  - F168: a push from a terminal is never checked.
  - F169: other repositories' pushes are judged against moto-diag.

  Each changes what the guards trust or guard. Worth doing if you push from a terminal, or want the guard to hold against the agent itself.
- **F138:** the workspace `CLAUDE.md` is 926 lines. Deciding what stops being shared is your call.
- **F135:** what the corpus means by a "model". A design question that 255C left open.
- **F117, F118 and F130: new axes for cooling and final drive,** and the predictor's corpora, which have no applicability field at all. Each is a feature-sized change to retrieval.
- **F116:** a substring search on "manual" matches the word "manual" in documents. Low impact since 255B, which selects rows by axis.
- **F151:** whether each of the 80 `cross_platform_*` rows is general or specific. It is 80 decisions, best taken with the reference-data track.
