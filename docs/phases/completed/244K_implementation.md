# Phase 244K — The gate that watched the doors and not the rooms

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

Gate 11 exists to stop the backend and the mobile app disagreeing about the API.
It compares **paths only**. At Phase 244J, regenerating the mobile snapshot for
an unrelated reason revealed that `KnownIssueResponse.source` had been missing
`"regulation"` since Phase 235B — **85 backend commits**, during which the app
compiled against a union that did not contain a value the API could return.

The gate was green the entire time, and correctly so: no path had changed.

**A guard that watches one axis reports safety on every axis.** That is the
defect, and it is worse than having no guard, because a green gate is read as a
statement about the contract rather than about paths.

## Step 0 findings

**Live spec and snapshot are currently identical** at every level — paths,
components, info, tags, version — because Phase 244J regenerated them. So the
gate can be tightened now without first repairing drift, which will not be true
again once anything diverges.

**Whole-document equality would be brittle, and wrongly so.** Two keys change
for reasons that have nothing to do with the contract:

| key | why it moves |
|---|---|
| `info.version` | tracks the package version, bumps on release |
| `servers` | built from `api_servers` config — environment-dependent |

Gating on those would produce failures that regeneration cannot fix and teach
people to regenerate reflexively, which is how a guard becomes a ritual.

**So the gate scopes to what the app compiles against**: `paths` and
`components.schemas`. Nothing else.

## Non-goals

- **Not gating `info` or `servers`.** They differ for legitimate reasons.
- **Not auto-regenerating.** A gate that fixes what it finds stops reporting.
  The remedy stays a deliberate command in the mobile repo.
- **Not changing what the snapshot contains.** Phase 244J already regenerated it.

## Logic

Three assertions beside the existing path check, each failing separately so the
message names the actual problem:

1. **A live schema absent from the snapshot** — the app has no type for
   something the API returns. Mirrors the existing path rule.
2. **A shared schema that differs** — the app's type is *wrong*, which is worse
   than missing because nothing fails at compile time. This is the
   `regulation` case, and the reason the phase exists.
3. **A snapshot schema absent from the live API** — the app types something the
   backend no longer returns. The opposite direction, and the one that breaks at
   runtime rather than at build.

**Failures name the field, not just the schema.** `"KnownIssueResponse differs"`
sends someone diffing 400KB of JSON; `"KnownIssueResponse.source: snapshot is
missing 'regulation'"` is actionable. The comparison walks one level into
`properties` to say which fields moved.

**The remedy is repeated in the message**, including that `generate-api-types`
must follow `refresh-api-schema` — Phase 244J found that the tracked
`src/api-types.ts` is derived from the snapshot, so refreshing one without the
other leaves that repo internally inconsistent.

## Key Concepts

- **A guard that watches one axis reports safety on every axis.** Green meant
  "no new paths", and was read as "the contract matches".
- **Wrong types are worse than missing types.** A missing type fails at build;
  a wrong one compiles and lies.
- **Gate what is contractual, not what is incidental.** Version strings and
  server URLs are neither.
- **A failure message that requires a 400KB diff is a failure to report.**

## Verification Checklist

- [x] A new live schema absent from the snapshot fails
- [x] A shared schema whose field set changed fails
- [x] A shared schema whose enum gained a value fails — the exact 235B case
- [x] A snapshot schema absent from the live API fails
- [x] `info.version` differing does **not** fail
- [x] `servers` differing does **not** fail
- [x] The failure names the schema and the field
- [x] The message names both regeneration commands
- [x] The existing path assertion still works
- [x] Mutation: revert the snapshot's `source` enum → the drift guard fails
- [x] Full regression green

## Risks

- **Tightening a gate makes unrelated work fail.** Any backend phase touching a
  response model now needs the mobile snapshot regenerated. That is the point,
  and it is a real tax — so the failure message carries the exact commands
  rather than leaving someone to find them.
- **The snapshot lives in another repository**, so a contributor without it
  checked out cannot satisfy the gate. The existing tests already skip when the
  file is missing; that behaviour is preserved rather than made stricter.
- **Over-precise field reporting could mislead** if a schema changes shape
  entirely. The comparison reports field-level detail where both sides are
  objects with `properties`, and falls back to naming the schema otherwise.

---

## Deviations from Plan

**The class already had a philosophy the plan nearly broke.** Its docstring
states: *"Structural comparison, not byte-wise: a prose edit to a description
should not fail the build."* Strict schema equality — the obvious
implementation, and what v1.0 implied — would have violated that on the first
reworded field description.

Prose keys (`description`, `title`, `example`, `examples`) are now stripped
recursively before comparison. Guarded in both directions: a reworded
description must not fail, and **an enum change must not be mistaken for prose**,
because stripping that swallowed the exact thing the phase exists to catch would
be the worst possible outcome.

**A guard of mine failed on itself — the fifth mention-versus-use of the
session, in the phase with the least excuse.** The assertion that `info` and
`servers` are not gated scanned the whole class source and found the very keys it
forbids, written in its own body. Repaired two ways: `code_of` from Phase 244G
strips the comments, and the check narrowed to `_schemas()` — the function that
decides what is compared. **A guard should read the code that does the work, not
the file it lives in.**

## Results

| Metric | Value |
|--------|-------|
| Axes gated | paths **and** `components.schemas`, both directions |
| Deliberately ungated | `info.version`, `servers` — with a guard enforcing it |
| Guards | 6 |
| Mutations run / behaved correctly | 5 / 5 |
| Regression | **6306 passed / 0 failed** (baseline 6300; +6 guards) |

Mutation 1 reproduced the real defect — removing `"regulation"` from the
snapshot's `source` enum — and produced:

```
KnownIssueResponse.source: snapshot is missing ['regulation']
```

Not *"a schema differs"*. The field, and the value.

**Key finding: a guard that watches one axis reports safety on every axis.**
Gate 11 was green for 85 commits while the contract was wrong, and it was
correct by its own terms the whole time — no path had changed. Nothing was
broken; the guard simply answered a narrower question than anyone was reading it
as. **Green meant "no new paths" and was read as "the contract matches".**

The three severities are now separated because they fail differently: a
**missing** type fails at build, a **stale** type 404s at runtime, and a
**wrong** type compiles and lies. The last is what went unnoticed, and it is the
one with no natural symptom.
