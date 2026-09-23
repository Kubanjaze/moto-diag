---
name: source-transmission
description: Source transmission classifications for machines that resolve `unknown` — census, candidates, extract, classify, refute, write — one make per batch, via the sandboxed orchestrator. Use when adding or correcting entries in knowledge/transmission.py's TRANSMISSION_LOOKUP, or when asked to run a coverage batch for a make.
---

# source-transmission — one make per batch

A machine resolves `unknown` when nothing sourced says what gearbox it has,
and an unknown machine loses every transmission-scoped row. This procedure
adds lookup entries **only from the maker's own documents**, each step
answering a mistake that was actually made.

## Run a batch

```
.venv/bin/python -B .claude/skills/source-transmission/orchestrate.py batch MAKE [SPELLING ...]
```

No spellings → every `unknown` spelling of that make from the census.
`--source-route anthropic` sends the source stage to claude-sonnet-5 (one
turn, no tools, the same guards) while Subconscious is unavailable; refute
stays on Opus. The default is `subconscious`; switching back is the flag.
Each summary records `source_route`, and each lookup entry a batch writes
carries `source_route=` — so fallback entries can be selected and re-run. The
run lives in `~/.cache/motodiag/source-runs/<make>_<stamp>/`: a fresh clone,
a DB snapshot, `candidates.json`, `source.json`, `refute.json`, `summary.json`. The operator
sees the summary and any stop — nothing else.

## The steps

| step | who | rule | the mistake it answers |
|---|---|---|---|
| census | `census.py` | every unknown pair, whole junction, no sampling | a model counting spellings produced 427 where ~600 was true (F139) |
| acquire | `acquire.py`, no model | a make's measured route (D7) fetches maker pages/PDFs into `~/research/motodiag/acquired/<Make>/`, sidecar by the script; the operator's hand downloads go through `inbox/` (`inbox/README.md`); cap 30/run, 1 req/s, robots.txt | a model that writes its own "original" (F141) |
| candidates | `candidates.py`, no model | library files that name the spelling, cut to ±40 lines with path and page; none → `no_evidence` **without a model call** | an agent-loop source stage browsed its way to 7.66M tokens for one spelling |
| dry run | `entry_check.mechanism_lines`, no model | a spelling is sent only if an excerpt sentence passes E12 or names V-matic, CVT, DCT, Y-AMT, AMT, centrifugal, direct drive, automatic, V-belt, variator or single-speed (a miss drops a spelling silently; a false alarm costs one call); the rest are `no_evidence`, "no mechanism line in the fetched pages"; counts in `summary.mechanism_lines` | Triumph and Yamaha spec pages give the gearbox only as table cells: 24 calls, nothing writable |
| extract | GLM-5.3 Marathon via `subc`, sandboxed, **one turn, no tools** | from the excerpts in its prompt only; the **maker's own word**, quoted verbatim; model codes become aliases | V-matic is Honda's CVT; a search for `CVT` misses it |
| classify | same | by mechanism; ambiguous → candidate set; no evidence → NULL | a model family is not a machine |
| reject | `entry_check.py` | E1–E10; E10: the document must be one of the excerpts handed over and the quote inside them; E3 matches the document itself | a quote that reads well but is not on the page — including in a file the model itself wrote (F141) |
| refute | Opus, sandboxed, fresh context | opens every cited page; **page images where OCR is weak** | OCR "Constanmesh,4speeds" is not evidence |
| write | Opus in the repo | one entry per model, citation quoted; **one make per commit**; tests; before/after table | — |

## Stops (alert + non-zero exit)

A batch stops **whole** — writes nothing — only on a systemic signal
(operator, 2026-09-23): a source- or refute-stage error, the wrong model
serving, a stage with no recorded usage, a token ceiling (150,000 per
spelling sent for every stage but refute; 300,000 per finding refuted for
refute), a blocked rate above 50%, or refute killing more than a quarter
of what it checked.

One finding's refute kill, entry_check rejection, names-the-model
disagreement, or a spelling the source skipped is **withheld**: recorded in
`summary.withheld`, never written, and it does not block the batch's other
ready findings. A `manual` finding needs a quote naming a rider-operated
clutch, a foot-shift pattern or the word "manual" within three words of
transmission, gearbox, gear shift or a gear count (E12). **Never resolve a
stop by editing the check.**

## The boundary

Every model stage runs under `sandbox-exec` in the run's clone:
`sandbox.sb.tmpl`, proven by `tests/test_phase257_sandbox_boundary.py`.
A writes-only profile was **not** a boundary — a dry-run push authenticated
through the keychain (Phase 257 Step 0). The profile denies credentials,
not network.

## Writing an entry

`TRANSMISSION_LOOKUP` in `src/motodiag/knowledge/transmission.py`: one
`_E(make, canonical, VALUE, (aliases...), "source quote")` per model, in
its make's section. The source string names the document and quotes it.
Ambiguous models go in `AMBIGUOUS_MODELS`. There is **no make-default**.
