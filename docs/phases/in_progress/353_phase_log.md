# Phase 353 — Small-engine carb service (single/twin-barrel) — phase log

**Status:** 🚧 In progress
**Opened:** 2026-09-24

---

### 2026-09-24 — Opened after 354

Taken before 258 per `docs/handoffs/2026-09-24_354_closed.md`: Gate 14
queries a scooter for CVT, electrical and carb content, and carb (353) is
the last of the three not built. Read before acting: the handoff, ROADMAP
rows 353, 354 and 258, `ROADMAP_AUTHORITY.md` (353 is backend, 205+),
`354_implementation.md` (v1.1) and its phase log, FOLLOWUPS F149, F150,
F142, F127, F129.

Branch `phase-353` from `master` at `0b0ac2c`, in sync with `origin`.
`roadmap_check.py` exit 0; ROADMAP row to 🚧 before Step 0 at `ee4a979`,
pushed.

**Standing rules for this phase (operator, same as 354):** stop once after
Step 0 only for a real fork, otherwise log each decision here and carry
on; bulk reading through Subconscious, refute on Opus; the whole-tree
gates (191C F9 lint, 244G, finding_check B2) on every pre-commit run;
close-out through merge and push; a new dated handoff naming 258 next.

**Decision (logged, not asked):** 354's reading pipeline is reused with
the field list swapped (`~/research/motodiag/353_step0/`). Two changes,
each for a measured reason:

- **Every library PDF is extracted, not a name-filtered set.** 354's file
  name filter missed `honda/ruck_*.pdf` (the four Ruckus owner's manuals
  Phase 252 read), the budget `Lance_*` manuals and the Dio. Documents are
  then selected by carburettor vocabulary, and a document outside the
  class is excluded by what its own title page prints (KTM 950 Super
  Enduro R, YZF600RW, XR650L, Bonneville; the MP3 500 as injected).
- **354's extracted page text was not kept** (`354_step0/` holds the
  index and sweep output, not the page files), so extraction re-ran:
  271 PDFs, 264 unique, 246 extracted, 18 unreadable by pypdf, 14 with
  no text layer.

### 2026-09-24 — Step 0: extension, content only, no fork

Measurements S0-1..S0-13 are in the implementation doc. In short: Track M
holds no carburettor service. The corpus's only carburettor-service rows
are ten unsourced big-bike rows filed under one make and model each, so no
carburetted scooter reaches a row about its own carburettor. The row's
"Keihin/Mikuni" is true for the Piaggio four-strokes and the Vino, and
false for the two-strokes (Dell'Orto, Teikei). The Kymco, SYM and CHF50
service manuals name no maker.

**Decision (logged, not asked): no fork.** Every question had a default
354 set: one make per row, written from verified quotes, an older defect
filed rather than patched (D5), title-page identity. One apparent fork,
how to label owner's-manual-only rows, already has an answer: 252 and
253 label them `service-manual` and say in the text which document it
is. 353 follows that.

**Decision:** the XV250 stays out (D7). It is the class's only twin, its
owner's manual prints "BDS26 × 1" and then "float chambers" in the
plural, and one manual is not enough to settle that.

**Decision:** R8 (Genuine) is a ceiling item only. The one Genuine service
manual is PGO's "PA 100 / 125" and never names the Buddy (S0-12, 354's
R7).

**Sweep:** 41 documents, 1,300 facts, 1,207 verified, 7% dropped, every
call parsed first time.
