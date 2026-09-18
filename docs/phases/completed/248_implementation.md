# Phase 248 — Regenerative braking diagnostics: the generic layer, anchored per make

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-18

---

## Goal

Row 248: "Regenerative braking diagnostics — regen ratios, coast-down
behavior, brake light trigger on regen, single-pedal mode." The third
content row under the rule 246 set and 247 kept: **every entry is written
as what the system does and how each make shows it, anchored to a
manufacturer document for every make named, or not written**; every
number carries its label into every display surface; one row carries one
label; a regulator record is its own row; a community source names its
site and page date. Regen is the one electric subsystem the rider
configures, so this row's centre of gravity is what each make lets the
rider set, what the machine does off throttle and approaching a stop,
whether the brake lamp answers regen, and whether any make offers a
one-pedal stop — each as published, or as an absence.

## Step 0 — findings

**S0-1. What exists.** `dtc_category_meta` has carried `regen`
("Regenerative braking system faults", severity high) since migration
004; it is empty, like the five other EV categories 246 and 247 audited.
No corpus row has a regen symptom. Thirteen rows mention regen, coasting,
a brake light or one-pedal; the electric ones are 247's identity row (Zero
specifies its controllers "with regenerative deceleration") and 242's Zero
brake-campaigns row, which is about a front-brake switch that fails wet so
the brake light does not come on **when the front brake is applied** — not
about regen — and it belongs to 242 as a make-specific failure pattern.
**Nothing generic about regen exists; nothing anywhere states a regen
ratio, a coast-down behaviour, a brake-lamp rule on regen, or a one-pedal
capability for any make.**

**S0-2. Sources, by make.** 246 and 247 fetched and verified the four
owner's manuals (Zero 88-09445-01, 8811984-AF, 88-09447-01; Energica
ENF003100 Rev. 02; H-D 94000703 and the 94001019 and 94001315 pages on the
Service Information Portal), Zero's 2020 service manual on an archived
dealer site, and the makers' web pages; none was read for regen. Of 247's
88 verified claims, seven touch regen ground only as a specification
phrase or a ride-mode mention. The regen content is expected in the
ride-mode sections of every manual (Zero's Custom mode and its adjustable
parameters; Energica's power profiles and regen levels; LiveWire's
Sport/Road/Range/Rain and Custom modes with a regen level), in the makers'
statements about the brake lamp during regen, in any regen limit tied to a
full or cold pack, and in the regulator record (a brake-lamp-on-regen
campaign would sit there). Community sources: zeromanual.com behind an
expired certificate, electricmotorcycleforum.com down, the LiveWire forums
behind a JavaScript challenge — as 247 found; zerologs.bike reachable.

**S0-3. The design question.** "Regen ratios" and "coast-down behaviour"
are the rider-facing settings and behaviours each maker documents in its
own words and units — percentages, named levels, per-mode defaults — and
they differ by make and platform. "Brake light trigger on regen" and
"single-pedal mode" are yes-or-no questions a manual answers or does not;
where it does not, the absence is the content, stated for the documents
read in full. The row is done in 246's shape: what regen does, what the
rider can set, what the machine does off throttle and at a stop, when
regen is reduced, how a regen fault shows — per make, anchored, or not
written.

**S0-4. Substrate — none.** The `regen` category exists; the question of
seeding regen fault codes is F90's shape and stays there. Any regen code a
manual publishes rides on the row's `dtc_codes` list, named in its text,
reachable through `kb by-code` (247's verified path).

**S0-5. Cadence.** As 247 ran it: three per-make sweeps through five
lenses (manufacturer document, regulator record, owner community, tooling,
platform generation), then **one refuter per document that fetches the
page itself**, then a critic; through the Agent tool (no workflow opt-in
for this row); the wording and number rules of 246 and 247 unchanged.

**S0-6. Boundaries.** A regen behaviour caused by the pack ("regen is
reduced when fully charged") is 248's; the pack's own limits are 246's.
The controller is 247's. Temperature bands are 249's; a regen limit tied
to temperature is 248's as behaviour, without the band. Cruise control and
ABS are named only where a maker ties them to regen.

## Decisions carried from 246 and 247

1. Fetch-and-verify research; the refuter fetches every page.
2. Community sources are `forum`, dated; official documents cited directly.
3. A number ships only with its label wherever displayed; one row, one
   label; regulation rows name their campaign number.
4. `regen` category: exists, empty; no seeding here (F90).

## Scope

1. **Up to five generic rows** in `known_issues_regen.json`, each anchored
   per make or not written: *settings* (regen ratios and levels, ranges,
   per-mode defaults, where set); *coast-down* (off-throttle and neutral
   regen, behaviour approaching a stop); *brake light* (whether and when
   regen lights the brake lamp); *single-pedal* (capability or absence);
   *limits and faults* (when regen is reduced or disabled, and how a regen
   fault shows). Regulator records and community statements on their own
   rows if any survive. `make` list-valued; regen codes in `dtc_codes`.
2. **Tests** in 247's shape on the new file, with 248's concepts in
   titles, controller-and-regen units in the number rule (percent, levels,
   speeds), the regulation and forum rules, the boundary test (no
   246/247 concept in a title; no temperature band table).
3. **Research record** in this doc.
4. README, quickstart, install guide, launch checklist: count bump.

## Non-goals

- No pack limits (246), no controller content (247), no temperature bands
  (249), no brake-hardware failure patterns (242–244 own those).
- No regen percentages, levels or speed thresholds from memory. None.
- No schema change; no `dtc_codes` seeding; no new commands.

## Results (v1.1)

**Built in 247's shape: seven rows, six service-manual concepts and one
dated community row, and no regulation row.** No recall campaign for any
of the three makes concerns regen, and 247's pattern gives regulator
records a row only when there is a campaign; the regulator record is
carried as sentences instead. The row's four bullets resolve three ways:
regen ratios and coast-down behaviour are published per make, in the
makers' own words; the brake lamp on regen is stated by one manual (the
LiveWire S2's) and left unstated by every other; a one-pedal stop is
offered by nobody, and the rows say so document by document.

### The content (`known_issues_regen.json`, seven rows)

| Concept | Row | Source | Anchors |
|---|---|---|---|
| Settings | *What the rider can set for regen on each make — named modes and levels in the manuals, percentages only on LiveWire's web pages* | service-manual | Zero 8811984-AF §3.13–3.16, 88-09445-01 §3.13–3.15, 88-09447-01 §3.20, firmware notes, technology page; Energica ENF003100 p.45, archived and live energicamotor.com pages; H-D 94000703 Table 30 and pp.97–98, 94001019 Widgets, 94001315 Ride Modes; livewire.com S2 and ONE pages |
| Coast-down | *Off-throttle regen and coasting on each make — a drag on a closed throttle, a coasting point just off it, and no published behaviour approaching a stop* | service-manual | Zero 8811984-AF §3.9, 88-09445-01 §3.9, 88-09447-01 §3.18; Energica pp.32, 45; H-D 94001315 Roll-Forward Regen, 94000703 pp.76–77; livewire.com roll-forward article |
| Brake light | *Does regen light the brake lamp — yes above an unpublished threshold on the LiveWire S2, and unstated in every other manual read* | service-manual | H-D 94001315 Roll-Forward Regen note item 1, livewire.com articles; 94000703 and 94001019 (silent); Zero 8811984-AF §3.7/§3.9, 88-09445-01, 2020 service manual Splice 37; Energica pp.74, 79, 108; NHTSA 20V704 and 12V307 named as brake-switch campaigns |
| Single-pedal | *No electric motorcycle maker offers a one-pedal stop — every manual read ends a stop on the friction brakes* | service-manual | Zero 8811984-AF and 88-09445-01 §3.9; Energica p.89; H-D 94001315 Roll-Forward Regen, 94000703 (read in full) |
| Limits and faults | *When regen is limited or cut on each make — a full pack, a cold pack, rear-wheel slip — and no fault code named for regen* | service-manual | Zero 8811984-AF §4.21/§7.5–7.7, 88-09445-01 §4.23, 88-09447-01 codes and flashes, firmware notes; Energica pp.29, 45, 74, 75, 78–83, archived technology page; H-D 94001315 note item 2, Traction Control System page, 94000703 pp.110, 112; livewire.com DSCS text |
| Tooling | *Where regen is set and read on each make — the dash, the app, and the dealer tool that loads the regen features* | service-manual | Zero 8811984-AF §3.21/§4.3, 88-09445-01 pp.3.20–3.21, 2020 service manual road test, technology page; Energica pp.26, 35, 37, 44–45, 48; H-D 94001315 Roll-Forward Regen, DT II notes MC-11026163, 94000703 Figure 35 |
| Full pack (community) | *What a Zero does with regen on a full pack, per the community log-analyser — a pulsing engagement that is protection, not a fault* | forum | zerologs.bike 'Reading Your Zero Logs' (Last updated: August 8, 2026) and 'Log Error Catalog' (Last updated: July 30, 2026) |

Every row is written as *what regen does* and *how each make shows it*;
every service-manual row names its documents by code and says which were
read from mirror copies; web pages are named as web pages with their page
or capture date, or "undated" where the page shows none; every name and
number is the document's own, re-read on the page by a refuter; nothing
is `model-generated`. The six concept rows carry `make` = `Zero,
Harley-Davidson, LiveWire, Energica` and resolve to all four marques
(tested). No codes ride on `dtc_codes`: no maker publishes a regen code,
and the lamp-circuit codes the brake-light row names (Zero 20 and 21,
Energica B1002 and B1003) are named in its text as lamp codes, not
listed as regen codes. `dtc_category_meta` and the `dtc_codes` seed are
untouched; the `regen` category stays empty (F90).

**The one number rule this row adds.** No owner's manual of the three
makes prints a regen percentage; the only percentages in the research are
LiveWire's S2 preset figures (Sport 65%, Road 35%, Range 80%, Rain 20%,
Custom 0-100%) on its product web pages, which sit in the page data
behind the ride-mode tabs. A new test holds every percentage in a
manual- or regulation-labelled row to a sentence that names livewire.com,
so a regen figure can never be presented as a manual's.

### A bug in the number rule, found and fixed

Mutation 2 (a `model-generated` row carrying a 40% regen figure) survived
its first run. The number rule's trailing `\b` can never match after a
`%` sign, because both the sign and what follows it are non-word
characters, so **percentages were invisible to the rule in 246's and
247's content tests too** — their mutations had used "100 mV" and
"600 A", which the rule did see. The guard is now a lookahead in all
three files (`test_phase246_bms_content.py`,
`test_phase247_inverter_content.py`, `test_phase248_regen_content.py`),
and all three mutation sets pass again (246 6/6, 247 8/8, 248 8/8).
Nothing shipped in 246 or 247 was mislabelled: every percentage in those
rows is service-manual or forum, both allowed.

### Deviations

1. **Seven rows, not five**: tooling has its own row as in 247, and the
   community statements sit on their own dated row.
2. **No regulation row.** No make has a regen campaign; the regulator
   record is a sentence set, and Zero's brake-switch campaigns 20V704 and
   12V307 are named as cross-references to the Zero brake-campaigns entry.
3. **Refuter-found material not yet written, filed as F92**: an NHTSA
   owner complaint (ODI 10861302, a 2013 Zero S whose brake light stays
   off under maximum regen); the 20V704 Part 573 sentence that model year
   2021 and later SR/F and SR/S add a parallel brake-lamp signal; the
   hdlivewireforum.com thread on a 2020 LiveWire's brake lamp flickering
   on light regen; an archived 2018 electricmotorcycleforum.com post on
   the brake light flashing under regen (the thread compares an Energica
   with a Zero, so the make must be confirmed); and sixteen more
   Harley-Davidson communications that mention regen. None has a verbatim
   quote in a refuter file yet, and the rule is no quote, no row.
4. **Kills**: a firmware note about ride-mode errors that names top speed
   and power, not regen; two marketing sentences (SR/F and X Line pages);
   an NHTSA complaint that never mentions regen; a FAQ's silence; the
   Energica ABS on/off procedure; a reading of Energica's "electronic
   brake" as regen that its page never makes; a web-page rendering
   artefact; a launch release's silence; a first-person LiveWire blog
   ("Personally though, about 80% Regen suits my riding style") that
   would have extended the S2's brake-lamp statement to the 2020 bike and
   the ONE, whose manuals are silent.

### Verification

- 64 tests in `test_phase248_regen_content.py`; 517 across the 18 suites
  run before the regression (the three content files, 246's label-surface
  file, 244D, 244F, 244I, 208, 78, 241–244, 244T, 03, 244S, 244E, 240).
- **8/8 mutations killed**, bytecode cleared and `-B`: strip every
  document name · add an unlabelled 40% setting as `model-generated` ·
  paste a community statement into a manual row · drop the page date from
  the forum row · delete the brake-light row · paste a temperature band
  table · attribute a regen percentage to a manual · list a code the
  text never names. The second survived its first run (above).
- 244G raw-source scan of the new test file: clean. `ruff` clean.
- No schema change; `dtc_codes` seed and `dtc_category_meta` untouched.
- Full regression **7,155 passed, 0 failed, 27:31**.

### Research record

**Cadence.** Three per-make sweeps (five lenses each) produced 90 claims
citing 40 URLs; **20 refuter groups fetched every page themselves**
(40/40) and judged 90/90 claims; a critic read the survivors against the
refuters' verified quotes and ruled on the material the refuters found.
Tally: 50 survive clean, 36 downgraded, 4 refuted; the critic killed 12
more and folded 5 regulator absences into one sentence. After class
corrections: 52 manual claims, 27 manufacturer web or firmware pages, 6
regulation, 5 forum. **The pass was real, and this time it cut the other
way**: all four refutations were absence claims the refuters overturned
by finding what the sweeps had missed — 23 Zero campaigns where the sweep
counted 13 (it skipped model years before 2014), an owner complaint
naming the brake light under regen, a LiveWire forum thread a plain
fetch could read after all, and an archived Energica owner post.

**Documents.** Zero: 2025 owner's manual 8811984-AF (12 claims), 2021
SR/F owner's manual 88-09445-01 (1, plus eight cross-manual checks), 2021
S/SR/DS/DSR owner's manual 88-09447-01 (3), 2020 service manual (2),
firmware release notes (3), four web pages, NHTSA records and bulletins
(3), zerologs.bike (2). Energica: 2018 Eva owner's manual ENF003100 Rev.
02 (16), four live energicamotor.com pages (5), five archived captures
(5), NHTSA (2), electricmotorcycleforum.com (2). LiveWire: 2025 S2 manual
94001315 (9), 2023 LiveWire ONE manual 94001019 (3), 2020 manual 94000703
(6), livewire.com model pages and articles (10), NHTSA (1), forum (1).

**Grid.** Settings, coast-down, limits and tooling have a manual anchor
for every make. Empty cells, carried as absences: the brake lamp on
regen for Zero, Energica, the 2020 LiveWire and the ONE; a one-pedal stop
for all three; a cold-battery regen limit for Zero, Energica, the 2020
LiveWire and the ONE; a regen fault code for every make; a dealer regen
test beyond Zero's road-test checklist.

**Not written** (numbers): Zero's ECO and RAIN speed caps; campaign and
complaint counts; ODI dates; Energica's range-test figure, menu-exit
speed, battery band and P1002; LiveWire's "80% Regen" blog preference,
ABS thresholds, CMS timestamps, the date of MC-11026163 (header not yet
read) and the forum thread's figures; the S2 Power and Throttle
percentages (not regen).

## Verification Checklist

- [x] Every row names a manufacturer document for every make it names (test)
- [x] No numeric setting or threshold without a label (test; the percent bug fixed in all three content tests)
- [x] `kb search regen` / `"brake light"` / `coast` each return a 248 row with its label (test)
- [x] `dtc_codes` seed untouched; `dtc_category_meta` untouched
- [x] 246's and 247's tests still pass (and their mutation sets, re-run)
- [x] Mutations: 8/8
- [x] Full regression green — **7,155 passed, 0 failed, 27:31**
