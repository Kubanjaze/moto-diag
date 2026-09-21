# Phase 255 — The transmission axis — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-21

---

## 2026-09-21 — Plan v1.0

Row 255 was planned as a content row about twist-and-go versus manual small
bikes. Its first Step 0 measurement found that the corpus cannot express that
distinction at all, and that **Phase 254 — closed the same day — shipped a
defect because of it.** Every Honda and Yamaha now retrieves the generic CVT
layer: a CBR1000RR gets 7 CVT rows, a Gold Wing 7, an XS650 8. A Kawasaki Ninja
400 gets 0, which isolates the cause to the make column rather than the content.

By the delivery standard written earlier the same day, that is a **validation**
failure and not a verification one. Phase 254 passed 85 tests, 22 of 22
mutations, a 986-test blast radius and a 7,750-test regression, all green, and
still reaches machines it does not describe. The operator's call: 255 becomes the
mechanism, the content row follows as 255B, and the over-reach is logged as a
dated bug-fix entry against 254 with its own commit.

Two things shaped the design more than anything else.

**250B cannot be copied, for two independent reasons found by reading its code
rather than its docstring.** It *reorders* rather than excludes —
`_electric_first` returns `electric + [everything else]` and removes nothing — so
copying it would leave CVT rows in a CBR1000RR's prompt. And it infers a row's
powertrain from the row's *marque names*, with `is_electric_row` documented as
"deliberately generous". That generosity is exactly what breaks here, because
Honda and Yamaha build both scooters and motorcycles. 255 diverges on both
points, deliberately, and 250B is not touched.

**The Cub clutch verification corrected my own premise.** I had assumed that
clutch content mentioning a lever does not apply to a Cub. Honda's own parts
catalogue `13K0GK01` — fetched and checked in the main session, not taken from a
report — names the internal actuator `LEVER COMP., CLUTCH`, part 22810-KPH-900,
inside the right crankcase cover. Excluding on the word "lever" would have
withheld content that applies. The catalogue also shows the Cub has **two**
clutches with disjoint parts lists: a centrifugal primary with no friction plates
at all, and a multiplate change clutch with four friction disks released by the
gear pedal. And `STARTING CLUTCH` turns out to be the starter motor sprag, a
third component — so my own earlier phrase "centrifugal start clutch" was using
Honda's name for something else.

One claim did not survive contact with the document. "Clutch free play is a
published Cub adjustment" is **not supported for the C125**: its owner's manual
`32K0GC20` returns zero hits for clutch lever, clutch cable and clutch adjust,
and all 18 of its freeplay references are about the brake pedal. The parts
catalogue proves a `BOLT, CLUTCH ADJUSTING` exists; no obtainable Honda document
publishes the procedure. Downgraded rather than shipped.

The operator tightened five things before the plan was committed, and the
sharpest was catching a per-category example I had written into my own
per-row rule: I had said a centrifugal-engagement row would declare
`{cvt, semi_auto_centrifugal}`, which is reasoning from the category rather than
from what the row says. A scooter clutch-bell wear limit does not hold for a
Cub's primary clutch. Most 254 rows will be `{cvt}` alone.

---

## 2026-09-21 — Build and v1.1

**The build is small; the sourcing was most of the work.** 43 lookup entries
across 8 marques, every document opened and read in this session rather than
accepted from a report. Each entry quotes the sentence it rests on.

**The evidence had to be tiered, and one tier was rejected.** Genuine, Kymco,
Piaggio, SYM and Yamaha print an explicit transmission type — "Transmission
Type — Continuously Variable (CVT)", "Automatic CVT", "automatic expandable
pulley variator, torque server, V-belt, automatic clutch", "Transmission type
V-belt automatic". Honda's European books print no type but name "the drive
belt **and weight rollers**", and weight rollers exist only in a variator, so
that is evidence rather than a guess. A bare "Drive Belt" row in a maintenance
schedule was **rejected**, because that is precisely the ambiguity Phase 254's
own row 4605 documents — three unrelated components share the name. That
single decision excluded fifteen budget-marque manuals.

**Honda's US books say nothing at all.** The 2025 Ruckus owner's manual has
**zero** occurrences of "belt" in 107 pages; the 2025 Metropolitan has none of
"drive belt" or "weight roller". Both are CVT machines. Neither can be
classified from its own owner's manual, so neither gets an entry and both lose
the layer. A document gap, not a knowledge gap — and not one this corpus is
allowed to close by inference.

**SYM turned out to be the proof the mechanism works.** One maker, three
machines, three different answers, all from that maker's own manuals: the
Symply is a CVT, the Symba is a Cub ("Clutch — Wet multi-plate type, auto
centrifugal clutch · Transmission — 4-speed gear change", which is the
mechanism definition of `semi_auto_centrifugal` in the maker's own words), and
the Wolf 150 is a motorcycle with a clutch lever. No marque-wide default could
produce that, which is the concrete argument for there being no make-default
at all.

**Two mutations survived the first run, and both were tests that looked like
they were checking something.** The alpha/numeric-splitting test asserted a
case that resolves the same way under both implementations, so it could not
tell them apart. And the backfill test was reading the *loader's* work: the
fixture database is built by loading seed files, which write `applicability`
on the way in, so the migration's `post_apply` hook never had to run. **The
piece that repairs the operator's live database was untested.** Both replaced,
both now caught — 24 of 24.

**A documented note came due.** `test_phase191b_serve_migrations.py` carries a
"NOTE FOR THE NEXT SCHEMA BUMP" explaining that its pin is spelled
`get_current_version(db_path) == N` and that grepping for `SCHEMA_VERSION`
misses it. It was written after the same pin was missed at 244M and caught only
by the full regression. This time the blast radius found it before the
regression did, which is the note doing its job.

One pin had to change shape rather than be bumped. Phase 244R's
`SCHEMA_VERSION == 62` asserted two things — that 244R's bump happened, and
that nothing had happened since — and only the first was ever its claim.
Relaxed to `>= 62` with the reason recorded inline.

**The cost is measured, not argued about.** Of the 53 model spellings the 254
rows reach, 40 resolve from a document and 13 do not, and those 13 lose the
layer. The withheld-rows counter attributes every withholding to its
provenance, so "unknown" (a gap a later phase closes) is distinguishable from
"ambiguous" (a machine that genuinely cannot be told from its sibling).

No live vehicle regresses: the operator's ten machines are all non-CVT and all
correctly lose rows they should never have had. The exposure is future
machines, which is why the mobile transmission field moved up to the phase
immediately after 255B.

**One more thing came out of testing the contract rather than reading it.**
"Rejected loudly" is easy to write into a plan. Exercising it showed that one
corrupt `applicability` value raises out of `_load_known_issues` — the
retrieval path for both `diagnose` and `code` — so **a single bad row stops
diagnosis for every machine.** The trade is kept, because dropping the row
silently would load a typo as *unscoped* and put it back in front of every Gold
Wing, which is the defect this phase exists to fix reintroduced by one
character. But it is a trade, so the error now names the offending row by id
and title, the behaviour is pinned by a test and two mutations, and it is filed
as F122 for the operator to revisit rather than left to be discovered.

**And the question that should have been asked first.** Late in the build, the
obvious question finally got asked: *which callers retrieve corpus rows for a
specific machine?* That is precisely the question Phase 254 never asked about
its own rows, and asking it here found **three doors, not one**. The diagnose
path was the one the plan covered. The video `/ask` endpoint hands twenty-five
retrieved rows straight to a vision model with **no composition at all** — an
MT07 and an XS650 were each getting two CVT rows there, and the Hondas missed
them only because their own rows filled the twenty-five first, which is ranking
luck rather than correctness. That one is fixed here, because it is the same
shape as the diagnose path, and `drop_inapplicable` is public rather than
private because of it.

`predict_failures` is the third and it **still leaks** — five of the 254 rows
sit behind an MT07's maintenance predictions, two behind a Gold Wing's. It is
deliberately not fixed: it is a scored fifty-prediction pipeline with its own
retrieval and its own drift bonuses, and changing it late, without a plan and
without a refuter, is exactly how Phase 254's defect shipped in the first
place. Filed as F123 with the numbers.

**The schema pins deserve their own note, because the phase's lesson repeated
itself at the very end.** Twelve pins had to be touched and it took five passes
to find them all. The subsystem-scoped blast radius found three. Running a
neighbouring file found a fourth. A grep found four more. A ninth was reachable
only because `gate12` runs `gate11` in a **subprocess**, so it never appeared in
the parent's own failure list. And the last three were found by re-running that
grep and **counting its hits instead of reading its first screenful** — the
first pass had been piped through `head`, and the truncated list was treated as
the whole set.

That last one is this phase's own subject, made by me, at the end of the phase
about it: a measurement that looks complete because nothing says it isn't.

**The regression's only failure was the orphan guard, and it was right three
times.** Phase 209B's integration-gap check — F9 subtype 2 — named three public
definitions this phase built and never wired. `scoped_rows` was deleted rather
than recorded: it had no caller *and* its docstring said "Used by the counter",
which was never true, and a helper describing a caller that does not exist is
not a gap worth writing down. `withheld_snapshot` and `reset_withheld` were
recorded as `test-infra`, with the concrete reason they cannot have an in-tree
caller today: the counters live in process memory and every CLI command is a
fresh process, so a stats command would print zeros every time.

That forced D6 to be stated more precisely than the plan stated it. The
withheld-rows cost is visible **in the logs**; the **aggregate is surfaced
nowhere a user can reach**. Every withheld-rows number in the v1.1 results was
obtained by calling the snapshot from a script — which is precisely what the
guard was pointing at, and the same shape of gap as the phase's own subject.

**And a second gate behind the first.** Fixing the orphan guard tripped Phase
244U's running-count pin — `len(ORPHANS) == 96` became 98 — which exists so the
allowlist cannot grow quietly. Two entries added, one orphan deleted rather
than listed, and the pin's own docstring now records which was which and why.
The pair of gates is the right shape: 209B asks *what* is unreached, 244U asks
*how many*, and neither alone would have made me say out loud that this phase
shipped two things nothing calls.

**Closed green on the third full regression: 7,882 passed, 0 failed, 0 skipped,
25:43.** The first found the orphan guard, the second found the running-count
pin behind it, and the third was clean. Both of the first two failures were
guards doing their job on code this phase wrote, which is the outcome to want
from a phase that exists because Phase 254's guards had nothing to say about
where its rows went.
