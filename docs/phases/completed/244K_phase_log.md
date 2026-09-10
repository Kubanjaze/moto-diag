# Phase 244K — Schema drift in Gate 11 — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

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


---

## 2026-09-10 — Built

Gate 11 now asks its three questions of `components.schemas` as well as paths: a
schema the snapshot lacks, a shared schema that drifted, and a schema the API no
longer returns. Separated deliberately, because they fail differently — a
**missing** type fails at build, a **stale** type 404s at runtime, and a
**wrong** type compiles and lies. The last is the one that went unnoticed for 85
commits, and the one with no natural symptom.

**The class already had a philosophy the plan nearly broke.** Its docstring says
comparison is structural, not byte-wise, so a reworded description does not fail
the build. Strict schema equality would have violated that immediately. Prose
keys are stripped recursively instead — and guarded in both directions, because
stripping that also swallowed enum changes would have quietly disabled the whole
point.

**A guard of mine failed on itself.** The assertion that `info` and `servers`
are not gated scanned the whole class and found those keys written in its own
body — the fifth mention-versus-use failure of the session, in the phase with
the least excuse for it. `code_of` from Phase 244G handled the comments, and
narrowing the check to `_schemas()` handled the self-reference. **A guard should
read the code that does the work, not the file it lives in.**

**Failure messages name the field.** Mutating the snapshot to reproduce the real
Phase 235B defect produced `KnownIssueResponse.source: snapshot is missing
['regulation']` rather than "a schema differs" — the difference between a report
and a rumour, on a 400KB document.

`info.version` and `servers` stay ungated on purpose: the first moves on
release, the second is environment config, and failures regeneration cannot fix
teach people to regenerate reflexively.

6 guards, 5/5 mutations behaved correctly, F9 lint clean. Regression **6306 passed / 0 failed** (baseline 6300; +6 guards).
