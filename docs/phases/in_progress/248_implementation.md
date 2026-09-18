# Phase 248 — Regenerative braking diagnostics: the generic layer, anchored per make

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-18

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

## Verification Checklist

- [ ] Every row names a manufacturer document for every make it names (test)
- [ ] No numeric setting or threshold without a label (test)
- [ ] `kb search regen` / `"brake light"` / `coast` each return a 248 row with its label (test)
- [ ] `dtc_codes` seed untouched; `dtc_category_meta` untouched
- [ ] 246's and 247's tests still pass
- [ ] Mutations: strip a document name; add an unlabelled percentage; paste a community statement into a manual row; delete a concept row; strip a campaign number
- [ ] Full regression green
