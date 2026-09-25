# Cheap builder, frontier reviewer: GLM-5.3 building phases 258–260 under Opus review

**Dates:** 2026-09-24 19:13 to 2026-09-25 13:00 (US Eastern)
**Status:** The experiment's findings are final. The process findings in §10 stay open until the queued pipeline is complete: Track N batches 1–3, then gate 272.
**Written by:** the Opus advisor session, from the run artefacts listed in §11. Every figure here was measured, not estimated, unless marked *est.*

---

## Summary

- **The setup.** Three consecutive phases were built by GLM-5.3 Marathon (through the Subconscious gateway) inside a macOS sandbox: 258, a test-only gate; 259, content plus a database migration; and 260, content plus a migration. Opus 5.5 then reviewed, re-tested, merged and deployed each one.
- **Build speed and content.** GLM brought each phase to "ready to merge" in 38–44 minutes, and its document work was accurate. In 259, every figure and quote it cited checked out on the manual page.
- **Integration defects.** Every phase still needed fixes before merge. They were almost all integration defects: repo-wide conventions, enforced by tests GLM had not run. There were no content errors. The Opus side introduced two defects of its own and shared a third.
- **Opus cost of landing a phase.** For 258 it was about a third of the cost of an Opus-built phase. For 259 it was about the same, because the review ran inside a long, high-context advisor session. For 260, a fresh review session cost about half what the advisor session had.
- **Budget.** Subconscious's Base plan allowed about **two GLM phases a day**. The third, 260, ran out of allowance minutes after its close-out commit.
- **Wall-clock.** Time was dominated by the full test suite, not by building: about 50 minutes serially, run 1–3 times per phase. That led to Phase 355, and the suite now runs in parallel in about 13.5 minutes with proven parity.

---

## 1. What was tested

| | |
|---|---|
| Builder | GLM-5.3 Marathon, through `subc claude` (Claude Code 2.1.282), with permissions bypassed inside the sandbox |
| Reviewer and lander | Claude Opus 5.5: the advisor session (258, 259) and a fresh builder session (260) |
| Sandbox | macOS `sandbox-exec` with Phase 257's profile. Writes were allowed only to the builder's clone (`~/Projects/moto-diag-glm`) and its run directory. No credentials were reachable. |
| Boundary proof | Planted writes to 8 locations outside the clone were all refused. A push to the main repo was rejected, and a push to GitHub had no credentials. The control dry run, outside the box, authenticated. |
| Division of work | GLM: Step 0, plan, build, tests, close-out documents, up to "ready to merge". Opus: review, refute of every document claim, the regression of record, merge, deploy. |

**Traps found while setting it up:**
- The shared virtualenv is an *editable* install of the main repo. A clone using it tests master's code unless `PYTHONPATH` points at the clone.
- `.gitignore`'s `.venv/` does not match a `.venv` symlink.
- zsh heredocs write to `/tmp`, which the sandbox refuses.

## 2. Results by phase

| | 258 Gate 14 | 259 PPI engine | 260 PPI chassis |
|---|---|---|---|
| Kind | tests only | content + migration 067 | content + migration 068 |
| GLM build time | 38 min | 44 min | 41 min (then out of allowance) |
| GLM model calls / tool calls | 177 / 193 | 185 / 211 | 167 / 171 |
| GLM context per call, median / max | 288K / 411K | 276K / 317K | 350K / 412K |
| GLM input: uncached / cached | 25.2M / 23.6M | 24.4M / 22.9M | 26.6M / 25.2M |
| Subconscious allowance used | ≈25M counted *(est.; the daily counter rolled over)* | **49.5%** of the day | the rest; 100% at 51.3M |
| Opus review and landing: calls | 41 | 109 | 130 |
| Opus tokens read / written / output | 14.7M / 0.38M / 61K | 55.5M / 0.16M / 115K | 23.1M / 0.62M / 93K |
| Where the Opus work ran | the advisor session | the advisor session | a fresh session |
| Full-suite runs before green | 2 (1 red) | 3 (2 red) | 2 (1 red) |
| Tests at merge | 9,321 | 9,346 | 9,375 |

## 3. Against Opus-built phases

| | Opus-built 353 | Opus-built 354 | GLM + Opus review 260 |
|---|---|---|---|
| Opus calls | 269 (4 refuter agents included) | 330 | 130 |
| Opus tokens read | 44.5M | 61.5M | 23.1M |
| Opus tokens written | 0.83M | 0.73M | 0.62M |
| Opus output | 187K | 274K | 93K |
| Session wall-clock | ~1.9 h | ~3.1 h | GLM 41 min, then Opus 3.3 h |

Read these with care. 353 and 354 were content phases with a four-agent refute. 260 was a content phase whose refute ran inside the landing session. The GLM path cut Opus usage roughly in half *when the review ran in a fresh session*. It did not cut wall-clock.

## 4. Quality: what GLM got right and wrong

**Right.**
- **Document claims.** In 259, claims C1–C6 matched the cited PDF pages (figures exact, quotes verbatim), and C7's conclusion (no leak-down test in the library) survived a whitespace-proof re-search.
- **Tests.** They were substantive: they reached the CLI, the API and the diagnostic prompt, and the mutation runs went red (258: 11/11).
- **Findings.** GLM filed real ones: F153–F157 in 258, F159 in 260.
- **Traps.** Once a trap was named in its prompt, GLM avoided it. 260 fixed the "Phase 260" reference that 259 had missed, because the F158 rule was in its prompt.

**Defects that reached review.**

| Phase | Defect | Introduced by | Caught by |
|---|---|---|---|
| 258 | A literal pin of the schema head (F124) | GLM | the full regression |
| 258 | The test-floor comment credited the wrong 8 tests | GLM | Opus review |
| 259 | A test read the live database (it would have failed after the deploy) | GLM | Opus review |
| 259 | The integration-gap allowlist went stale when a module was wired | GLM | the full regression |
| 259 | The same allowlist sizes are pinned in 3 files; the fix above moved one | **Opus** | the full regression |
| 259 | C7's control claim was false for its own search method | GLM | Opus refute |
| 259 | "Phase 260" left in the new template's user-facing text | GLM, missed by Opus | the census, after the deploy |
| 260 | Inserting 068 stripped 067's rollback | GLM | Opus review |
| 260 | Upgrade and rollback tests (including 259's rewrite) held only while their migration was the head | GLM **and Opus** | Opus landing |
| 260 | The fix above wrote a head literal (F124) | Opus | the full regression |

**The pattern.** The defects are integration defects. They break conventions that live in tests GLM did not run, or they surface only once the next migration lands. Content errors are rare. The full regression caught four of these defects, one run at a time. That is why a GLM phase needed 2–3 full runs.

## 5. Where the Opus cost went

- **Context size.** In the advisor session each Opus call re-read about 500K tokens of conversation. That made 259's landing about 2.4× more expensive in reads than 260's landing in a fresh session.
- **Review cycles.** Each late failure meant another fix and another full regression.
- **The refute pass,** which opens every cited page, stays on Opus by design.

## 6. Time: the test suite

- Serially the suite took about 50 minutes (49 min 40 s measured on 2026-09-25) for about 9,375 tests. Each phase ran it 1–3 times.
- **Phase 355** (merged `a547958`) runs it with pytest-xdist: **13 min 28 s for 9,388 tests** (`-n auto --dist load`). Parity is proven three ways: the passed test IDs match the serial run's, the result is stable across two runs, and a planted failure is caught. 8 parallel-unsafe tests were fixed.
- **The variance is the machine,** not the tool: the same tree took 24–27 minutes in the afternoon. Low Power Mode is on for AC power, and SQLite's fsync caps the workers at 25–35% CPU.

## 7. Subconscious budget

- The Base plan shows **60M daily tokens**, resetting at 00:00 UTC (20:00 US Eastern).
- One GLM phase used about **half the daily allowance**. The allowance hit 100% at 51.3M GLM tokens during 260.
- What counts is roughly *uncached input + output*: in the first two minutes of 258 the counter tracked that sum. Cache reads appear to count for little or nothing.
- The plan page shows "Cancels Oct 23, 2026".

## 8. Verdict

GLM is a fast, accurate *content* builder, and a poor *integration* builder in this repo. It pays only when all four of these hold:
1. GLM runs the **full suite** itself before handing over, not a hand-kept list of checks;
2. the review runs in a **fresh, small-context** Opus session;
3. every known trap is **named in the prompt**;
4. the suite is **fast**, as it has been since 355.

Under those conditions it roughly halves Opus usage per phase, at about two phases a day on the Base plan. Without them it saves little. 259 cost about as much Opus as an Opus-built phase.

## 9. Changes adopted because of this (committed)

- CLAUDE.md, "How a phase runs": five standing rules (`c1b3ed7`). A phase runs to its finish line; bulk reading goes on GLM and judgment on Opus; whole-tree checks run before every commit; every close-out writes a handoff; one writing session per checkout.
- `roadmap_check.py` R6: every close-out must leave its handoff (`c1b3ed7`).
- Rule 1: only the operator grants a stop's approval, in their own words; pre-approvals are scoped (`b3285f3`).
- Phase 355: the parallel regression, `regression.sh` (`a547958`).
- F158: 33 internal build references remain in user-facing text after 068, with a guard test proposed.

## 10. Parked, not acted on until the pipeline completes

These are the operator's "kinks" list. They are speculative until the queued work (Track N, gate 272) is done:
- The whole-tree checks are a hand-kept list. At least 14 exist, and CLAUDE.md names 4.
- The same allowlist sizes are pinned in three test files.
- The F158 guard test is not written; 33 references remain.
- R6's convention for batched phases, which batch 1 will settle.
- Review cost in a long session compared with a fresh one.
- The GLM sandbox's `PYTHONPATH` breaks 7 packaging tests; there is no `uv` for a separate venv.
- verify_phase check 12 cannot see a refute written as prose.
- A5 does not require the regression command.
- The machine speed limit: Low Power Mode on AC, SQLite fsync.

## 11. Data sources

| What | Where |
|---|---|
| GLM run directories (prompt, sandbox profile, baseline, transcript) | `~/.cache/motodiag/glm-builder/258_20260924_190801/`, `259_20260924_211014/`, `260_20260925_005511/` (transcripts under `tmp/cfg/projects/`) |
| Opus landing of 260 | Claude Code session `f196d436` |
| Advisor session (the 258 and 259 landings, the census, this report) | session `d9364522` |
| Opus-built comparisons | 353: session `2f039c7d` plus 4 subagents; 354: session `0f4f7aed` |
| Phase 355 (parallel tests) | session `319fe5f2`; `docs/phases/completed/355_*` |
| Phase records | `docs/phases/completed/258_*`, `259_*`, `260_*`; `docs/handoffs/2026-09-2{4,5}_*` |
| Findings | `docs/FOLLOWUPS.md`: F153–F159 |
| Metric script | a per-transcript card: model calls, tokens by kind, context median and max, tool counts |
