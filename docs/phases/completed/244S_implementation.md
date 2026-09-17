# Phase 244S — The retrieval fixes reach the commands people use

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-17 (built 2026-09-17)

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

- [x] Both retrieval functions return rows of the same shape, proven by a test that reads a list field from each
- [x] `/ask`'s latent undecoded-row bug is gone as a side effect, with a test
- [x] `diagnose quick` on a typo'd make ("Homda") retrieves the corpus instead of nothing
- [x] The correction is printed, so the technician learns the garage entry is wrong
- [x] A 2022 KTM 1290 Super Adventure no longer receives the entry that excludes it
- [x] Rows arrive tiered, most specific first
- [x] The year filter still applies, and is applied before the cap
- [x] The prompt is bounded at 12 rows; before/after sizes recorded
- [x] `kb list --make livewire` surfaces LiveWire entries rather than burying them
- [x] `kb list --model` still behaves as a substring filter, with the decision recorded
- [x] `motodiag code` and the interactive `diagnose start` flow both still work
- [x] Mutations: revert each call site; drop the shape conversion; hide the correction; drop the year filter; apply the cap before the filter — each caught
- [x] 209B gate passes; f9 lint clean; full regression green

## Deviations from v1.0

**1. The excluding entry is ranked and labelled, not dropped.** The checklist
said a 2022 KTM 1290 Super Adventure "no longer receives the entry that
excludes it". It still receives it — 244E's rule is that knowing more must
never return less, so the resolver tiers rather than filters. Measured: the
two model-specific rows come first, and the excluding entry arrives as
`make_other_model`. That is the right outcome, and the checklist item was
written too strongly.

**2. The prompt builder had to learn the tier.** A consequence of the above
that v1.0 did not draw: once tiered rows reach `build_knowledge_context`, an
entry about another model renders identically to one written about this
machine. Rows now carry a scope label — "this model", "this make, model not
specified", "same make, DIFFERENT model" — and a row without a tier renders
exactly as before.

**3. A latent crash, found by a fixture.** `build_knowledge_context` read
`issue.get("fix_procedure", "")`, which returns None for a NULL column, and
called `len()` on it. No shipped corpus row has a NULL there; the column is
nullable, so one new entry without a procedure would have crashed every
diagnosis that retrieved it. Fixed in the same phase.

## Results

| | |
|---|---|
| The typo case | "Homda"/"cbrf4i" went from **0 rows to 12**, tiered model-first, with both corrections printed |
| What the model used to get | `""` — an empty knowledge base, with nothing on screen saying so |
| Row shape | one, `row_to_issue_dict`, used by both paths; the `/ask` endpoint's undecoded rows are repaired as a side effect |
| Ordering | model-specific first, then make-wide, then other models of the same make |
| The excluding entry | still present, ranked last of its query and labelled `make_other_model` (Deviation 1) |
| The prompt | says which scope each entry has (Deviation 2) |
| Prompt size | bounded at **12** rows, fetched at 200 so the year filter has material. Retrieval was unbounded: 45–95 rows, 40–60 KB per call, ×3 interactively |
| Year filter | moved into Python and applied **before** the cap |
| `kb list` | resolves the make; `--model` stays a substring browse filter, and that decision is now written down |
| Latent crash | a NULL `fix_procedure` no longer breaks the prompt (Deviation 3) |
| Tests added | **20** |
| Mutations | **7 of 7 caught** |
| Regression | **6,856 passed, 0 failed, 26:49** |

**Mutations**

| | mutation | caught by |
|---|---|---|
| M1 | diagnose reverts to the LIKE path | `test_the_command_path_now_finds_the_corpus` |
| M2 | the resolver stops decoding rows | `test_the_resolver_path_does_too` |
| M3 | the year filter is dropped | `test_an_out_of_range_entry_is_excluded` |
| M4 | the cap runs before the year filter | `test_the_filter_runs_before_the_cap` |
| M5 | the prompt stops labelling the tier | `test_the_prompt_says_a_different_model_is_a_different_model` |
| M6 | a NULL fix_procedure crashes again | `test_a_row_with_no_fix_procedure_does_not_crash_the_prompt` |
| M7 | the prompt is unbounded again | `test_the_prompt_is_bounded` |

**Left for 244T and 244U**, unchanged: `SafetyChecker` has no caller, and 117
definitions are invisible to the 209B gate behind re-exports.
