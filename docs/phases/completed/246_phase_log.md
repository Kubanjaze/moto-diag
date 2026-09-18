# Phase 246 — BMS diagnostics: the generic layer, anchored per make — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-18

---

## 2026-09-18 — Plan v0.9, then v1.0

The first row since the 244 series that authors corpus content, so the
draft stopped for review with Step 0 done and nothing built. The operator
settled four things: the research runs as a workflow whose refuter fetches
every cited page itself; the Unofficial Zero Manual is `forum` except where
it reproduces an official document; a forum-cited number is allowed only if
its label is surfaced wherever the number is displayed, enforced by a test;
and the `battery` DTC category — audited end to end and found data-only at
the contract but migration-bound at the meta table, over a corpus holding
zero Energica DTCs — is 247's.

## 2026-09-18 — Part 1: the label travels with the number

Step 0 had found one display surface with no label: the prompt.
`build_knowledge_context` now carries `source:` per entry and the system
prompt says what the label means. Nine tests walk every surface with one
seeded forum threshold. Committed before any content was written, because
the rule is what makes the content safe to write.

## 2026-09-18 — Built

Sixty claims, fourteen pages, every page fetched by the refuter that judged
it; a critic read the survivors against the pages and cut what the refuters
let through. Seven rows: five service-manual concepts, each written as what
the BMS does and how Zero, Energica and LiveWire each show it, with the
documents named by code; two forum rows for the only community numbers,
on their own rows because a row has one label. Nothing model-generated.
The concept check's first draft matched "moderate" and let a deleted row
pass — fixed to word-bounded title matches, and the mutation dies.

The forum source is not the one Decision 2 named: the Unofficial Zero
Manual could not be fetched (expired TLS), so under Decision 1 it could not
be cited; zerologs.bike, the one community source a refuter could verify,
carries the two forum rows, and the operator confirmed it is independent.
Re-verified at close-out: S0-6 was wrong about the meta table — migration
004 seeded all twenty categories, `hv_battery` included; the CLI accepts
it; it holds no rows because the corpus seeds no Energica DTCs. Nothing to
add, nothing to classify; recorded as F90.

51 tests, 390 across the suites, 6/6 mutations. README count 970 → 977.

## 2026-09-18 — Complete

Regression **7,028 passed, 0 failed, 27:22**. No schema change.
