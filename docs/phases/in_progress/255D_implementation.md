# Phase 255D — Procedures as folders

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-22

> Step 0 is committed at [`255D_step0.md`](255D_step0.md) (`75f6634`) and is
> not re-run. This plan begins at "Decisions taken".

---

## Decisions taken

Six, from the operator on 2026-09-22, after Step 0 was reviewed.

| # | decision |
|---|---|
| 1 | Assertion is **hook AND test**. The test asserts closeout's artefacts; the hook is `PreToolUse` on `Bash(git push *)`, exit 2 when the test fails. The workspace-trust caveat is **documented in the repo README, not assumed**. |
| 2 | **First act of v1.0 is running the mechanism** — one trivial skill, shown triggering on a planted invocation, before any real skill is written. |
| 3 | Order: **closeout → finding → refute.** |
| 4 | **CLAUDE.md split, own commit.** Root keeps cross-project rules; `moto-diag/CLAUDE.md` gets moto-diag's; the 226 lines of agent-pool machinery move to a folder or are deleted — **measure which**; other projects' blocks move to their own files. Dated change-log entry in each file that changes. Root target: the ~174 load-bearing lines. |
| 5 | Every skill: **independent-reference positive control** (a known-bad fixture the assertion must fail on), a dated change log **in the skill's own folder**, and a **script** for anything that is "run this and check that". |
| 6 | `verify_phase.sh` from the supplied block, parameterised on `PHASE`, `REG_HASH`, `TIP`; the roadmap count method comes **from the CLAUDE.md rule, not a second implementation**. |

## D0. Decision 4's measurement, answered before the plan depends on it

Decision 4 says the 226 lines move or are deleted, and to **measure which**.
Measured over every completed phase document in the repository:

| machinery | phases citing it | most recent |
|---|---|---|
| `auto-iterate` | 6 | **168** |
| `Agent Pool` | 7 | **168** |
| `peak-efficiency` | 3 | **195C** (a passing mention) |
| `Builder-A` / the two-role pattern | 15 | **191D** |
| **`Spawn script`** (50 lines) | **0** | **never** |

Current work is 255D. The two-role pattern was last genuinely used **64
phases ago**; the agent pool **87 phases ago**; and the single largest block
in the section — the 50-line spawn script — **has never been cited by any
phase at all.**

Every hit found outside CLAUDE.md is a **record** — a completed phase log or
an `implementation.md` row describing a phase that *was* built that way.
**Not one is an invocation.** So under decision 4's own rule the answer is
"delete", not "move to a folder": a procedure folder for a procedure nobody
runs is the phantom filing again, in a new shape.

**Recommendation, flagged as the operator's call.** Delete the 226 lines
**from CLAUDE.md** and preserve them at
`docs/archive/auto-iterate-and-agent-pool.md` with a dated note naming the
phases that used them. Rationale: deletion from CLAUDE.md is the point —
nobody reads it there and it dominates the file — but destroying 226 lines
of written practice with fifteen phases of evidence behind it is
irreversible, and the phase logs reference it by name. Archiving costs one
file and keeps every reference resolvable. **If the operator prefers literal
deletion, git history holds it and this plan changes by one line.**

## D1. Run the mechanism first — nothing else is written until this passes

Per decision 2. Before `closeout` or any real content exists:

1. Create `.claude/skills/ping/SKILL.md` — a trivial skill whose entire body
   is an instruction to emit one fixed sentinel string.
2. Invoke it on a planted invocation and **show the sentinel in the
   output.**
3. Create `.claude/settings.json` with a `PreToolUse` hook matching `Bash`,
   `if: "Bash(git push *)"`, whose command is `exit 2` with a fixed message,
   and **show a `git push` being blocked by it.**
4. Remove the blocking hook; keep the skill until step 3 of D2 replaces it.

**Why this is step one and not a smoke test at the end.** Step 0 verified
only *absence* — that no skills, commands, agents or hooks exist on this
machine. Everything else it reports is documentation, cited but unexecuted.
**A plan built on an unrun mechanism is a plan built on a docstring**, which
is instance (b) on the CLAUDE.md list, added today. If the sentinel does not
appear, or the hook does not block, v1.0 stops here and the phase is
re-planned around whatever the mechanism actually does.

**Recorded failure mode to watch:** a skill is a *prompt*, not a script. A
passing step 2 proves the file was loaded and read, **not** that its
instructions will be followed under load. That is precisely why the
enforcement in D2 is a test and not the skill's own text.

## D2. `closeout` — the skill, the script, the test, the hook, the fixture

### D2.1 The skill

`.claude/skills/closeout/SKILL.md`, carrying the judgement: what a
close-out is for, what "done" means, when a step may be skipped and what
must be said if it is. Supporting files beside it, referenced through
`${CLAUDE_SKILL_DIR}`:

| file | what it is |
|---|---|
| `verify_phase.sh` | decision 6's script, below |
| `roadmap_words.py` | the **single** implementation of the 120-word count |
| `CHANGELOG.md` | decision 5's dated log, in the folder |
| `fixtures/` | the known-bad and known-good phase directories |

### D2.2 `verify_phase.sh`

Taken from the supplied block, parameterised on `PHASE`, `REG_HASH`, `TIP`,
with its ten numbered checks preserved in order and wording. **Two changes,
both forced by decisions already taken:**

1. **Check 6 is replaced.** The block counts the roadmap row with
   `awk '{print "tokens:", NF-1}'` — the whole row, pipes and title
   included. That is a **third** counting method, different from both of the
   two that were argued about, and it is the one that would have passed a
   122-word row. Decision 6 says one implementation, so check 6 calls
   `roadmap_words.py`.
2. **Check 5 is tightened** to match the register format 255C's log now
   uses: not merely that `bug fix #` appears, but that the numbering is
   contiguous from `#1` and each entry carries a `Commit.` line.

Everything else — the push/clean check, the no-code-after-the-hash diff, the
completed/in_progress listing, the stub grep, the findings header, the live
schema read, the backup listing, the targeted test run — is unchanged.

### D2.3 `roadmap_words.py` — one implementation, cited by the rule

The count method is defined in the workspace CLAUDE.md rule "ROADMAP rows
are an index, not the record": body cell only, whitespace-split with nothing
stripped, a markdown link is one word. **That rule currently embeds a
one-line command, which this phase makes a second implementation the moment
the script exists.**

So the rule changes in the same commit: it keeps the method **in words**
(the rule is the specification and must stay readable without running
anything) and replaces its inline one-liner with a **path to the script**.
Specification in the rule, implementation in the folder, exactly one of
each. Recorded here because it reverses a one-liner added earlier today.

### D2.4 The test — asserting artefacts, not that closeout ran

`tests/test_phase255D_closeout_contract.py`. For the phase named as current
it asserts:

| # | artefact |
|---|---|
| 1 | Both phase docs are in `docs/phases/completed/`, neither in `in_progress/` |
| 2 | The phase log's status line reads Complete |
| 3 | The implementation doc has a **Deviations** section |
| 4 | The phase log's bug fixes are a contiguous dated register from `#1`, each with a `Commit.` line |
| 5 | The log carries a regression line with **both** a commit hash and a collected count |
| 6 | A ROADMAP row exists for the phase and its **body cell** is ≤ 120 words by `roadmap_words.py` |
| 7 | `implementation.md` carries a row for the phase and its version is above the previous phase's |

Each is a file fact, and each is something a skipped close-out leaves
undone. **"Closeout ran" is deliberately not asserted** — it is
unfalsifiable from inside the suite, and a test that cannot fail is the
thing this phase exists to stop shipping.

### D2.5 The positive control — independent reference

Decision 5, sharpened by 255C into *independent reference*: the control must
be satisfied by something that does **not** reimplement the procedure.

`fixtures/phase_ZZZ_bad/` is a complete, fabricated phase directory with
seven planted defects, one per assertion — doc left in `in_progress/`,
status still In progress, no Deviations section, a bug-fix list numbered
`#1, #3`, a regression line with a count but no hash, a 130-word roadmap
row, no implementation.md row. `fixtures/phase_ZZZ_good/` is the same
directory corrected.

Two tests: **every assertion fails on the bad fixture, naming which**, and
**every assertion passes on the good one.** A fixture whose defects are
generated by the closeout script would prove nothing; these are written by
hand and committed.

### D2.6 The hook

`.claude/settings.json`:

```json
{ "hooks": { "PreToolUse": [ { "matcher": "Bash",
  "hooks": [ { "type": "command", "if": "Bash(git push *)",
               "command": ".claude/skills/closeout/pre_push_guard.sh" } ] } ] } }
```

`pre_push_guard.sh` runs the closeout test for the current phase and exits
2 on failure, which blocks the push and returns stderr to the model.

**The workspace-trust caveat goes in the repo README**, per decision 1, in
these terms: *a committed hook does not run until the workspace is trusted,
so a fresh clone gets no push guard; the test is the guarantee, the hook is
only the latency.* Documented rather than assumed, because **a hook that
silently does not run reads exactly like a hook that passed** — which is the
shape of every defect this project has spent a week on.

## D3. `finding` — second, because it is cheap and the evidence exists

`.claude/skills/finding/`. The evidence is **F135**: 255C's plan stated a
finding was "filed on the general-applicability ticket", and it was not —
the claim was written and the entry never created, caught at close-out by
looking for the ticket the plan cited.

* **Script:** `next_f_number.sh` — reads the highest assigned from
  `docs/FOLLOWUPS.md` *and* the mobile file, since F-numbers are one global
  sequence across both repositories, and prints the next.
* **Assertion:** `tests/test_phase255D_finding_contract.py` — the header's
  "highest assigned is **FNNN**" matches the highest entry actually present,
  and every `F` number referenced in a phase doc under `completed/` resolves
  to an entry that exists. **The second half is what F135 would have
  caught.**
* **Positive control:** a fixture pair — a FOLLOWUPS file whose header
  claims F140 while the last entry is F138, and a phase doc citing an F
  number with no entry. Both must fail; the corrected pair must pass.

## D4. `refute` — third, and honest about what it cannot assert

`.claude/skills/refute/`. Judgement-only markdown: how a refuter pass is
scoped, what a refuter is told, what counts as a killed claim, and the rule
that every cited page is fetched rather than remembered.

**It gets no runtime assertion, and the plan says so rather than inventing
one.** What it gets instead, per the operator's framing, is a **checklist it
must emit**: a refuter pass ends by printing a fixed-shape block — claims
examined, claims killed, citations fetched, citations that could not be
fetched — and the assertion is only that the block is present and complete
in the phase log, which `verify_phase.sh` can check as a text fact.

**Stated limit:** that checks the *report*, not the *work*. A complete block
is consistent with a lazy pass. This is recorded as the honest ceiling of
what a procedure folder can enforce for a judgement task, not papered over.

## D5. The CLAUDE.md split — own commit, per decision 4

| destination | content | approx. lines |
|---|---|---|
| **workspace-docs `CLAUDE.md`** | cross-project rules only: Golden Rules, How Claude should help, Delivery standards, Output format, Evidence discipline, Negative claims, Targeted edits, Deploy backups, ROADMAP rows, Safe Change Policy, Run-this expectations, Session continuity, CLAUDE.md Change Management, plus the Change Log | **~174 target** |
| **`moto-diag/CLAUDE.md`** (new — moto-diag has none today) | MotoDiag-Specific Context, Product project documentation structure, the phase build workflow's moto-diag specifics, implementation.md versioning | ~120 |
| **`docs/archive/auto-iterate-and-agent-pool.md`** | the 226 lines, per D0 | 226 |
| **other project files** | COS-Specific Guidance (65), Drug Discovery Domain Guidance, Track 1 cheminformatics, Coding Standards Java (19) / JavaScript (28), Java multi-module (19) | ~160 |

Dated change-log entry in **each file that changes**, naming what left and
where it went. **Nothing is deleted before its destination exists** — the
move and the deletion are the same commit, so no intermediate state loses
text.

## D6. Verification

* **The mechanism runs** (D1) — sentinel emitted, push blocked — **before
  any other work**, and the evidence is pasted into the phase log.
* **Every skill's assertion is broken on purpose and seen to fail**, against
  its hand-written known-bad fixture, and the failure names which assertion.
* **`verify_phase.sh` is run against 255C**, a phase that is already closed
  and known good, and must pass — a script that has only ever been run on
  the phase it was written for is untested.
* **And against the bad fixture**, and must fail.
* `COLLECTED_TEST_FLOOR` raised in the commit that adds the tests.
* Full regression with hash and count.

## Scope

1. D1's mechanism proof, evidenced in the phase log.
2. `closeout`, `finding`, `refute` — in that order, each with folder,
   script where applicable, dated changelog, assertion and known-bad
   fixture.
3. `verify_phase.sh` and `roadmap_words.py`; the CLAUDE.md rule re-pointed
   at the script.
4. The push-guard hook and the README trust caveat.
5. The CLAUDE.md split, own commit.
6. Roadmap row, implementation.md row, phase docs.

## Non-goals

* **No `step0`, `regress`, `migrate` or `hooks` folder.** Four of the memo's
  seven are deferred until three have been run on real phases.
* **No plugin, no marketplace, no agent definitions.** Skills and one hook.
* **No change to any phase's content or to the knowledge base.** This phase
  touches process files and tests only.
* **No retroactive close-out.** Closed phases are not re-verified beyond
  D6's single run of the script against 255C.
* **No deletion of the 226 lines' content** — archived per D0 unless the
  operator directs otherwise.

## Risks

| risk | mitigation |
|---|---|
| The mechanism does not behave as documented | D1 runs it first and stops the phase if it does not. Step 0 verified only absence; nothing else is assumed. |
| A skill is a prompt and may simply not be followed | The test is the enforcement and is independent of the skill text. Recorded explicitly in D1. |
| The hook does not run on a fresh clone, and silence reads as a pass | README caveat per decision 1; the test is the guarantee. Called out in D2.6 in exactly those terms. |
| The closeout test hard-codes the current phase and rots | The phase is read from `docs/phases/in_progress/`, not pinned; if that is empty, the test asserts nothing is half-closed rather than passing vacuously. |
| `roadmap_words.py` and the CLAUDE.md rule drift apart | The rule keeps the specification in words and cites the script path; the script is the only implementation. Check 6 calls it. |
| The archive is written and then never referenced, becoming the phantom filing again | D0's archive note names the phases that cite it, so the references resolve; and `finding`'s assertion is the general form of that check. |
