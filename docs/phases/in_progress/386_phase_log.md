# Phase 386 — Fleet records — phase log

**Status:** 🚧 In progress
**Branch:** `phase-386-fleet-records` (Opus session on the Mac, the only writer)

---

### 2026-10-22 — Opened, and Step 0

The prompt is `docs/prompts/386_fleet_records.txt`, saved verbatim. 385
has a merged prompt and no row; the operator: "Take the next free ROADMAP
number after 385 (385 keeps its own prompt)", so this phase is 386.

- `ee300a4`: `docs/reports/2026-10-22_fleet_proposal.md` committed byte for
  byte as the branch's first commit (sha256 `473e7e4c…58342` before and
  after).
- `51a8f52`: row 386 as 🚧 (67 words by `roadmap_words.py`;
  `roadmap_check.py` ok) and the prompt. Pushed.
- `wholetree.sh` before each: exit 0, 1794 passed, both times.

**A guard blocked a command.** Adding the row with a short Python script
was refused by the edit guard: "a Python script body writes to a path the
edit guard cannot resolve, and the body names src/ or tests/". The row's
text names `src/` and `tests/`. The row went in with the Edit tool instead;
the guard is unchanged.

Read first: `docs/handoffs/2026-10-21_384_closed.md` (the newest, by
`git log -1 --name-only --format= -- docs/handoffs/`); rows 380–384;
`ROADMAP_AUTHORITY.md`; the 385 prompt. No open finding touches a
documents-only phase except through the debt table.

Step 0 is `386_step0.md`. In short: of the debt table, four items are
confirmed (root `phase_log.md`, `implementation.md` line 6,
`contributing.md`, the `CLAUDE.md` import) and four refuted (the version
split is documented on purpose; `README.md` was fixed in 378; F132–F134
all resolve; 072 was applied live 2026-09-27 23:38:26). B2 catches a lost
F132 but cannot see F133 or F134, which no completed phase document cites.
353 and 354 cost $17.87 and $22.66 at list price. No API key is set on the
Mac, and `orchestrate.py`'s Anthropic stages already run on the OAuth
token. The repo is public with no protection on master.

Waiting for the operator: the desktop paste block's output, the `/usage`
figures, and K11.

**A second guard block.** Committing and pushing Step 0 in one command
(`git commit … && git push`) was refused by the push guard. They ran as two
commands; `3e030d6` pushed. The guard is unchanged.

### 2026-10-22 — The operator's answers to Step 0

- **The desktop:** the operator ran the checks in the Ubuntu window on the
  home PC in their own block and pasted the output; ALL GOOD. It is
  verbatim in `386_step0.md` S0-5: systemd `running`; the API and
  `tailscaled` up 1 day 7 h 45 min; `unshare -Ur true` works and `bwrap`
  is installed; `gh` installed and logged in as Kubanjaze.
- **Usage:** "current session 7% (resets 5pm); current week all models 6%,
  current week Fable 10% (both reset Oct 28, 12pm, America/New_York)." The
  operator: "Record that as a baseline only; it includes today's
  interactive use. The number that decides fleet throughput is measured
  around one Engineer build in a later phase, not here." In S0-6.
- **K11:** "Subconscious: nothing to do until it cancels tomorrow. I'll
  give you the K11 line on 10/23." Not yet confirmed; nothing done to the
  account.
- **GitHub accounts and master protection:** "leave both for a later
  phase, your default is right. File one follow-up finding carrying two
  facts so that phase doesn't rediscover them: rulesets are free on a
  public repo and moto-diag is public today, so if the repo ever goes
  private, master protection becomes a GitHub Pro purchase, not a click;
  and the fleet's own GitHub identity (an App, or a machine user with
  write) is created in the phase where a rank first pushes," The pasted
  text ends at that comma; the finding carries the two facts as given.

**Decision: the close-out waits for the K11 line.** The prompt asks for
K11 in this phase's log when the operator confirms it, and the operator
gives it on 2026-10-23. The build runs now; the regression of record and
the close-out follow the K11 line, so it lands in this log and not the next
phase's. Waiting on the operator's own word is not a rule-1 stop; the row
says so while it waits.
