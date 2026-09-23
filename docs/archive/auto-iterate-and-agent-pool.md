# Auto-iterate and the agent pool — ARCHIVED

**Archived 2026-09-22 by Phase 255D. Nothing invokes this.**

Measured over every completed phase document before archiving:

| machinery | phases citing it | most recent |
|---|---|---|
| `auto-iterate` | 6 | **168** |
| `Agent Pool` | 7 | **168** |
| `peak-efficiency` | 3 | **195C** (a passing mention) |
| `Builder-A` / the two-role pattern | 15 | **191D** |
| **`Spawn script`** | **0** | **never** |

Work was at 255D. The two-role pattern was last genuinely used **64 phases
ago**, the agent pool **87**, and the 50-line spawn script **has never been
cited by any phase at all.** Every reference found outside CLAUDE.md is a
*record* — a completed phase log describing a phase that was built this way
— and not one is an invocation.

It is archived rather than deleted because fifteen phase documents name it,
and those references should still resolve. If this is ever revived, it
should be revived as a procedure folder with a control, not pasted back
into a file everyone loads and nobody reads.

---

### Auto-iterate discipline (HARD RULES — no exceptions)
**CRITICAL: Speed does NOT justify skipping documentation.** Writing stub files ("Phase 03 plan") or blank docs and pushing them to git destroys accountability. Every implementation.md must have ALL sections with real content. Every phase_log.md must have timestamped entries with real detail. If you don't have time to write proper docs, you don't have time to move to the next phase.

When auto-iterating through multiple phases, these rules are non-negotiable:

**Per-phase checklist (execute in this exact order, every phase):**
1. Write implementation.md v1.0 (ALL sections: Goal, CLI, Outputs, Logic, Key Concepts, Verification Checklist, Risks)
2. Write phase_log.md with timestamped plan entry
3. Copy both to project repo, commit as plan, push
4. Write code (main.py or module)
5. Create venv / install deps (if needed)
6. Validate locally (`--help` or import check)
7. Run and verify output
8. Update implementation.md to v1.1 (update ALL sections, mark checklist [x], add Deviations/Results/key finding)
9. Update phase_log.md with timestamped build-complete entry
10. Copy both to project repo (COS: `docs/phases/{NNN}_*`)
11. Commit all code + docs, push
12. Move phases/in_progress/ → phases/completed/
13. Update ROADMAP (mark ✅)
14. For COS phases: update project `implementation.md` (add Phase History row, bump version), update project `phase_log.md`, push
15. Only now may you start the next phase

**What you must NEVER do during auto-iterate:**
- Skip writing implementation.md v1.0 before coding
- Skip the plan commit/push (step 3)
- Skip running the code (step 7) — every phase must produce verified output
- Skip updating implementation.md to v1.1 with results
- Skip updating phase_log.md with build-complete timestamp
- Batch tracking updates across multiple phases
- Skip the project-level doc updates for COS phases
- Use agents for phases that modify shared COS monorepo code (risk of conflicts)
- Sacrifice doc quality for speed — phase 130 gets the same detail as phase 101
- **Rush or abbreviate content to go faster** — every knowledge base entry, every fix procedure, every forum tip must be fully fleshed out with real detail, specific part numbers, labor times, and practical mechanic-level advice. "Detailed and meticulous" is the standard, not "rapid and abbreviated." If a phase has 10 issues, each issue gets the same level of care as a standalone write-up. Speed comes from efficient tooling, not from cutting corners on content quality.

**If an agent is used:** it must follow the same 15-step checklist. If it skips steps, the work must be redone manually before proceeding.

**What NEVER gets pushed to git:**
- The `phases/` directory itself — stays local as a planning record only
- Each project repo is standalone with its own `implementation.md` and `phase_log.md` copies

**`phases/` directory is local-only.** Never `git init` it, never push it.

---

## Agent Delegation for Auto-Iterate

**When to use:** Multi-phase auto-iterate sessions where the parent Claude (me) would otherwise burn context on mechanical build/finalize work that can be delegated.

**Model:** Me (the parent Claude) act as **Architect**. I spawn fresh **Builder** and **Finalizer** agents per phase. Two roles × two slots (A/B) for parallel work when independent phases can run concurrently.

### Honest limits of this pattern (Phase 125 correction)
- **Each `Agent()` call is a fresh spawn.** The Claude Code runtime in use (as of Phase 125) does NOT expose a `SendMessage`/continue-agent capability. Agents do not persist across dispatches — each phase gets newly-spawned agents with full priming prompts.
- **"2 per position" means parallelism, not redundancy-over-time.** Builder-A and Builder-B can run concurrently on two independent phases (or one phase + one prep task). Naming is stable for clarity in logs, but every spawn is independent.
- **Sandboxed agent runtime blocks Python execution.** Builder agents cannot run `pytest` themselves — they write code + tests and report done. The Architect (me) runs the phase-specific tests as trust-but-verify BEFORE trusting the "build complete" signal. This is already a CLAUDE.md rule; Phase 125 reinforced why it's mandatory.
- **"Idle" agents don't exist.** A spawned agent that finishes its priming prompt is done; there's no standby. Don't spawn primers ahead of time — spawn right when work is ready to dispatch.
- **Cross-session persistence**: the *pattern* persists via this CLAUDE.md section + memory entry. Agent instances do not.

### The two roles (spawned fresh per phase or per parallel work unit)

| Role | Slots | Responsibilities |
|------|------:|------|
| **Builder** | A, B | Write production code + test file. **Attempt** to run local phase tests (`pytest tests/test_phaseNNN_*.py`) — if sandbox blocks Python, report the built files and escalate test-run to Architect. Do NOT run full regression. Do NOT commit. |
| **Finalizer** | A, B | Run full regression. Update docs (v1.0 → v1.1, timestamped `phase_log.md` entries, move to `completed/`, update project `implementation.md` + `phase_log.md` + `ROADMAP.md` + package status table). Commit + push. Report commit hash + regression runtime. |

**Dispatch pattern**: normal sequential phases → spawn Builder, wait, verify tests, spawn Finalizer, wait, verify commit, move on. When two independent phases can be built in parallel, spawn Builder-A and Builder-B simultaneously; each gets a fresh Agent() call with its own priming prompt.

**Reality check (Phase 125 finding)**: if the agent runtime blocks Python (sandbox policy), the Builder cannot self-test. Architect must run Phase-specific tests BEFORE dispatching the Finalizer — otherwise Finalizer wastes 11+ minutes on a full regression that would fail on phase-specific tests anyway. This is why trust-but-verify exists.

### Spawn script (paste at the start of any auto-iterate session)

When a user asks to auto-iterate across multiple phases, and no agent pool exists yet, spawn all four in a single message (parallel calls). Each agent gets this priming prompt (adapt role name):

```
You are Builder-A for moto-diag auto-iterate (or whichever project is active).

Your role — permanent until this session ends:
- Await dispatch via SendMessage for one phase at a time.
- When dispatched, you will receive: phase number, path to implementation.md v1.0, scope constraints.
- Your job per phase:
  1. Read the plan at docs/phases/in_progress/NNN_implementation.md.
  2. Build production code + test file per the plan.
  3. Run ONLY the phase-specific tests (pytest tests/test_phaseNNN_*.py).
  4. Fix any failures caught by those tests.
  5. Report back: files created/modified, test count, any deviations, any build-phase fixes.
- Do NOT run the full regression — that's Finalizer's job.
- Do NOT commit or push — that's Finalizer's job.
- Do NOT modify shared CLAUDE.md, memory files, or any project outside the phase scope.
- Never skip or abbreviate workflow steps. Every implementation.md v1.0→v1.1 rule in CLAUDE.md applies.
- If you hit something unclear or a plan ambiguity, STOP and report — don't guess.

Acknowledge with "Builder-A online, awaiting phase dispatch" and wait.
```

Finalizer prompt is identical shape, role-adjusted:

```
You are Finalizer-A for moto-diag auto-iterate.

Your role — permanent until this session ends:
- Await dispatch after Builder reports a phase's code is complete.
- Your job per phase:
  1. Run full regression: .venv/Scripts/python.exe -m pytest tests/ (11-12 min typical).
  2. Verify zero regressions; if any, report and STOP.
  3. Update docs/phases/in_progress/NNN_implementation.md to v1.1 — ALL sections with real content, Verification Checklist [x], Results table populated, Deviations section if any.
  4. Update docs/phases/in_progress/NNN_phase_log.md — change status to ✅ Complete, add timestamped "Build complete" and "Documentation update" entries.
  5. Move both files from in_progress/ to completed/.
  6. Update project implementation.md (bump version, add Phase History row, update package status table if relevant, add new tables to DB inventory).
  7. Update project phase_log.md (timestamped entry, similar style to prior phases).
  8. Update docs/ROADMAP.md (mark phase ✅).
  9. git add -A && git commit (HEREDOC with Co-Authored-By trailer) && git push.
  10. Report back: commit hash, new/total test count, regression runtime, files touched.
- Never skip, abbreviate, or stub any doc section. CLAUDE.md quality bar applies.
- Never use --no-verify or --amend. Never force-push.
- If anything fails in a way you can't resolve, STOP and report.

Acknowledge with "Finalizer-A online, awaiting dispatch" and wait.
```

### Per-phase dispatch (me, as Architect)

1. Write `implementation.md` v1.0 + `phase_log.md` plan entry (my job — architecture calls don't delegate).
2. Commit + push the plan (my job — small diff, context-cheap).
3. **Spawn a fresh Builder** (`Agent(subagent_type="general-purpose")`) with the full priming prompt + phase-specific dispatch text. Use `run_in_background=true` so I can do other work while it builds.
4. When Builder reports done, **I run the phase-specific tests myself** (`pytest tests/test_phaseNNN_*.py`) — Builder's sandbox may have blocked Python, and even if not, running tests locally is faster than re-dispatching the agent to re-run and report.
5. If phase-specific tests fail, fix them in-place (or re-dispatch Builder with specific corrections). If they pass, proceed.
6. **Spawn a fresh Finalizer** with the full priming prompt + "Phase N built, please finalize" dispatch text.
7. Verify Finalizer's claimed commit actually exists on master (`git log --oneline -1`).
8. Update my local todo list. Move on to next phase.

### Parallel pattern (when two independent phases are ready)

Spawn Builder-A and Builder-B in a single message with two `Agent` tool calls (parallel). Each builds an independent phase. When both report done, run both phase-specific test suites. Then spawn Finalizer-A and Finalizer-B in parallel. Sequential commits (Finalizer-A commits first, Finalizer-B pulls + commits after — they must coordinate git state via the filesystem, not via messaging). Only useful when two phases truly have no file overlap.

### Full parallel-pipeline pattern (INTEGRAL TO AUTO-ITERATE)

The single-phase-at-a-time rhythm (write plan → build → regress → commit → next) is a **bottleneck** when the upcoming phase queue is well-defined. The correct pattern for any multi-phase auto-iterate run is a **staged pipeline with 6-8 concurrent agents**:

**Stage A — Planners (6-8 agents in parallel).** At the start of an auto-iterate batch, spawn one Planner agent per upcoming phase in a single message (multiple parallel `Agent()` calls). Each Planner reads the ROADMAP entry + relevant existing code, then writes `docs/phases/in_progress/NNN_implementation.md` v1.0 and `NNN_phase_log.md`. They do NOT write code. They do NOT commit — I do a single batched commit of all the plan docs once they return. This stage converts N phases of sequential plan-writing (me, ~3 min each) into one parallel wave.

**Stage B — Builders (2-6 agents in parallel when dependencies allow).** Once the plan docs are committed, spawn Builder agents. Phases that don't share files run concurrently; phases that depend on each other serialize. Rule of thumb: anything adding a new isolated module (e.g., per-protocol adapters in `hardware/protocols/*.py`) can parallelize; anything editing shared files (`cli/main.py`, `core/migrations.py`, `core/database.py` SCHEMA_VERSION) must serialize.

**Stage C — Architect verifies (sequential, fast).** When each Builder reports done, I run its phase-specific tests locally (~10 seconds each). I do NOT dispatch Finalizer agents on untested code.

**Stage D — Finalizers (2-4 agents in parallel, but sequential git commits).** Once phase tests pass, spawn Finalizer agents to update docs v1.0→v1.1 + project-level docs. Finalizers can work in parallel on their doc edits, but the final `git commit && git push` must serialize — only one Finalizer commits at a time, with the others pulling between. OR (simpler): Architect batches the commits, committing each phase as its Finalizer reports done.

**Stage E — Full regression runs in background** while Stage B/C/D for later phases continue. The 5-12 minute regression wait no longer blocks the pipeline.

### File-overlap analysis (before parallel Builder dispatch)

Before spawning N Builders in parallel, do a quick file-overlap audit. If two phases BOTH write to any of these shared-state files, serialize them:

- `src/motodiag/cli/main.py` — almost every CLI phase edits this to register a new group
- `src/motodiag/core/migrations.py` — sequential migration numbers
- `src/motodiag/core/database.py` — `SCHEMA_VERSION` bumps
- `pyproject.toml` — optional extras additions
- `implementation.md`, `phase_log.md`, `docs/ROADMAP.md` — project-level docs (Finalizer-serialize)

Phases that can cleanly parallelize: those adding ISOLATED new modules (new packages, new test files, new per-protocol adapters). Example: Phases 135-138 each add a separate `hardware/protocols/*.py` file — fully parallelizable once Phase 134's base.py is in place.

### Target throughput

With 6-8 concurrent agents at the Planner stage and 4-6 at the Builder stage, throughput should be **3-5x** the single-phase-at-a-time rhythm. The human-visible limit becomes git commit serialization + full regression cadence, not agent build time.

### When to DROP parallelism and go sequential
- Gate phases (integration tests across all prior phases). Always sequential.
- Phases that touch multiple shared files (cli/main.py + migrations.py + etc.). Serialize.
- When regression breaks and needs diagnosis — stop spawning new agents until green.
- When a Builder reports deviations that worry me — pause, resolve, then resume pipeline.

### Trust-but-verify (hard rule)

After every Finalizer run, I MUST:
- `git log --oneline -1` — confirm the commit hash the Finalizer reported exists
- `git diff HEAD~1 --stat` — spot-check the file count matches what Finalizer claimed
- Read a random line from the new implementation.md v1.1 to confirm content quality (no stubs, no "TBD", no template placeholders)

If any of these fail, the phase is NOT complete regardless of what the Finalizer said. I fix it myself or re-dispatch with specific corrections.

### When NOT to use the pool
- Phase involves me making scope/architecture calls (plan writing, gate tests, roadmap changes). That's Architect work — I don't delegate.
- Phase touches CLAUDE.md or memory files. Same reason.
- Phase is < 200 LoC total and can be built in-process faster than coordinating with an agent.
- User says "just do it yourself."

### Cross-session continuity
Agent instances don't survive a session ending. They also don't survive a single session, as of the Phase 125 runtime check — each `Agent()` call is fresh. What persists:
- This CLAUDE.md section (read automatically at every session start)
- Memory entry `feedback_persistent_agent_positions.md` (loaded via MEMORY.md index)

The **pattern is permanent**: Architect → plan → spawn Builder → verify tests → spawn Finalizer → verify commit → next phase. The priming prompts above are re-used verbatim on every spawn. Total cost per delegated phase is ~2× priming prompt tokens — non-trivial but much less than the parent Claude holding the full build-and-finalize context itself across a multi-phase run.

---

## Peak-Efficiency Agent Pool Mode (8-10 concurrent agents, role-diversified)

**When the user asks for "peak efficiency" / "multiple agents running in tandem" / explicitly requests a specific agent count (e.g., "8 agents", "4 builders + 2 architects"), switch from the sequential parallel-pipeline into this expanded role-diversified pool.** Canonically deployed 2026-04-18 during moto-diag Track E auto-iterate (Phases 141-146 landed in parallel).

### Role distribution (target 8-10 concurrent)

| Role | Count | Purpose |
|------|------:|---------|
| **Builder** | 2-4 | Write production code from `implementation.md` v1.0 specs. File-overlap-analyzed before dispatch (see shared-file rules below). |
| **Planner** | 1-2 | Draft implementation.md v1.0 + phase_log.md plan entries for upcoming phases. `Plan` subagent type. Returns docs inline for Architect to persist. |
| **Architect-Reviewer** | 1 | Independent cross-phase review of in-flight plans. Reports API contract drift, kwarg-ordering conflicts, file-overlap risks. |
| **Architect-Auditor** | 1 | Project-level drift audit: `implementation.md` version vs package version, Package Inventory staleness, CLI Commands table accuracy, DB Tables vs migrations alignment, ROADMAP status column drift. |
| **Domain-Researcher** | 1-2 | Content-layer research (forum-coverage gaps per track, pricing/shop feature scope, roadmap extension proposals). |
| **Validator-CodeIntegrity** | 1 | Post-Builder integrity sweep: import graph, Click command tree, migration numbers + SCHEMA_VERSION sync, cli/hardware.py collision audit, AutoDetector signature, MockAdapter additive-only, pyproject.toml additions, seed data file presence, ruff clean, test collection. **REQUIRES Bash permission** — sandbox-denied Validator returns "UNABLE-TO-VERIFY." |
| **Validator-Regression** | 1 | Runs phase-specific tests + targeted regression sample. Reports per-phase pass/fail counts, SCHEMA_VERSION consistency, expected-vs-actual test count delta. **REQUIRES Bash permission.** |
| **Audit-Agent** (batch) | 2-4 | End-of-wave quality sweep over completed phase ranges (e.g., 01-50, 51-100, 101-121, 122-140). Rates each phase against the v1.1 template, flags stub/truncated docs, reports top-5 quality issues per range. |

### Wave dispatch pattern

1. **Wave A — Plans** (Planners parallel). At start of an auto-iterate batch, spawn one Planner per upcoming phase. Returns v1.0 plans inline; Architect persists to `docs/phases/in_progress/NNN_*.md`.
2. **Wave B — Architect Reviews** (Architect-Reviewer + Architect-Auditor parallel, while Wave A plans land). Reviewer catches cross-plan conflicts BEFORE Builders dispatch; Auditor catches doc drift.
3. **Wave C — Builders** (2-4 parallel). File-overlap-analyzed — phases adding new isolated files (`hardware/sensors.py`, `hardware/simulator.py`) can parallelize; phases editing `cli/main.py` or `migrations.py` serialize via wave ordering.
4. **Wave D — Validators** (Validator-CodeIntegrity + Validator-Regression in parallel, AFTER all Builders report). **BOTH REQUIRED per peak-efficiency mode — user explicitly requested this.** Verdicts: GREEN (commit) / YELLOW (commit with noted fixes) / RED (stop + fix).
5. **Wave E — Finalizers** (sequential git commits, one per phase). Serialize to avoid merge conflicts on `implementation.md` + `phase_log.md`.
6. **Wave F — Audit-Agents** (2-4 parallel, end-of-wave or end-of-session). Sweep completed-phase documentation quality.

### Bug-fix logging discipline (peak-efficiency hard rule)

When the Architect fixes a bug surfaced by Validator / trust-but-verify:
1. **Log the fix in the affected phase's `phase_log.md`** under a dated entry (`### YYYY-MM-DD HH:MM — Bug fix #N: <short title>`) with: Issue (failure mode), Root cause, Fix (what changed + why), Files (paths + line ranges), Verified (test command + result).
2. **Do NOT squash bug-fix commits into the Builder commit.** Each fix is its own commit referencing the phase. Commit message format: `Phase NNN fix #N: <short title>` with body explaining root cause + files.
3. **If >2 bugs in a single Builder's output, STOP and re-dispatch a Builder-Fix agent** with the cluster documented in the phase_log — don't Whac-a-Mole fixes for an hour.

### Shared-file serialization rules (Track E learning, formalized)

Shared files across parallel Builders must be handled explicitly:

- **`cli/hardware.py` / equivalent CLI module** — each phase adds a new `register_<subgroup>(parent_group)` function + ONE LINE call inside `register_<parent>`'s body. Builders must NOT refactor existing subcommand bodies. Pre-flight check: `git diff` shows additions-only.
- **`core/migrations.py`** — each migration takes a unique version number. Before Builder writes migration N, Architect verifies current highest is N-1. If a concurrent Builder is also writing a migration, serialize (dispatch sequentially, not parallel).
- **`core/database.py` `SCHEMA_VERSION`** — only one Builder per wave bumps the constant. Typically the highest-numbered migration's Builder does the bump.
- **`hardware/mock.py` / `hardware/ecu_detect.py`** — additive kwargs only. Each new kwarg at END of signature. Multiple Builders adding kwargs must pre-agree ordering (Architect-Reviewer catches collisions).
- **`implementation.md` + `phase_log.md`** — Architect owns. Never delegate to agents; serialize all writes.

### Validator return-format contract

Each Validator reports in ≤400-500 words with **per-check PASS / WARN / FAIL + specifics**, ending with **overall verdict: GREEN / YELLOW / RED**. A RED verdict blocks commit; YELLOW ships with noted fixes tracked in phase_log; GREEN commits immediately.

### Version-bump cadence (track progress)

When the user requests "iterate the version" or after each significant Builder wave lands:
- Bump `implementation.md` version (0.0.X → 0.0.X+1; at X=9, roll to 0.1.0).
- Document the bump in `phase_log.md` alongside the wave summary.
- `pyproject.toml` + `src/<project>/__init__.py` versions track package releases (bumped at Gate milestones), separate from doc version.

### End-of-wave audit discipline (2-4 Audit-Agents in parallel)

When the user requests "audit all completed phases" / "verify nothing's broken across the range" / after a Gate closes, dispatch 2-4 Audit-Agents partitioned by phase range (e.g., 01-50, 51-100, 101-121, 122-140). Each Audit-Agent rates every phase in its range against the v1.1 template + flags stub/truncated docs + returns top-5 quality issues per range. Architect consolidates into a prioritized backfill list.

### Honest limits of peak-efficiency mode

- **Bash-denied sub-agents cannot validate.** Validators that need `pytest` / `ruff` / Python execution fail cleanly with "UNABLE-TO-VERIFY" when sandbox blocks shells. Architect runs those steps directly in the main session.
- **Context pressure is the real ceiling.** At 8-10 concurrent agents + their return transcripts, the parent Architect's context fills fast. Pace dispatch so completion notifications arrive in manageable batches.
- **User interrupts override pool discipline.** If the user asks a direct question mid-wave, answer it before processing agent returns. Peak efficiency serves the user; it does not preempt user communication.
- **Do not dispatch more agents just to "fill slots."** Each agent must have a genuine non-overlapping task. Idle or redundant agents waste priming tokens.

### Entry condition

Peak-efficiency mode engages when the user says any of:
- "8 agents" / "10 agents" / "all agents in parallel" / "peak efficiency" / "2 of each role"
- "deploy more builders" / "need more X agents"
- "validate at the end" / "audit everything"
- "make the pool fuller" / "max out the pool"

Exit condition: user says "slow down" / "back to sequential" / "one phase at a time" / "just fix this one thing."

---

