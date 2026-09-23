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

No spellings → every `unknown` spelling of that make from the census. The
run lives in `~/.cache/motodiag/source-runs/<make>_<stamp>/`: a fresh clone,
a DB snapshot, `candidates.json`, `source.json`, `refute.json`, `summary.json`. The operator
sees the summary and any stop — nothing else.

## The steps

| step | who | rule | the mistake it answers |
|---|---|---|---|
| census | `census.py` | every unknown pair, whole junction, no sampling | a model counting spellings produced 427 where ~600 was true (F139) |
| candidates | `candidates.py`, no model | library files that name the spelling, cut to ±40 lines with path and page; none → `no_evidence` **without a model call** | an agent-loop source stage browsed its way to 7.66M tokens for one spelling |
| extract | GLM-5.3 Marathon via `subc`, sandboxed, **one turn, no tools** | from the excerpts in its prompt only; the **maker's own word**, quoted verbatim; model codes become aliases | V-matic is Honda's CVT; a search for `CVT` misses it |
| classify | same | by mechanism; ambiguous → candidate set; no evidence → NULL | a model family is not a machine |
| reject | `entry_check.py` | E1–E10; E10: the document must be one of the excerpts handed over and the quote inside them; E3 matches the document itself | a quote that reads well but is not on the page — including in a file the model itself wrote (F141) |
| refute | Opus, sandboxed, fresh context | opens every cited page; **page images where OCR is weak** | OCR "Constanmesh,4speeds" is not evidence |
| write | Opus in the repo | one entry per model, citation quoted; **one make per commit**; tests; before/after table | — |

## Stops (alert + non-zero exit)

A refute verdict that is not `kept`; blocked rate above 50%; a spelling
with no finding; any entry_check rejection; a stage served by the wrong
model. **Never resolve a stop by editing the check.**

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
