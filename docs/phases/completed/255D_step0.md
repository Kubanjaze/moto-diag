# Phase 255D — Procedures as folders — Step 0 (DRAFT, not v1.0)

**Date:** 2026-09-22 · **Branch:** `phase-255D-procedures-as-folders`

Three questions were set: confirm the tooling's documented layout rather than
assume it; census CLAUDE.md and propose what moves; design `closeout` first,
with the assertion that makes skipping it fail.

---

## S0-1. The tooling, confirmed rather than assumed

Researched against the current documentation and then checked against this
machine. **Four of the memo's assumptions do not survive.**

### What the docs say

| thing | the answer | source |
|---|---|---|
| project skill | `.claude/skills/<name>/SKILL.md` | code.claude.com/docs/en/skills |
| personal skill | `~/.claude/skills/<name>/SKILL.md` | ibid. |
| the file's name | **always `SKILL.md`** | ibid. |
| supporting files | supported, referenced via `${CLAUDE_SKILL_DIR}` | ibid. |
| slash commands | **skills ARE the command mechanism**; `.claude/commands/<name>.md` is the legacy form | plugins-reference, "Commands vs Skills" |
| arguments | `$ARGUMENTS`, `$0`/`$1`, or named via an `arguments:` frontmatter list | skills docs |
| shell in a skill | a skill is a **prompt, not a script**; `!` + backticks injects command output at load | ibid. |
| hooks config | `hooks → <EventName> → [ { matcher, hooks: [ {type, command, if, timeout} ] } ]` | hooks-guide |
| committed hooks | `.claude/settings.json` may define them, **gated on workspace trust** | ibid. |
| blocking | exit 2 blocks and feeds stderr back; `PreToolUse` also blocks via `hookSpecificOutput.permissionDecision: "deny"` | ibid. |

### The four corrections

1. **There is NO pre-push hook event.** The documented event list has no
   `PrePush` or git-specific event of any kind. The memo's "pre-push
   assertion" cannot be built the way it was imagined. The documented route
   is a **`PreToolUse` hook matching `Bash` with `if: "Bash(git push *)"`**,
   exiting 2 to block. This changes S0-3 below, and it is the single most
   important finding of the research.
2. **Skills, not commands.** "Slash commands" as a separate mechanism are
   legacy. A procedure folder is a **skill**, and the folder name is fixed:
   `.claude/skills/<name>/SKILL.md`. The memo's "versioned folders" are
   real, but they are skill folders with a mandated filename.
3. **Directory-scoped skills are not a documented feature.** Scope is user /
   project / plugin. A procedure cannot be scoped to `src/` by the mechanism.
4. **A committed hook requires workspace trust.** It does not run for a
   fresh clone until the workspace is trusted, so a hook is an assertion for
   *this* working copy, not a property of the repository. **This is why a
   test is the stronger guarantee and a hook is the faster feedback** — see
   S0-3.

### What this machine actually has

**Nothing.** Verified directly: `~/.claude/skills`, `~/.claude/commands` and
`~/.claude/agents` do not exist; `/Users/lilquant/Projects/moto-diag/.claude/`
does not exist at all; `~/.claude/settings.json` holds one key and no `hooks`
block; there is no project `settings.json` or `settings.local.json`. The
phase is greenfield, which removes the migration risk the memo worried about
and means the first folder also creates the directory.

**Caveat, stated rather than hidden:** the table above is documentation, read
and cited. The only claims I verified *by execution* are the absence claims
in this subsection. Nothing has been run through a skill or a hook on this
machine yet, so **S0-3's mechanism is unproven until the positive control in
v1.0 runs it.** That is the point of the control.

---

## S0-2. The census — 1,328 lines, and what is actually in them

Measured by heading, 38 top-level sections, 120 headings total.

| category | lines | share |
|---|---|---|
| **rule** — a constraint on how work is done | 829 | 62% |
| **procedure** — an ordered sequence someone follows | 323 | 24% |
| **record** — what happened, kept for the next reader | 174 | 13% |

### The procedures, by size

| lines | section |
|---|---|
| 149 | `Agent Delegation for Auto-Iterate` (L460) — incl. a 50-line **Spawn script** |
| 77 | `Peak-Efficiency Agent Pool Mode` (L609) |
| 44 | `Auto-iterate discipline` (L416) |
| 38 | `implementation.md versioning rules` (L311) |
| 34 | `Phase build workflow` (L227) |
| 28 | `CLAUDE.md Change Management` (L995) |
| 25 | `Multi-Workstation Sync Discipline` (L725) |
| 19 | `Prompt Templates` (L1023) |
| 14 | `Deploy backups` (L1094) |
| 11 | `Session Continuity & File Handoff` (L984) |

### The records

| lines | section |
|---|---|
| 125 | `CLAUDE.md Change Log` (L1204) — 11 dated entries, growing 8–21 lines each |
| 39 | `Recurring Failure Families` (L686) |
| 10 | `Context Search Keywords` (L974) |

### The finding the census produces

**The rules that are load-bearing for this project are a small minority of
the file.** Golden Rules, Delivery standards, Evidence discipline, Deploy
backups, ROADMAP rows, Negative claims, Targeted edits and Output format
together are **~174 lines, 13%.** Those are the ones cited in a working
session.

Against that: **226 lines (17%) are auto-iterate and agent-pool machinery**,
and a further large block is other projects entirely — Track 1 drug
discovery and cheminformatics, Coding Standards for Java (19) and JavaScript
(28), Java multi-module (19), and `COS-Specific Guidance` (65). None of that
is wrong; none of it is read during a moto-diag phase.

### Proposed movement

| from CLAUDE.md | to | why |
|---|---|---|
| `Phase build workflow`, `Phase completion gate`, `implementation.md versioning rules`, `Deploy backups` procedure half, `ROADMAP rows` counting method | **`closeout`** | one ordered sequence, run every phase, currently in four places |
| the regression-with-hash-and-count discipline (today implicit, plus `COLLECTED_TEST_FLOOR`) | **`regress`** | invoked by `closeout`, also standalone |
| `Evidence discipline` measuring half; the Step 0 shape this project actually uses | **`step0`** | the rule stays; the sequence moves |
| the adversarial refuter workflow (**not in CLAUDE.md at all** — it lives only in practice) | **`refute`** | an undocumented procedure is the strongest case for a folder |
| `Migration rollback forward-compat` + the migration/rollback/round-trip sequence | **`migrate`** | three of 255C's seven bug fixes were migration-shaped |
| the F-number discipline and `FOLLOWUPS.md` entry format (**also not in CLAUDE.md**) | **`finding`** | 255C filed F135 partly *because* the format was unwritten and a filing was claimed that never happened |
| `Agent Delegation` + `Peak-Efficiency Agent Pool` (226 lines) | **out of scope, flagged** | large, and not exercised in current working style; moving it untested would be a guess |

**What stays in CLAUDE.md:** rules only, plus the Change Log, which is a
record and belongs with the rules it records.

**Open question for v1.0, not decided here.** CLAUDE.md lives in
`workspace-docs`; these procedures are moto-diag's and would live in
`moto-diag/.claude/skills/`. That splits rule from procedure across two
repositories. The alternative is a `workspace-docs` skills directory that
moto-diag sessions cannot see, which is worse. **Recommendation: procedures
go in moto-diag, and CLAUDE.md gains one short section naming them and where
they live** — so the index stays in one place while the content is versioned
next to the code it operates on.

---

## S0-3. `closeout` first — and the assertion, rewritten around the research

The memo asked for "its assertion (pre-push or test) that makes skipping it
fail". **There is no pre-push hook event**, so the choice is not
pre-push-or-test. It is:

| option | mechanism | fails when | weakness |
|---|---|---|---|
| **A. hook** | `PreToolUse`, matcher `Bash`, `if: "Bash(git push *)"`, exit 2 | at the moment of push | needs workspace trust; does not survive a fresh clone; blocks the tool, not the repository |
| **B. test** | a pinned test in `tests/`, `COLLECTED_TEST_FLOOR` style | on any run of the suite | fires at test time, not at push time — later feedback |

**Proposed: both, and they are not redundant.** The test is the guarantee —
it travels with the repository, runs in any checkout, and cannot be skipped
by declining a trust prompt. The hook is the *latency*: it catches the
omission at the push rather than at the next full regression, which on this
tree is a 30-minute round trip.

**What the test asserts.** Not "closeout ran" — that is unfalsifiable from
inside the suite. It asserts the **artefacts closeout is defined to
produce**, for the phase named as current: that the phase doc has moved from
`in_progress/` to `completed/`, that its status line reads Complete, that a
ROADMAP row exists for it and its body cell is within the 120-word cap by
the method now written into CLAUDE.md, and that `implementation.md` carries
a row and a bumped version. Each is a file fact, checkable, and each is
something a skipped closeout leaves undone.

**The positive control, per folder.** The memo's rule — a folder counts only
after a positive control — is sharpened by 255C's experience into
*independent reference*: the control must be satisfied by something that
does **not** reimplement the procedure. For `closeout` that is a **known-bad
fixture**: a phase directory prepared with the doc left in `in_progress/`,
against which the assertion must fail, and the same fixture corrected,
against which it must pass. 255C spent a commit on a guard that could not
fail and another on a control that measured a proxy; the control is
specified before the folder, not after.

**Build order:** `closeout` alone in v1.0, with its test, its hook and its
known-bad fixture. Nothing else moves until that one folder has been run
end to end on a real phase. Six more folders designed on an unproven
mechanism would be six guesses.

---

## S0-4. Risks

| risk | mitigation |
|---|---|
| A skill is a prompt, not a script — it can be read and not followed | The test is the enforcement; the skill is the instruction. They are separate on purpose. |
| A committed hook needs workspace trust and silently does not run without it | Recorded as a known limit; the test is what actually guarantees. The hook's absence must not read as a pass. |
| Moving a procedure loses the reasoning attached to it in CLAUDE.md | Each folder carries its *why*, and CLAUDE.md keeps a one-line pointer. Nothing is deleted before its replacement runs. |
| The documentation read here does not match the installed build | Flagged: only the absence claims were verified by execution. v1.0's first act is running the mechanism, not writing six more folders on top of it. |
| Seven folders is a rewrite of how the project works, mid-stream | `closeout` only in v1.0. The other six are proposals in S0-2, not commitments. |
