# Phase 257 — The orchestrator and `/source-transmission`

**Version:** 1.2 | **Tier:** Standard | **Date:** 2026-09-23 (close-out)

History: 1.0 the plan (2026-09-22); 1.1 the during-build amendment below
(source stages on Subconscious); **1.2 the close-out** — every section
annotated *As built*, the checklist ticked with its evidence, and
Deviations and Results added. (The close-out would ordinarily be v1.1;
that number was taken by the amendment.)

Step 0: [`257_step0.md`](257_step0.md) (measurements, proofs). This plan is
built on it and does not repeat it.

## Goal

A headless orchestrator that runs a written procedure — census → acquire →
extract → classify → refute → write — against the transmission lookup, one
make per batch, inside a sandbox it cannot write out of. The operator sees
per-make batch summaries and stops, nothing else.

Its first real job is coverage for the ~600 spellings that resolve
`unknown`. **This phase ships the machine and its first tranche, not the
coverage.** Later makes are batches of the same tool, not new phases.

*As built:* the machine shipped, and its batches ran well past tranche 1 —
nine makes batched, **71 lookup entries** written (census 605 → 528).
Coverage stopped where acquisition did; the rest is F143.

## Why a procedure and not a model's judgement

Every loose number in 255B–257 Step 0 came from counting what a search
matched instead of what the matched thing was (F139). Each SOP step exists
because a specific trap was hit; the orchestrator enforces the steps, so a
run cannot skip one because it is inconvenient.

## Decisions

**D1. Where it runs.** Every model stage runs as
`claude -p --model claude-opus-5-5` (operator decision: Claude Code
throughout, no GLM) inside `sandbox-exec`, in a **fresh clone** — not a
worktree, which cannot be bounded (S0-3). The database is a **snapshot**
copied into the run's tmp. The token arrives by environment from
`~/.config/motodiag/anthropic.env`; the keychain is denied.

**D2. The boundary is a test.** The planted-attempt probe from S0-3 becomes
`tests/test_phase257_sandbox_boundary.py`: it runs `sandbox-exec` with the
shipped profile over a probe script (no model, no network cost) and asserts
every planted write, push and credential read fails while the in-clone
controls succeed. A profile edit that opens a hole fails the suite.

**D3. Guards in the orchestrator, each tested.** It refuses to start if:
`ANTHROPIC_BASE_URL` is set to anything but Anthropic; the token begins with
anything but `sk-ant-`; it would pass `--bare` (skips hooks); a call lacks
an explicit `--model`. And it always passes `--max-budget-usd`.

**D4. The procedure** — one skill folder, `.claude/skills/source-transmission/`,
with the 255D shape: `SKILL.md`, a dated `CHANGELOG.md`, scripts, and a
hand-written known-bad fixture its check must fail on.

| step | who | rule, and the trap it answers |
|---|---|---|
| census | `census.py`, no model | every `unknown` pair by make, counted, no sampling — the figures of record |
| acquire | model, sandboxed | on-disk library first, then maker portals and spec pages; **blocked / not-found are recorded outcomes**, never guessed past |
| extract | model, sandboxed | the **maker's own word** (V-matic, DCT, Y-AMT, centrifugal); model codes become aliases; **no spelling-match counting** |
| classify | model, sandboxed | by mechanism; ambiguous variants → candidate set; no evidence → **NULL** |
| reject | `entry_check.py` | recycled headers, marketing copy, garbled OCR, single table cells, missing quote or page |
| refute | Opus, in the repo | `/refute` opens every cited page; **page images where OCR is weak** |
| write | Opus, in the repo | one lookup entry per model with its citation; **one make per commit**, tests, before/after table |

**D5. Stops.** A batch stops and alerts (macOS notification, confirmed in
S0-5; non-zero exit; a summary file) on: a refute verdict disagreeing with
extract/classify; a blocked rate above **50%** of a make's spellings; any
red test. The first two are tunable after the first real batch; red is not.

**D6. Tranche 1 — the six spellings with a maker document on disk.**

| spelling | today | action | evidence |
|---|---|---|---|
| SYM Wolf 150 | `manual` | none | already sourced |
| SYM Wolf Classic 150 | unknown | alias on the Wolf 150 entry | Wolf 150 owner's manual, spec page headed *"Model Classic 150"* |
| SYM Wolf CR300i | unknown | new entry | Wolf CR300i owner's manual: *"squeeze the clutch lever fully, push shift pedal down to engage the 1st gear"* |
| Kymco K-Pipe | unknown | new entry | K-Pipe 125 owner's manual: *"Transmission … 4-speed, foot shift"* |
| Honda Grom, Grom 125 | unknown | new entry, both aliases | GROM125 service manual — **page images read in refute**; the OCR is not evidence |

**D7. Acquisition is measured, not built out.** 0 of 10 makes yield the
maker's word in one fetch (S0-2). This phase records, per make, which
method works — a document endpoint, a browser, or blocked — with one real
document fetched as proof where it works. That table is the input to the
first real batch.

**D8. The `{manual}` rule stays.** Tranche 1 moves five spellings out of
531 unknown machines; nowhere near enough to lift Phase 255's A1. F140 (the
rule is enforced on seed JSON only) is untouched here.

**D9. Numbering.** This phase is 257 by operator decision. The ROADMAP row
that held 257 (*Small-engine carb service*) moves to **353**, the next free
number, unchanged.

*As built, per decision:* D1 — the model stages run sandboxed in a fresh
clone as planned; the route changed twice (v1.1: Subconscious; then the
operator's fallback, `claude-opus-5-5@medium`, while Subconscious was
suspended), and every entry records its route in a `source_route` field.
D2, D3 — as planned, each a test. D4 — the procedure grew three no-model
steps the table does not show: `candidates.py` (excerpts, so the source
stage is one turn with no tools), `acquire.py` (maker documents enter the
library only through the script, with provenance, E11) and the dry run;
entry_check grew from its classes to E1–E12. D5 — stops as planned plus
token ceilings and refute's kill rate; a single finding's failure is
withheld, not a stop (operator). D6 — tranche 1 written as planned; the
Grom was carried by Honda's spec pages, not page images (a better source
came first). D7 — measured per make, then built into `acquire.ROUTES`.
D8 — unchanged: the `{manual}` rule stays; F140 untouched. D9 — done.

## Non-goals

Lifting A1; coverage beyond tranche 1; the mobile per-vehicle transmission
field (the phase after this one); GLM or any second provider; any
scheduling or daemon — the orchestrator is run by hand, one batch at a
time.

*As built:* "coverage beyond tranche 1" and "GLM" were both crossed, each
by operator decision (Deviations). A1 was not lifted; the mobile field was
not touched; no scheduling was added.

## Verification checklist

- [x] `test_phase257_sandbox_boundary.py` — every planted attempt fails,
      controls pass; break-it: loosen the profile and it fails (build slice 1)
- [x] guard tests for D3, each with a planted violation (build slice 1)
- [x] `entry_check.py` fails its known-bad fixture per rejection class
      (E1–E12, `test_phase257_source_checks.py`)
- [x] census reproduces **605** unknown pairs on the live snapshot (build
      slice 2)
- [x] tranche 1: five spellings resolve `model-sourced` / `manual`; each
      entry quotes the maker and names the page (605 → 600)
- [x] Grom refuted — **from Honda's spec pages, digital text, not page
      images**: the batch found a better source than the OCR (Deviations)
- [x] one end-to-end orchestrator run on tranche 1 with its batch summary
      (`Honda_20260922_233404` and the SYM and Kymco runs)
- [x] D7 table: all 21 census makes, 43 URLs, method per make, one real
      fetch each (`~/.cache/motodiag/d7/20260923_002937/`)
- [ ] full regression with hash and count; floor raised before it

## Risks

- **The sandbox rules are macOS-specific and `sandbox-exec` is deprecated.**
  The boundary test is what notices if a macOS update changes behaviour.
- **A model can report success it did not have** (the planted run reported
  honestly, but that is one run). Every outcome the orchestrator acts on is
  re-checked by a script or by refute, never taken from the model's text.
- **Cost.** ~$0.05 floor per call, ~$0.13 for an eight-step run. Budget
  capped per call.

*As built:* the sandbox held; the boundary test runs every suite. A model
did report success it did not have, more than once — a quote de-hyphenated
across a line break, a miscitation in Kawasaki's first batch, a finding
omitting its citation — and each was caught by a script or refute, never
by the model. Cost was the risk that bit: an agent-loop source stage
measured 7.66M tokens for one spelling, which forced the one-turn,
no-tools redesign and per-stage token ceilings.

---

# v1.1 amendment (2026-09-22, during build) — the source stages run through Subconscious

**D1 as written was wrong about the operator's intent.** "Just use Claude
Code" meant *drive Claude Code through Subconscious*, not *drop GLM* — the
orchestrator exists to spend the long, context-heavy source stages on
Subconscious's gateway (GLM-5.3 Marathon, 3M-token context, managed
compaction) and save Opus context. Corrected:

| stages | route | how | credential |
|---|---|---|---|
| acquire, extract, classify | Subconscious, `subconscious/glm-5.3-marathon` | `subc claude --model … -- -p …`, sandboxed | held by `subc login`; the orchestrator never reads it |
| refute | Anthropic, `claude-opus-5-5` | `claude -p`, sandboxed, budget-capped | `CLAUDE_CODE_OAUTH_TOKEN` from `anthropic.env`, by environment |
| write | Opus in the repository | targeted edits, one make per commit | — |

**Measured before adopting it:** a headless `/ping` through `subc claude`
emitted the sentinel, served by `subconscious/glm-5.3-marathon`; and the
planted-attempt run, repeated with `subc claude` inside the sandbox and all
permissions bypassed, was denied on every escape (repo via Bash and Write,
`~/.claude`, push to the repo, GitHub push, `gh` token read). `subc` needs
no write outside the sandbox. Leak check independent of the model: clean.

**D3 guards, corrected:** a credential may travel only on its own route.
The Subconscious route carries **no** credential variable at all (subc
supplies its own), and its gateway must be `api.subconscious.dev`; the
Anthropic route carries exactly the OAuth token. `--max-budget-usd` applies
to the Opus route only — Claude Code's cost for the Subconscious model is an
estimate (`costBasis: unknown`); the real figure is on the Subconscious
usage page.

**Known and accepted:** inside the sandbox the model can *read*
`~/.subconscious/profiles/default.env`, because `subc` must. The profile
denies reading the Anthropic token file; the Anthropic token is only ever in
the environment of an Anthropic-route process.

**Observed in passing, and it is the design's premise:** in the sandboxed
GLM run, one control step failed for a reason the model then explained
wrongly (it guessed a hidden `.gitignore`; the file had simply been
committed by an earlier run). No stage's outcome is taken from a model's
account of itself.


---

# v1.2 — close-out (2026-09-23)

## Deviations

- **Coverage stopped where acquisition did.** The plan shipped the machine
  and tranche 1; the phase kept batching, make by make, by operator
  decision, until the operator named KTM the last make. Nine makes were
  batched (SYM, Kymco, Honda, Suzuki, Kawasaki, BMW, Triumph, Yamaha, KTM)
  and eight wrote entries; Triumph wrote none (its handbook downloads
  return 403). What stopped coverage was never the procedure: it was a
  maker site refusing a script, a make with no measured route, or a route
  never batched. All of it is **F143**, with counts: 528 unknown census
  spellings, 412 of them machine names.
- **The source route changed twice.** v1.1 moved the source stages to
  Subconscious (GLM-5.3 Marathon). Subconscious was then suspended, and the
  operator set a fallback: `claude-opus-5-5@medium`, one turn, the same
  guards. 57 of the 71 entries carry that route in `source_route`, so they
  can be re-sourced once Subconscious is back (F143).
- **The source stage is not an agent.** As planned it browsed; it spent
  7.66M tokens on one spelling. It became one turn with no tools, reading
  only `candidates.py`'s excerpts, with per-stage token ceilings and E10
  binding every quote to an excerpt it was handed.
- **Acquisition was built, not only measured.** D7 said "measured, not
  built out". `acquire.py` was built: maker routes (spec pages, BMW's
  index, Honda motopub, Yamaha's Owner's Manual Library, ktm.com's manual
  list), an operator inbox, provenance sidecars and E11.
- **Owner's manuals replaced spec pages** for Yamaha and KTM: spec pages
  give the gearbox only as table cells, and a table cell is not E12
  mechanism evidence. A manual-route PDF is read whole, and a manual that
  prints only a code ("YJ125Y", "YZFR6L") is named by its pinned list
  record (operator decisions).
- **Grom:** refuted from Honda's spec pages, not the service manual's page
  images. A better source came first.
- **Seven bug fixes**, one shared cause, recorded in the phase log: each
  rule was verified against the case it was written for, not the artefact
  it meets in use.
- **Held unknown by operator decision:** Yamaha MT-09 and MT-07; KTM's two
  contains matches, EXC and Enduro R; Honda's E-Clutch CB650R and CB750.
