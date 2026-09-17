# Phase 244S — The retrieval fixes reach the commands people use

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-17

---

## Goal

Phases 244C–244I built typo-tolerant vehicle resolution, junction-table
retrieval and specificity tiering, and proved each against the corpus. **All
of it reaches exactly one route** — the video-question endpoint. `motodiag
diagnose` and `motodiag kb list`, the two surfaces a technician actually
uses, still retrieve with `make LIKE '%X%'`.

Measured on the live corpus, that costs three things:

1. **A typo empties the corpus, silently.** `diagnose` takes make and model
   from the garage row — free text somebody typed. A bike entered as "Homda"
   returns **0 rows**, `build_knowledge_context([])` returns `""`
   (`engine/prompts.py:65-66`), and the model diagnoses with no corpus at all
   while nothing on screen says so. The resolver returns **143** for the same
   input. This is verbatim the failure 244C exists to end, still shipping on
   the product's primary command.
2. **The prompt gets an entry written to exclude that machine.** For a 2022
   KTM 1290 Super Adventure, the LIKE path returns issue 1277, whose model
   column reads *"390 Adventure, 790 Adventure, 890 Adventure — as distinct
   from 1290 Super Adventure"*. `LIKE '%1290 Super Adventure%'` matches the
   exclusion clause. 244I's junction indexes it as 390/790/890 only, and the
   resolver ranks it `make_other_model`.
3. **Specific entries sit behind generic ones.** `kb list --make
   harley-davidson` returns 143 rows, of which 14 are LiveWire, ordered by
   severity with no idea which are about the bike in front of you.

## Step 0 — findings

Run as two agents (design + adversarial check) inside the 244R Step 0 sweep.
**The checker broke the first design**, and its corrections are the plan
below. Every number here was independently reproduced by both agents.

**S0-1. The two paths return different row shapes.** `search_known_issues`
returns `_row_to_dict(row)` (`issues_repo.py:178`), which JSON-decodes
`symptoms`, `causes`, `dtc_codes` and `parts_needed` into lists
(`:283-294`). `known_issues_for_vehicle` returns bare rows plus a
`match_tier` key (`vehicle_resolver.py:401`). **Swapping one for the other
would hand callers undecoded strings where they expect lists.** This must be
fixed first, as its own step.

**S0-2. It is already broken on the one route that uses the resolver.** The
`/ask` endpoint has been handing undecoded rows to `_format_known_issues`
since 244E, and got away with it only because that formatter reads no list
field. Fixing the contract repairs a latent bug rather than creating one.

**S0-3. The signature cannot stay.** `_load_known_issues` is typed
`-> list[dict]`; the resolver returns `(VehicleIdentity, rows)`. There is no
version of this change that reaches the resolver *and* surfaces the
correction while keeping the old return type. Three call sites change
(`cli/diagnose.py:362`, `:433`, `cli/code.py:159-161`), feeding four
commands.

**S0-4. Without printing the correction, the typo case is not fixed — it is
re-hidden.** If "Homda" silently resolves to Honda and nothing says so, the
technician never learns their garage entry is wrong, and a CB500 → CB500F
substitution becomes an unreportable mislabel.

**S0-5. Today's retrieval is unbounded, so "preserve current behaviour" is
not available.** Real vehicles return 45–95 rows, 40–60 KB of prompt per
call, ×3 rounds in the interactive flow. The resolver defaults to 25. A limit
has to be chosen deliberately, and it is a cost decision now that Phase 209D
records what a call costs.

**S0-6. `kb list --model` is documented as a substring filter**
(`cli/kb.py:403`), and 244C's own Risks section says the resolver "stays"
narrow rather than becoming a global normalisation layer. Part of this
divergence is deliberate. Measured: resolving names into the surviving LIKE
filter buys 0→142 on the make side, ~nothing on the model side, and
**narrows** `--make BMW --model K1600` from 5 to 3. The half-measure is worse
than either end.

## Scope

1. **One row shape, proven identical.** Promote `_row_to_dict` to a public
   `row_to_issue_dict` in `issues_repo.py`; call it from both retrieval
   paths, applied in `vehicle_resolver.py` before `match_tier` is attached.
   A test asserts `isinstance(row["symptoms"], list)` for rows from **both**
   functions, because from here on two paths feed one prompt builder.
2. **`diagnose` and `code` retrieve through the resolver.**
   `_load_known_issues` returns `(identity, rows)`; all three call sites
   updated. The year filter moves into Python (the resolver has no `year`
   parameter), applied *before* the cap so filtering cannot starve the
   result.
3. **The correction is printed.** All four commands show
   `identity.corrections()` and `identity.suggestions()` — "Homda → Honda",
   "CB500 → CB500F" — so a resolution is visible rather than silent. This is
   what makes S0-4 a fix instead of a deeper hiding place.
4. **A named limit, with its cost recorded.** Fetch generously (200) so the
   year filter has material, cap at **12** after filtering — matching what
   the vision formatter already renders
   (`media/vision_analysis_pipeline.py:101`). Before/after prompt sizes go in
   the phase doc, so the 209D cap is tuned against measured numbers.
5. **`kb list` resolves the make only.** `--model` stays a substring browse
   filter, and the doc records that 244E's tiering deliberately does not
   apply to it — a decision that is currently written down nowhere. This
   captures the entire measured win with no narrowing regression.

## Non-goals

- **Full delegation of `kb list` to the resolver** (tiering, year and
  severity passthrough, rewritten help). That is the other end of S0-6 and a
  phase of its own if the browse surface should become a ranked one.
- **`core/search.py` and `advanced/predictor.py`**, the other two LIKE
  callers. Out of scope until the shape contract has shipped and settled.
- **The API's `/v1/kb/issues` endpoint.** Same reasoning, plus a contract
  Gate 11 pins.
- **244T (safety wiring) and 244U (the gate's blind spot)**, which remain as
  scoped by the 244R audit.

## Verification Checklist

- [ ] Both retrieval functions return rows of the same shape, proven by a test that reads a list field from each
- [ ] `/ask`'s latent undecoded-row bug is gone as a side effect, with a test
- [ ] `diagnose quick` on a typo'd make ("Homda") retrieves the corpus instead of nothing
- [ ] The correction is printed, so the technician learns the garage entry is wrong
- [ ] A 2022 KTM 1290 Super Adventure no longer receives the entry that excludes it
- [ ] Rows arrive tiered, most specific first
- [ ] The year filter still applies, and is applied before the cap
- [ ] The prompt is bounded at 12 rows; before/after sizes recorded
- [ ] `kb list --make livewire` surfaces LiveWire entries rather than burying them
- [ ] `kb list --model` still behaves as a substring filter, with the decision recorded
- [ ] `motodiag code` and the interactive `diagnose start` flow both still work
- [ ] Mutations: revert each call site; drop the shape conversion; hide the correction; drop the year filter; apply the cap before the filter — each caught
- [ ] 209B gate passes; f9 lint clean; full regression green
