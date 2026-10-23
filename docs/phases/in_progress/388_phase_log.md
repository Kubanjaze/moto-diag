# Phase 388 — The fleet's host and its fence — phase log

**Status:** 🚧 In progress
**Branch:** `phase-388-fleet-host` (Opus session on the home desktop, the only writer)

---

### 2026-10-22 — Opened, and Step 0

The prompt is `docs/prompts/388_fleet_host.txt`, saved verbatim. 385 has
a committed prompt (`385_the_push_tokens_own_write.txt`) and no row, and
387 is closed, so the next free number is 388.

- `9c67f93`: row 388 as 🚧 (72 words by `roadmap_words.py`;
  `roadmap_check.py` ok) and the prompt. `wholetree.sh` before it, run on
  its own: exit 0, 1837 passed, 10 skipped.
- `c6cc419`: `388_step0.md`. `wholetree.sh` before it: exit 0.
- `2f570ce`: v1.0, `plan_check 388` PASS (a first run failed P6 on a line
  of mine starting with "…", rewrapped). `wholetree.sh` before it: exit 0.
  Pushed.

Read first: `docs/handoffs/2026-10-22_387_closed.md` (the newest, by
`git log -1 --name-only --format= -- docs/handoffs/`); rows 380–387;
`ROADMAP_AUTHORITY.md` (388 is this repository's); the fleet proposal;
`387_implementation.md` (what it locked: `rank_call.call` and the ranks'
`run=` callable, the eleven labels, the read-only fence by tool list);
`386_implementation.md` and the deploy changelog's setup-token procedure;
F213, F214 and F215 in `docs/FOLLOWUPS.md`.

Step 0's findings, in `388_step0.md`:
- claude 2.1.309, the operator's Max login, no `ANTHROPIC_API_KEY`
  anywhere looked, and **no fleet setup-token on this machine**: the phase's
  one rule-1 stop (a login). Built and proven without it as far as no model
  call is needed.
- `../workspace-docs` is here (pre-approval (b) not needed). The import
  loads from the repository root and **not** from a fresh clone, even with
  the sibling beside it: Claude Code's approval is per project path.
- `claude -p "/usage"` prints the 5-hour and weekly figures in print mode,
  0 turns, no cost: no ceiling file needed.
- A prototype bubblewrap fence with no `/home` refused every planted write
  and read; a proxy outside with a bridge inside let claude reach only
  `api.anthropic.com` (a dummy key, refused by the real API, nothing billed)
  and refused GitHub with 403.

**A guard blocked a command.** A Step 0 probe ran `git commit` and `git
push` inside one `bwrap … sh -c '…'` line, against a throwaway clone in the
scratchpad. The push guard refused it: "This command runs `git commit`
before `git push` … Run `git commit` and `git push` as separate commands."
It judges the command's text, and the text held both. Split into two runs;
the guard is unchanged.

Decisions (each in `388_step0.md` S0-7 with its reason): the model call is
the fenced part and the rank's script is not; the fence seeds the import
approval for its own clone path; the sweep reads the ten state labels, not
`mission`; the digest is kept, not committed or posted; a second Windows
task holds the VM like 382's.
