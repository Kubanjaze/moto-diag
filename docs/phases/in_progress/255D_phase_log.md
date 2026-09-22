# Phase 255D — Procedures as folders — phase log

**Status:** ⏸ HALTED at D1 — the mechanism does not behave as documented
**Opened:** 2026-09-22

---

### 2026-09-22 19:00 — D1: the mechanism proof. One half passes, one half fails, and a third thing is broken

v1.0's D1 said: run the mechanism before writing anything that matters, and
**if either half fails, stop and re-plan.** One half failed. This is the
stop.

## Result 1 — the skill is NOT discoverable. **FAIL.**

`.claude/skills/ping/SKILL.md` was created, containing a single sentinel
`PING-255D-SENTINEL-8f3a2c`. Invoking it returned:

```
Unknown skill: ping
```

**Two locations were tried, because the first failure had an obvious
alternative explanation.** The session's transcript directory is
`~/.claude/projects/-Users-lilquant-Projects/`, which encodes the session
root as `/Users/lilquant/Projects` — the **parent** of the repository, not
`moto-diag`. So the skill was placed a second time at
`/Users/lilquant/Projects/.claude/skills/ping/SKILL.md`. **Same result.**

**Conclusion:** skills are enumerated when the session starts. A skill
created during a session is not invocable in that session. This is not a
path error — it reproduces at both candidate roots.

**Not yet distinguished, and the operator can settle it in one step:**
whether a restart makes `ping` invocable. The file is committed and left in
place for exactly that test.

**Second finding, independent of the reload question, and it matters more
for the plan.** If the project root for `.claude/` discovery is the
directory a session is *started in*, then a skill committed to
`moto-diag/.claude/skills/` is invisible to any session started at
`/Users/lilquant/Projects` — which is how this session was started, and
therefore plausibly the normal case. **That would make "versioned folders in
the repo" unreachable by the mechanism that is supposed to read them.** v1.0
assumed the repository was the root. It did not verify it, and Step 0 did
not either.

## Result 2 — the PreToolUse hook DOES block. **PASS.**

`.claude/settings.json` was given a `PreToolUse` hook on `Bash` running a
script that writes to stderr and exits 2. It fired, and the block came back
as the tool error:

```
PreToolUse:Bash hook error: [.../pre_push_guard_test.sh]:
BLOCKED-255D-HOOK-4d1e9b: closeout has not been verified for this phase.
```

So the enforcement half of D2.6 is real: **exit 2 blocks, and stderr reaches
the model.** That is the mechanism the push guard depends on, and it works.

**Two qualifications, both learned the hard way.**

*Config is picked up with roughly a one-turn delay.* The first `git push`
after writing `settings.json` was **not** blocked; the hook fired on the
following turn. A guard written and immediately tested in the same turn will
look like it does not work.

*A blocking hook on `Bash` locks out `Bash`, including the command that
would remove it.* That is how the block was discovered: it fired on a `cat`,
not a push. Recovery was via the `Write` tool, which does not pass through a
`Bash` matcher. **Worth knowing before a guard is installed for real.**

## Result 3 — `if` is honoured on PostToolUse and IGNORED on PreToolUse. **BROKEN as v1.0 specified.**

This is why the blocking hook fired on a `cat`. Isolated with non-blocking
marker hooks so nothing could lock out again:

| hook | `if` | non-push command | result |
|---|---|---|---|
| `PostToolUse` on `Bash` | `Bash(git push *)` | ran | marker **absent** — filtered correctly |
| `PreToolUse` on `Bash` | `Bash(git push *)` | ran twice | marker grew **1 → 2** — fired both times |

**`PreToolUse` ignores `if` in this build.** v1.0's D2.6 specifies exactly
that combination, so **the push guard as planned would block every Bash
command in the session.** It did, to me, for one turn.

**The fix, for the re-plan:** the guard must filter itself. The hook receives
the tool call as JSON on stdin, so `pre_push_guard.sh` reads
`tool_input.command`, exits 0 immediately unless it is a `git push`, and only
then runs the closeout test. That is correct whether or not `if` is honoured,
and it does not depend on a field whose behaviour differs by event.

## What this changes

v1.0's enforcement design survives: **a test plus a PreToolUse guard that
exits 2** is buildable and was demonstrated. What does not survive is
(a) the assumption that a skill can be added and used without a restart,
and, more seriously, (b) the assumption that `moto-diag/.claude/skills/` is
the directory the mechanism reads.

**Halted for re-planning rather than continuing, per v1.0 D1 and the
operator's instruction.** Building `closeout` now would mean writing a skill
that cannot be invoked into a directory that may not be read, and enforcing
it with a hook configured in a way that blocks every command.

**Nothing was left behind.** The test hook, its guard script and the
session-root copy of the skill were removed;
`moto-diag/.claude/skills/ping/SKILL.md` is committed and kept, because it
is the fixture for the restart test.
