# source-transmission — changelog

## 2026-09-22 — created (Phase 257)

A sandboxed, headless procedure for the transmission lookup. Built boundary
first: the sandbox profile and its planted-attempt test before any stage
that runs a model, because the Step 0 finding that shaped everything was
that **a writes-only profile was not a boundary** — a dry-run push to
GitHub authenticated through the macOS keychain helper.

**Two routes.** The source stages run through Subconscious (`subc claude`,
GLM-5.3 Marathon) — the operator's reason for the orchestrator is to spend
the long, context-heavy reading there. Refute runs on Opus. A credential
only ever travels on its own route; the Subconscious route carries none
(subc holds its own). The guard exists because it happened: the operator's
first key file pointed the Anthropic token at a third-party host.

**The model's account is never the evidence.** entry_check matches every
quote against the document text; refute re-opens every page; the leak
checks in Step 0 were run independently of what the model reported. In the
first sandboxed GLM run a control failed for a reason the model then
explained wrongly — the premise, observed.

## 2026-09-22 — E9: evidence copies must declare their originals (F141)

The Honda batch saved text renders under `evidence/` and E3 verified the
quotes against those renders — files the source stage itself wrote. A
model that edits its own copy passed the check, because the check read
the copy. Now a document under `evidence/` must carry a
`<file>.provenance.json` sidecar (original — an on-disk library path or
a URL — plus its sha256, and `fetched_as` for a URL). E9 rejects a copy
with no sidecar, an unreadable original, or a hash that no longer
matches; E3 extracts the ORIGINAL's text in entry_check's own code
(HTML→text there, `.txt` raw, PDF via pypdf) and matches the quote
against that, never against the copy. Known-bad fixtures plant a
doctored copy, a missing sidecar and a stale hash; both breaks were
seen to fail before the check was trusted. Filed and closed as F141 in
the same commit.

## 2026-09-23 — the source stage is one turn with no tools (token redesign)

As an agent loop the source stage cost ~2.4M tokens a spelling; Kymco's
one spelling was 7,661,322 input tokens. It browsed. Now `candidates.py`
(no model) cuts the library to excerpts per spelling — ±40 lines, path,
page — and the source stage gets those in its prompt, with `--tools ""`,
and answers once. A spelling with no excerpt is `no_evidence` and the
model is not called. More than two turns is an error.

This also closes what E9 left open (F141): a sandboxed model with tools
could write the "original" a sidecar declares. The stage now writes
nothing, and **E10** rejects a finding whose document is not one of the
excerpts it was handed, or whose quote is not inside them. E3 reads a
library original through `_extract_text`, so an HTML page is matched as
the text the stage saw.

Web acquire left the source stage with this change: a manual not on disk
comes back `no_evidence`. Refute is unchanged and keeps its tools.

## 2026-09-23 — every stage's tokens are recorded; 150K per spelling is a stop

`summary.json` carries `tokens`: each stage's usage from `claude -p`'s
`modelUsage`, the total, and the ceiling — 150,000 × spellings sent to
the model, set by the operator and not an option. Over it after the
source stage, refute is not run. The runs did always record usage in
`source.json`; nothing summed it or acted on it.
