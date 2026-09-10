# Phase 244K — Schema drift in Gate 11 — phase log

**Status:** Planned
**Opened:** 2026-09-10

---

## 2026-09-10 — Plan v1.0 written

Gate 11 exists to stop the backend and the mobile app disagreeing about the API,
and it compares **paths only**. Phase 244J regenerated the mobile snapshot for
an unrelated reason and found that `KnownIssueResponse.source` had been missing
`"regulation"` since Phase 235B — **85 backend commits** during which the app
compiled against a union that did not contain a value the API could return.

The gate was green throughout, and correctly so by its own terms: no path had
changed. **That is the defect. A guard that watches one axis reports safety on
every axis**, and a green gate gets read as a statement about the contract
rather than about paths.

Worth being precise about how this surfaced: nobody was looking for it. It fell
out of adding an unrelated endpoint. A backend-only phase would have left it
drifting, and there is no reason to think 85 commits was the limit.

**Step 0 settled the strictness question.** The live spec and the snapshot are
currently identical at every level, because 244J just regenerated them — so the
gate can be tightened now without first repairing drift. But whole-document
equality would be wrong: `info.version` tracks the package version and moves on
release, and `servers` is built from environment config. Gating those produces
failures regeneration cannot fix, which teaches people to regenerate reflexively
— that is how a guard becomes a ritual.

So the gate scopes to what the app actually compiles against: `paths` and
`components.schemas`, in both directions, with the drift case separated from the
missing case because **a wrong type is worse than a missing one** — the missing
one fails at build, the wrong one compiles and lies.

The last decision is about the failure message. `"KnownIssueResponse differs"`
sends someone diffing 400KB of JSON. The guard will name the field and the
change, and repeat both regeneration commands — 244J found that
`src/api-types.ts` is tracked and derived, so refreshing the schema without
regenerating types leaves that repo internally inconsistent.
