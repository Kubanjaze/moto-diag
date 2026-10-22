# MotoDiag Fleet Proposal

2026-10-22 · Kerwyn Medrano (operator) with the Claude advisor session. Living copy with diagrams: https://claude.ai/artifact/BPfbhJcsNDGnbedFqxmNNC

## Purpose

Run MotoDiag phases as a fleet that calls Kerwyn only for the five things CLAUDE.md rule 1 already reserves for the operator, plus the handful of things no agent can physically do. Fable decides, Opus builds, and three staff officers absorb the approvals and the relaying that make Kerwyn the bottleneck today. Everything runs on the machinery the repo already has: the sandboxed `orchestrate.py` pattern from Phase 257, the push and edit guards, `verify_phase.sh`, the handoff files, and the desktop's fixed-button door from Phase 384.

This revision is grounded in the record rather than in the first sketch: the Sept 24–25 GLM builder experiment (`docs/reports/2026-09-25_glm_builder_findings.md`), the Sept 28 orchestrator design session, the Oct 15–21 desktop migration (382–384), CLAUDE.md as of the 2026-10-20 change log, and the plan of record of 2026-10-12. Nothing in the repo was changed.

## What the record shows

The rework Kerwyn had to do came from being the message bus between sessions and machines, not from agent code. The pipeline itself is already strong: 11,000 tests, 14 verify checks, two guards that fail closed, and every phase since 255D closing with a handoff.

| Date | What went wrong | Who caused it | What it cost |
| --- | --- | --- | --- |
| 2026-09-22 | A long prompt meant for the main session was pasted into the GLM terminal; GLM in auto mode acted on it in the real repo and removed the trial worktree | relay | branch cleanup, a 30-minute forensic pass |
| 2026-09-24 | GLM wandered outside its worktree; an instruction to stay inside was not a boundary | agent, unfenced | Phase 257 gained the sandbox-exec hard requirement |
| 2026-09-24/25 | GLM phases 258–260 each needed 2–3 full regressions before merge: integration defects in conventions it had not run | agent, wrong tests | roughly the Opus cost of an Opus-built phase in 259 |
| 2026-10-08 | The Mac hibernated mid-phase | hardware | Phase 382 moved live to the always-on desktop |
| 2026-10-15/19 | Every deploy step on the desktop was carried by hand between two computers; chopped heredocs, `<` eaten by the terminal, a stray file named `witch phase-384 &&` | relay | Phase 384 built the door so the Mac runs the PC's steps |
| 2026-10-19 | Phase 382's M7 results pasted into the 383 builder; 382 and 383 close-outs nearly collided on the same live DB | relay | a state note had to be hand-written into both sessions |
| 2026-10-21 | The app re-registered a push token during 384's verify, so check 8 failed on a column no gate names | process gap | F212, Phase 385 |

What already exists and the fleet must reuse rather than rebuild:

- **A sandboxed, budgeted, two-route stage runner:** `.claude/skills/source-transmission/orchestrate.py` runs each model stage as `claude -p` in a fresh `git clone --no-hardlinks` under macOS `sandbox-exec`, with an explicit `--model`, a per-call dollar cap, token stops per stage, and guards that refuse a credential sent to the wrong host. `tests/test_phase257_sandbox_boundary.py` proves the fence with planted writes.
- **Hard gates as hooks, not prose:** `pre_push_guard.sh` and `edit_guard.sh` in `.claude/settings.json` (PreToolUse on Bash). The push guard runs `roadmap_check.py` R1–R7 and `wholetree.sh` on every push and the eight close-out artefacts on a push to master.
- **A close-out that a script can judge:** `closeout_check.py` A1–A8, `verify_phase.sh` (14 checks), `regression.sh` (parallel, prints the line of record), `refute_check.py` C1–C7, `finding_check.py` B1–B2.
- **An inter-session channel:** `docs/handoffs/YYYY-MM-DD_<phase>_closed.md`, required by R6, read first by every new session.
- **A fixed-button door to the desktop (Phase 384):** `ops/desktop/motodiag_remote.py`, forced-command SSH over the tailnet, operations limited to status, dryrun, apply-live, verify-live, backup, api-start/stop/restart, server-pull. Anything else exits 64.
- **A written division of labour (rule 2):** bulk reading on GLM via Subconscious, judgement on Opus, every entry recording its `source_route`.
- **A precedent log in the operator's own words:** `docs/reports/2026-10-12_plan_of_record.md` quotes each decision with its date.

What the record says about the models: GLM-5.3 built a phase to “ready to merge” in 38–44 minutes with accurate document work and no content errors, but every phase needed integration fixes; the review halved its Opus cost only when it ran in a fresh, small-context session (260 vs 259). The Subconscious Base plan allowed about two GLM phases a day and **cancels on 2026-10-23** (K11, still undecided).

## Chain of command

```
Fleet Admiral — Kerwyn            (rule-1 stops, ROADMAP, the hands-only queue)
  │ delegates, by written rules
  ├── Executive Officer (Fable, fresh)   approves plans by checklist
  ├── Quartermaster (Opus, not builder)  runs the 14 checks; merges
  └── Yeoman (Haiku)                     decisions log, daily digest
  │ missions
  ▼
Captain — Fable                   step 0 verdict, plan v1.0, merge call; never pushes code
  ├── research tasking ──► Science Officer (GLM via subc, or Haiku): census, sourcing, Step 0 grep
  └── locked plan v1.0 ─► Chief Engineer — Opus: builds in a clone; regression, v1.1, handoff, PR
                              └── PR ──► Red Team (fresh Opus, or 2nd vendor): /refute, F9, A1–A8 diff
```

The staff row is what takes Kerwyn out of the loop. Today the operator does three jobs that are really rule-following, not judgement: approving a v1.0 that already passes the written checks, merging a phase that already passes `verify_phase.sh`, and answering builders' questions whose answer is already in the plan of record. Each gets an officer who applies the written rule and escalates only the cases the rule does not cover.

The Captain is the existing advisor role (the Opus session that wrote `257_step0.md` and the plan of record) moved to Fable and run as fresh `claude -p` calls rather than one long session: the GLM report measured a 2.4× cost difference between a review in a long advisor session and the same review in a fresh one. The Science Officer is rule 2's GLM-via-Subconscious role, with `--source-route anthropic` (Haiku) as the fallback the orchestrator already supports. The Red Team is a refute pass by a model that did not build the phase; the record shows GLM's own numbers could not be trusted until Opus re-ran them, so this seat is never the builder.

## Standing orders

Every boundary below is held by something that already fails closed, not by prompt wording: the edit guard, the push guard, the sandbox profile, `deploy.py`'s exit 4, and the desktop door's exit 64.

| Rank | Model | May do | May never do | Held by |
| --- | --- | --- | --- | --- |
| Fleet Admiral (Kerwyn) | — | Grant a rule-1 stop in his own words; pick a real fork; change a threshold or a rule; reorder the plan of record; edit CLAUDE.md; approve a live apply that alters or deletes rows; override any officer | Delegate a rule-1 approval (CLAUDE.md, 2026-09-25: an agent never grants itself one) | Rule 1 text; `deploy.py apply-live` refuses without the committed diff |
| Executive Officer | Fable, fresh `claude -p` | Read a v1.0 and its step-0 report; flip `plan:approved` when every item on the plan checklist passes; otherwise send it back to the Captain with the failed items (two rounds at most); only a plan that passes the checklist but carries a risk the checklist does not cover reaches the Admiral, as a 3-line recommendation | Edit the plan; approve a reshape; approve anything on the rule-1 list | `claude -p` with only Read, Grep and Glob allowed, no Bash; the dispatcher flips the label from the parsed verdict, never the model; the checklist is a script (`plan_check.py`, to be written) with a known-bad fixture; its own GitHub identity: issues write, contents read |
| Quartermaster | Opus, fresh `claude -p`, never the builder's session | Run `regression.sh`, `wholetree.sh --full`, `verify_phase.sh`; confirm claimed commits in `git log`; diff v1.0 against v1.1 for stubs; merge to master and run `/closeout`'s tail when all 14 checks pass and the Red Team is clear | Merge with any red; merge a phase whose live apply is unapproved; loosen a guard | The push guard (A1–A8, R1–R7) runs on its push exactly as on Kerwyn's; its own identity is the only non-admin one allowed to merge, with no bypass |
| Yeoman | Haiku | Answer a builder's blocking question by K-id from `docs/decisions.md`; append the Admiral's new decisions as one line each: K-id, date, his words verbatim, the check it became; write the daily digest; file the hands-only queue | Invent a decision; answer a rule-1 question | claude -p with only Read, Grep and Glob, no Bash; a question with no precedent is escalated verbatim; the digest pulls the activity log by time window, never through a capped search; its own identity: issues write, contents read |
| Captain | Fable, fresh `claude -p` per call | Classify step 0 (greenfield / extension / reshape); write v1.0 (all sections) and push the plan commit on `phase-NNN`; write the merge recommendation after the Red Team clear; stop a phase | Push code; merge; change ROADMAP or CLAUDE.md | Branch protection on master; its own identity may push phase-\* branches only, never admin |
| Chief Engineer | Opus | Build v1.0 in a fresh clone on `phase-NNN`; small diffs; `wholetree.sh` before every commit; the regression of record; v1.1 + Results + Deviations; dated phase\_log entries; the handoff; open the PR | Re-plan; touch raw datasets, seeds, splits, eval protocols, `migrations.py` without a `--full` record; a third bug fix without stopping | Edit guard, push guard, `COLLECTED_TEST_FLOOR`, the sandbox profile |
| Science Officer | GLM-5.3 via `subc`, or Haiku | Census, candidates, acquisition from the on-disk library, extraction, first-pass classification; the Step 0 overlap grep; write `NNN_step0.md` | Touch `src/`; call a live API without a logged dry run; write outside its clone | `sandbox-exec` profile proven by `test_phase257_sandbox_boundary.py`; no network tool |
| Red Team | Fresh Opus (second vendor later) | `/refute` every claim in the PR, max 3 rounds; the F9 checklist; A1–A8 against the docs; post findings on the PR | Push anything; approve its own fix | `refute_check.py` C1–C7; read-only clone |

Three rules sit above the table. **Rule 1 is unchanged**: the five stop conditions still reach the Admiral, and only the Admiral answers them. **Rule 5 is extended**: one writer per checkout becomes one writer per phase branch, and every rank works in its own clone, never in `~/Projects/moto-diag`. **Rule 8 of the workspace agreement (trust but verify) moves from Kerwyn to the Quartermaster** for the classes of phase the Admiral has written down; everything else still merges by hand until the Quartermaster has refused at least one planted bad PR (a v1.1 with a stub section, a missing handoff) and named the right check when it did; five matching verdicts on green phases prove nothing, because the base rate is green.

## The bridge

Git is the only channel, and the repo already has most of it: the phase branch, the ROADMAP row (🚧 before Step 0, per the ledger rule), the handoff file every close-out must write (R6), and `docs/prompts/` for the prompt that starts each session. What the fleet adds is a **label on a GitHub issue per phase** as the single state word, so that no session has to read another session's screen and Kerwyn never carries a paste between windows. The 382/383 collision on 2026-10-19 is the case this prevents: two phases on one live DB, each told the other's state by hand.

```
step0:open ─(Captain files v1.0)─► plan:needs-admiral* ─(Admiral/XO flips)─► plan:approved
     ▲                                     │ rejected, back to Captain
     └─────────────────────────────────────┘
plan:approved ─(Engineer, in a clone)─► build:open ─(PR opened)─► review:open ─(Red Team clear)─► merge:needs-admiral*
                                           ▲                          │ findings, back to the Engineer
                                           └──────────────────────────┘
merge:needs-admiral* ─(merge)─► merged, /closeout
* the two gates: the XO after step 2, the Quartermaster after step 8; the Admiral until then
```

The documents are the contract between ranks, in the shapes the repo already enforces:

- Science Officer → Captain: `docs/phases/in_progress/NNN_step0.md`, with every count showing the query that produced it (the 2026-09-28 rule: “measure what produced the number”).
- Captain → Engineer: `NNN_implementation.md` v1.0, all sections, the plan commit pushed first.
- Engineer → Red Team and Quartermaster: the PR, carrying v1.1 with Results and Deviations, the `### Bug fix #N` entries, the regression line that A5 parses, and `docs/handoffs/YYYY-MM-DD_NNN_closed.md`.
- Any rank → Admiral: a comment on the issue with the label `needs-admiral`, in plain English per rule 6, one paste block, ending ALL GOOD or SOMETHING IS OFF.

Two loops stay inside the fleet. A rejected plan goes back to the Captain with the XO's reasons; findings go back to the Engineer, up to the refute limit of three rounds, after which wording defects become one finding and factual defects mean the row does not ship (K9). A third bug fix in one build stops the Engineer and tags the Admiral: more than two bugs means a common root cause, not a third patch.

## Triggers and where the fleet runs

The fleet is a local dispatcher, not GitHub Actions. The repo has no CI, the regression needs the project's own machine (11,000 tests, 28 minutes, SQLite fsync-bound), the guards are PreToolUse hooks in `.claude/settings.json`, and CLAUDE.md imports `../workspace-docs/claude/working-rules.md` from outside the repo, which a cloud runner would not have. A GitHub label is still the state word, because `gh` can read and write it from any machine without a human relaying.

**The host is the desktop, from step 2.** It has been always-on since Phase 382, it holds live, and the Mac hibernated mid-phase on 2026-10-08. The Mac's remaining job is the deploy side of the 384 door; it never hosts the dispatcher again. One dispatcher process polls `gh issue list --label` every few minutes and launches the stage the label asks for; the label is the lock, so “never both writing at once” is a property of one process on one host, not a policy. A stage is `orchestrate.py`'s pattern lifted one level: one `claude -p` call, an explicit `--model`, a dollar cap, a token stop, and the model's text never acted on unchecked. The read-only seats (XO, Yeoman) run with only Read, Grep and Glob allowed and no Bash, so they need no fence and can start on the desktop today; the dispatcher flips the label from the parsed verdict.

**Always-on desktop is not always-on WSL2.** A systemd timer inside the distro fires only while the VM is up, and WSL stops the VM shortly after the last process exits unless something holds it. Phase 382 already solved this once for the API: `ops/desktop/motodiag-wsl-boot.xml` is a Windows Task Scheduler job that starts WSL at boot. The dispatcher goes in the same way, a scheduled task running `wsl.exe -- <dispatcher>` at startup, which survives Windows Update reboots. Before relying on either: `systemctl is-system-running` in the distro, and find what holds the VM open today; if it is the 384 door's sshd, a WSL restart kills the timer and the door together.

| Label | Who runs | What runs | Fence |
| --- | --- | --- | --- |
| `mission` (Admiral opens the issue; the ROADMAP row goes 🚧) | Science Officer | Step 0: overlap grep, census, library acquisition, `NNN_step0.md` | fresh clone, no network tool, writes to `docs/` only |
| `step0:done` | Captain | v1.0 on `phase-NNN`, plan commit pushed | fresh clone, push guard refuses master |
| `plan:needs-review` | Executive Officer | `plan_check.py`; flips `plan:approved` or files `needs-admiral` | read-only clone |
| `plan:approved` | Chief Engineer | the build, `wholetree.sh` per commit, the regression of record, v1.1, the handoff, the PR | fresh clone; edit guard; push guard; `COLLECTED_TEST_FLOOR` |
| `review:open` (PR opened) | Red Team | `/refute` and the A1–A8 diff; posts on the PR | read-only clone |
| `review:clear` | Captain | merge recommendation, 3 lines, on the PR | read-only clone |
| `merge:needs-review` | Quartermaster | `verify_phase.sh`, commits exist, no stubs; merges; `/closeout` tail; label `merged` | the same push guard as Kerwyn's |
| any label older than 24 h, or `needs-admiral` | Yeoman | one digest to Kerwyn: escalations, the hands-only queue, nothing else | read-only |

**The fence on Linux is the gate for every seat that writes or runs scripts** (Captain, Engineer, Red Team, Quartermaster). Phase 257's boundary is macOS `sandbox-exec` with a profile that allows writes only inside the clone, proven by planted writes that fail. The desktop runs WSL2, where `sandbox-exec` does not exist. The candidates are a Linux user namespace (bubblewrap) or the repo's `Dockerfile` with a read-only bind of everything but the clone; `unshare -Ur true` in the distro decides between them before anything is built. The proof is 257's plus one: eight planted writes outside the clone refused, a push to master rejected, the control run outside the fence succeeding, and a **ninth case, the `../workspace-docs` import resolving**: a fenced clone that cannot see `workspace-docs` passes all eight write tests and runs with no workspace rules, which the 2026-09-23 NOT LOADED proof already showed.

**One identity per seat.** Each rank gets its own GitHub token with the least it needs: XO and Yeoman, issues write and contents read; Captain and Engineer, push to `phase-*` branches; Quartermaster, merge. Nothing push-capable is admin, and the spend ceiling is per identity, so the digest can show who spent what. A fine-grained PAT on Kerwyn's account is still Kerwyn, still admin, still a bypass; the fleet's identity is a GitHub App or a machine user added as a write collaborator, with no bypass on master.

## Keeping the Admiral out of the loop

Kerwyn's irreducible list is already written down; the fleet only has to stop asking him for everything else. From rule 1 and the record, the things only he can do:

| Only the Admiral | Why it cannot be delegated | How it reaches him |
| --- | --- | --- |
| A real fork: two plans that ship different things | Rule 1; every serious miss of 2026-09-22–28 was an agent choosing on its own | Captain writes both options in 3 lines each; XO files `needs-admiral` |
| A change to a threshold or a rule's definition | Rule 1 | Yeoman's digest; the answer is quoted into CLAUDE.md's change log |
| A live-DB change that alters or deletes rows | Rule 1; `deploy.py apply-live` refuses without the committed, approved diff | Quartermaster commits the dry-run diff and files `needs-admiral`; the approval is Kerwyn's scoped wording, applied literally |
| A login, a credential, an account | Rule 1; Stripe (273), Subconscious, Tailscale approvals, the offsite backup and Sentry accounts for 345 and 343 | the hands-only queue |
| A physical device or machine | iPhone smoke tests, the USB cutover in 382, a sleeping Mac, a desktop that needs a signed-in user | the hands-only queue |
| Maker portals that block automation | 257's Step 0 fetched 0 of 10 portals; downloads go into `~/research/motodiag/inbox/` by hand | the hands-only queue, with the exact file-naming convention |
| Reordering the plan of record; editing CLAUDE.md | The Admiral's own words are the precedent log | by hand, dated, quoted |

Everything else is routed by three mechanisms:

1. **Written rules of engagement instead of per-item approval.** The XO's `plan_check.py` and the Quartermaster's merge conditions are scripts with known-bad fixtures, the same standard every skill in `.claude/skills/` already meets. A phase that passes them proceeds; the Admiral reads about it in the digest. The first version of the plan checklist is short: a ROADMAP row exists and is 🚧; `NNN_step0.md` exists and every count shows its query; the step-0 classification is greenfield or extension (a reshape escalates); no path under `data/`, no seed, split or eval protocol is touched; every v1.0 section is filled; the plan cites the last three CLAUDE.md change-log entries as checks it will pass; the stop conditions it anticipates are listed.
2. **A hands-only queue, not interrupts.** A rank may file `needs-hands` only after it has proved it cannot do the thing itself: a logged 403, an exit 4, a missing credential. Every item carries which computer and which window, one paste block ending ALL GOOD or SOMETHING IS OFF (rule 6), and a check the rank runs after Kerwyn reports back, so a slip on his side is caught by the agent that asked, not found three phases later. The queue is worked once a day, in one sitting.
3. **Every correction becomes a check.** This is already the project's habit: K1–K9, K18, K23, the edit guard after two `sed -i` violations, F183's `finally` fix after two lost regressions. The fleet makes it a gate: no `plan:approved` for a phase whose Step 0 does not cite the three newest change-log entries and the guard each one became.

The measure of success is the count of `needs-admiral` and `needs-hands` items per phase, recorded in the digest. The record from 373 to 384 is roughly five interventions per phase; the target after five fleet phases is one.

## Guardrails

Nothing new is needed except the fence on Linux, a plan checklist, and branch protection. Everything else exists and fails closed; the fleet changes who runs it, from Kerwyn's memory to a script that reads an exit code.

| Guardrail | Rule | Held by today | What the fleet adds |
| --- | --- | --- | --- |
| Agents cannot write outside their clone or push to master | CLAUDE.md rule 2 | `sandbox-exec` profile from 257; `test_phase257_sandbox_boundary.py`; the push guard | the same proof on the desktop's Linux fence, plus the workspace-docs case; branch protection on master through a ruleset (free on a public repo, which moto-diag is), with the fleet's own identities and no bypass. This is the only lock that holds regardless of who ran what: the push guard is a Claude Code PreToolUse hook, so it fires on git push inside the tool loop and nowhere else; gh pr merge is a server-side call, a terminal is not the tool loop, and the 2026-09-22 incident was a different tool entirely. Extend the guard's match to gh pr merge as well; and the step that answers this doc's own objection to Actions is a self-hosted runner on the desktop that makes verify\_phase.sh a required status check on PRs to master, so the checks are enforced at merge time rather than one step before it |
| One writer per checkout | rule 5 | text only | every rank in its own clone, enforced by the dispatcher, not by instruction |
| No edits to `src/` or `tests/` through shell commands | rule 6 | `edit_guard.sh`, fails closed | unchanged |
| Whole-tree checks before every commit; `--full` before the regression of record and in content phases | rule 3 | `wholetree.sh`; `regression.sh` refuses to start without a `--full` record; the push guard | unchanged |
| ROADMAP row before Step 0; never a reused number; a handoff per close | the ledger rule; R1–R7 | `roadmap_check.py` in every suite and on every push | the dispatcher refuses a `mission` whose row is missing |
| Close-out complete before a push to master | A1–A8 | `closeout_check.py` via the push guard | the Quartermaster reads its exit code; the Admiral reads the digest |
| Live apply only from the branch, after the regression, before the close-out commit, with an approved diff | rule 4, K18 | `deploy.py apply-live` refuses otherwise | the approval text is Kerwyn's scoped wording, pasted verbatim by the Yeoman, never paraphrased |
| No test reads the live DB; no schema head pinned | 244H, F124 | tests | unchanged |
| Refute stops at three rounds; wording defects become one finding; factual defects mean no ship | K9 | `refute_check.py` C5–C7 | the Red Team runs it, never the builder |
| More than two bug fixes means a root-cause stop | workspace rule 5 | prompt text | the Engineer counts `### Bug fix #N` entries and stops at 3 |
| Credentials never enter the repo or the wrong route | 257 D3 | `orchestrate.py` guards; the `sk-ant-` / `sk-gw-` pre-commit check; the dispatcher's environment carries a setup-token and no ANTHROPIC\_API\_KEY, which would bill API rates silently | unchanged |
| A stage without recorded token usage is a stop | 257 | `orchestrate.py` `token_stop` | the same rule for every fleet stage |

One rule the fleet needs that nothing holds today: **a run that cannot finish its stage leaves the label where it found it and comments why.** A half-moved label is worse than a stalled one, because the next rank starts on a state that is not true.

## Cost model and model choice

Fable touches a phase four times and never runs a tool loop; Opus runs the loops; the cheap model does the reading. The measured record sets the expectations, not guesses.

| Rank | Model | Calls per phase | Measured basis |
| --- | --- | --- | --- |
| Captain | Fable (`claude-fable-5-1`), fresh `claude -p` | 3: step-0 verdict, v1.0, merge recommendation | the 260 landing in a fresh Opus session cost about half the 259 landing in the long advisor session (23.1M vs 55.5M tokens read) |
| Executive Officer | Fable, fresh `claude -p` | 1 per plan, plus re-reviews | reads v1.0 and the step-0 report only, never the diff |
| Chief Engineer | Opus (`claude-opus-5-5`) | 1 long run plus fix cycles | Opus-built 353 and 354: 269 and 330 calls, 44.5M and 61.5M read, 1.9–3.1 h wall |
| Quartermaster | Opus, fresh | 1 per merge | mostly scripts; the model only reads exit codes and diffs |
| Science Officer | GLM-5.3 Marathon via `subc`, else Haiku (`claude-haiku-5-5`) via `--source-route anthropic` | 1 per mission | GLM: 38–44 min to ready-to-merge, 167–185 model calls; the source stage is now one turn with no tools, 150K tokens per spelling cap |
| Red Team | Fresh Opus | 1 per PR, up to 3 rounds | 353's four refuter agents are the ceiling; cap stays at 6 agents |
| Yeoman | Haiku | 1 per day plus per question | the Pieces clone already runs its rollups on Haiku |

**K11 is due tomorrow, 2026-10-23.** The Subconscious Base plan gives about two GLM phases a day and cancels then. The record's verdict: GLM pays only when it runs the full suite itself, every trap is named in the prompt, the review is a fresh small-context session, and the suite is fast; the last three are now true. The Science Officer seat is the only one that needs it, and the orchestrator already falls back to `--source-route anthropic`. Renew if the sourcing backlog (about 600 machines with no manual on disk) will run in the next month; otherwise let it lapse and run the Science Officer on Haiku, which keeps every guard and loses only the price.

**The fleet runs on the Max subscription, not the API** (decided 2026-10-22, 14:20). At list rates a 354-sized build is roughly $40–60 on the API with a normal cache-hit rate, and a whole phase with fix cycles, a fresh-Opus Red Team and four Fable calls about $100; at the 373→384 pace of about six phases a week that is $500+ a week against $100–200 a month for Max. The exact figure comes from the Claude Code session logs for 353 and 354, which hold the input, cache and output split; that measurement is part of the records phase, not an estimate in this document. `claude -p` is Claude Code, so subscription auth is in bounds; the Agent SDK, Subconscious and any Python of the fleet's own are not, and stay on a key.

**What quietly puts the fleet on the API anyway.** If `ANTHROPIC_API_KEY` is set in the environment, Claude Code bills API rates regardless of the login. `orchestrate.py`'s Opus route runs on a key today (`BUDGET_USD`, the `sk-ant-` guard), so a dispatcher that inherits that environment is on the API from its first call. The dispatcher gets a `claude setup-token` OAuth token and no key; the key lives only in the one stage that needs it. Kerwyn also has a Console org, and a Max subscriber with a Console org has reported print mode billing API rates despite the OAuth login. So the first unattended stage is a Haiku one-liner, after which Settings › Usage on claude.ai should move and Console billing should not; rule 8 applied to billing, before the Engineer is ever launched. `/fast` stays out of the fleet.

**Built for the limits, not for dollars.** Two limits need headroom: the rolling 5-hour window and the weekly caps (all-model plus model-specific; `/usage` shows both and the reset time). The pool is shared with Kerwyn's own sessions, so an Engineer run can starve his Thursday. The rules:

- The dispatcher launches no new Opus stage above about 70% of the weekly cap, and launches Opus builds at the top of a fresh 5-hour window; a 2–3 h build with 300 calls is the only stage that collides with the window.
- Every stage is resumable: the session id is captured from `--output-format json`; a rate-limit exit leaves the label where it was, comments the reset time, and the dispatcher relaunches with `--resume` after the reset.
- The dollar cap is Anthropic's, not the dispatcher's: usage credits are prepaid, bill at API rates, carry a monthly cap, and can be disabled. Off means a hard stop at the subscription; on with a small cap means bounded overflow. The per-stage token stop stays; `BUDGET_USD` is dead weight on the subscription route.
- Cheap seats stay on Haiku: Yeoman, and the Science Officer fallback.
- If the cap binds on Max 5×, 20× is the lever before extra usage.

**Phases per week is measured, not read off the published limits**, which are quoted in hours and have moved more than once this year: one Engineer-class phase on the subscription, weekly percentage in `/usage` before and after. If one phase is 20% of the weekly cap, the fleet runs five a week on the plan and anything past that is about $100 a phase in credits. That number goes in the records phase beside the auth decision.

## Debt the sweep found

These are stale records an unattended fleet would read as true. They should close before any rank runs unattended, and each is a docs-only phase or a change-log entry, not new machinery.

| Where | What is stale | Why it matters to the fleet |
| --- | --- | --- |
| `phase_log.md` (root) | Last entry is Phase 255B, closed 2026-09-22; nothing since | A rank told to read the project log reads a month-old state |
| `implementation.md` line 6 | Still carries a Windows `Local:` path; doc version 0.13.112 vs `pyproject` 0.6.0 | The version split is noted in the file but a script reading either number gets a different answer |
| `docs/contributing.md` | Says `pytest -q` takes about 9 minutes; the suite is 11,000 tests and 28 minutes | A new rank would budget the wrong wall-clock |
| `README.md` | Still says a skill added mid-session is unavailable; removed from CLAUDE.md on 2026-09-27 | Noted in that change-log entry as outside the approved change; still open |
| `CLAUDE.md` | Imports `@../workspace-docs/claude/working-rules.md`, not in this repo; the F9 taxonomy lives in `docs/patterns/`, not in the rules | A clone on the desktop or any runner without `workspace-docs` beside it loads no workspace rules; the 2026-09-23 proof showed a headless session answered NOT LOADED before the import |
| `docs/FOLLOWUPS.md` | F132, F133, F134 found marked MISSING on 2026-10-07 | `finding_check.py` B2 should catch a cited number that does not resolve; confirm it does |
| Phase 359 | Migration 072's live apply is still not confirmed in any record read | Either it landed and the record is silent, or F159/F163/F166 are still open |
| K11 | The Subconscious decision is in the plan of record's operator list, due 2026-10-23 | Decides the Science Officer's model |

None of this is created by the fleet; all of it is what the fleet would trip over. The first fleet phase is a records phase that closes the table above, so the Yeoman's first digest is built on a true ledger.

## Rollout

One rank per phase, each under the discipline it will enforce: its own ROADMAP row, Step 0, v1.0, regression, handoff. Nothing runs unattended until the fence is proven on the machine it runs on. Phase numbers below are placeholders; the ledger assigns the real ones.

1. **Records phase (docs only).** Close the debt table: root `phase_log.md`, `implementation.md` line 6, `contributing.md`, `README.md`, the MISSING findings, 359's status. Let K11 lapse (verdict below). Create the fleet's GitHub identities and the master ruleset. Pull 353's and 354's token split from the session logs, log the dispatcher in on a setup-token with no API key in its environment, run the Haiku billing check, and measure one phase's share of the weekly cap. Zero risk to `src/`.
2. **The XO on Phase 385, on the desktop.** 385 is small (one column, `device_tokens.last_seen_at`, closes F212) and its prompt is already in `docs/prompts/`. Write `plan_check.py` with a known-bad fixture, run the XO as a read-only `claude -p` on 385's v1.0, and compare its verdict with Kerwyn's. Kerwyn still approves and merges. The grade: would he have approved what it approved, and did a planted bad plan get sent back.
3. **The Yeoman, on the desktop.** `docs/decisions.md` seeded from the plan of record's quoted operator words as K-ids; the daily digest pulled by time window from the activity log; the `needs-hands` and `needs-admiral` labels. Read-only, no fence needed.
4. **The dispatcher's host.** `systemctl is-system-running`, what holds the VM open, the startup task beside `motodiag-wsl-boot.xml`, `unshare -Ur true`. No writing seat runs until this is done.
5. **The fence on Linux.** bubblewrap or the `Dockerfile`; nine planted cases, including the `workspace-docs` import; the control run outside the fence succeeding.
6. **The Captain and the Engineer on one Wave 1 phase.** 303 or 348 (roles, audit log) need nothing outside the code. Fable writes v1.0, the XO reviews it, Opus builds in a fenced clone under its own identity, Kerwyn merges by hand. Grade by regression count, bug-fix count, and whether v1.1's Deviations match the diff.
7. **The Red Team.** A fresh Opus refute on that PR, with the A1–A8 diff. Compare its findings with what the regression and Kerwyn found.
8. **The Quartermaster, in shadow.** It runs `verify_phase.sh` and writes its merge verdict to the digest while Kerwyn still merges. Promote it only after it has refused at least one planted bad PR and named the right check, and record the rule-8 change in both CLAUDE.md files with the date. Whoever merges closes the mission issue through the same `/closeout` tail: Kerwyn during shadow, the Quartermaster after.
9. **The dispatcher end to end**, with the self-hosted runner making `verify_phase.sh` a required check on master, and one full phase with Kerwyn only answering the digest.

Do not skip to step 9. Each step is a phase with its own implementation.md, and the fleet is built the way it will build.

## Decisions taken, 2026-10-22

The Admiral's verdicts on the open list, and where each landed in this document. The auth question was answered at 14:20: the subscription. Nothing on the list is open.

| Decision | Verdict | Where it landed |
| --- | --- | --- |
| K11, Subconscious | Let it lapse. Nothing before the dispatcher step exercises the Science Officer and the sourcing backlog is not scheduled; re-subscribe the week sourcing goes on the roadmap. Only a cancellation penalty or a lost rate flips this | Cost model; rollout step 1 |
| Where the fleet runs first | Desktop from step 2. XO and Yeoman are read-only and need no fence; the Mac is deploy-side only and never hosts the dispatcher again; the label is the lock | Triggers; standing orders |
| Quartermaster scope | Extension or greenfield, no migration, no `data/`, no live apply. Promotion requires refusing a planted bad PR and naming the check; five green matches prove nothing | Standing orders; rollout step 8 |
| Branch protection | Yes, as a ruleset with the fleet's own identities and no bypass. The push guard is a hook and fires only inside the tool loop; branch protection is the lock that holds regardless; extend the guard to `gh pr merge`; a self-hosted runner makes `verify_phase.sh` a required check | Guardrails; triggers |
| XO: veto or recommendation | Neither. Checklist failures go back to the Captain, two rounds max; only a passing plan with an uncovered risk reaches the Admiral, as a recommendation. The earlier contradiction between standing orders and the bridge is resolved in favour of the bridge | Standing orders |
| Per-run cap | Resolved by the auth decision: the fleet runs on the Max subscription; the cap is Anthropic's usage-credit cap (off = hard stop), the dispatcher holds 70% weekly headroom and makes every stage resumable; the first unattended stage is a Haiku billing check; phases per week is measured in the records phase. **Subscription, 14:20** | Cost model |
| `decisions.md` | New file, but K-ids, not a third numbering scheme: K-id, date, the words verbatim, the check it became; `finding_check`'s B2 habit applies to cited K-ids | Standing orders (Yeoman); rollout step 3 |
| Who closes the issue | Whoever merged, through the same `/closeout` tail | Rollout step 8 |
| The activity log | Not a gap: 22 rollups since Oct 18; the 30-result search was sorted by relevance. The Yeoman pulls by time window, never through a capped search | Standing orders (Yeoman) |
| Not on the list | Always-on desktop is not always-on WSL2 (startup task beside `motodiag-wsl-boot.xml`); a ninth fence case for the `workspace-docs` import; one identity per seat with least privilege | Triggers; rollout steps 4–5 |

## Sources

Repository `Kubanjaze/moto-diag` at `1e8230a` (master, 2026-10-21): `CLAUDE.md` (change log to 2026-10-20), `ROADMAP_AUTHORITY.md`, `docs/ROADMAP.md`, `docs/reports/2026-09-25_glm_builder_findings.md`, `docs/reports/2026-10-12_plan_of_record.md`, `docs/phases/completed/257_step0.md`, `docs/handoffs/2026-10-21_384_closed.md`, `.claude/skills/source-transmission/orchestrate.py`, `.claude/settings.json`, `ops/desktop/`. Chats: “Motodiag architecture decisions” (to 2026-09-28), “Mac to PC file transfer” (2026-10-15 to 10-21), “Mac diagnostic commands” (2026-10-15), “Missing phase\_log.md in moto-diag-mobile” (2026-08-21). Activity log: the local Pieces clone's workstream rollups, 2026-09-28 to 10-11. Claude Code docs: [headless](https://code.claude.com/docs/en/headless.md), [sub-agents](https://code.claude.com/docs/en/sub-agents.md), [adversarial review](https://code.claude.com/docs/en/best-practices.md).
