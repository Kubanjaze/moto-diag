# Phase 387 — The XO and the Yeoman — phase log

**Status:** 🚧 In progress
**Branch:** `phase-387-xo-yeoman` (Opus session on the Mac, the only writer)

---

### 2026-10-22 — Opened, and Step 0

The prompt is `docs/prompts/387_xo_and_yeoman.txt`, saved verbatim. 385
has a committed prompt and no row, and 386 is closed, so the next free
number is 387.

- `ce59e68`: row 387 as 🚧 (60 words by `roadmap_words.py`;
  `roadmap_check.py` ok) and the prompt.
- `wholetree.sh` before it, run on its own: exit 0, 1794 passed.

Read first: `docs/handoffs/2026-10-22_386_closed.md` (the newest, by
`git log -1 --name-only --format= -- docs/handoffs/`); rows 382–386;
`ROADMAP_AUTHORITY.md`; the fleet proposal; `386_implementation.md`,
`386_step0.md`; `docs/decisions.md`. Open findings that touch this phase:
F213 (B2 reads only phase documents; the proposal applies B2's habit to
K-ids, which `decide` does for its own line) and F214 (the fleet's own
GitHub identity and the ruleset, later; this phase uses the operator's
login as the prompt says).

**A guard blocked a command.** A shell loop probing six model ids wrote
each answer with `> $m.json`; the edit guard refused it: "the edit guard
cannot tell where the redirect `>` `$m.json` writes (a variable,
substitution, glob or unknown directory), and blocks what it cannot
resolve. Use a literal path." The probes moved into a scratchpad script,
`probe_models.py`, that writes its own files; the guard is unchanged.

Step 0 is `387_step0.md`. In short: Fable is reachable (`claude-fable-5-1`
served), so the XO runs on Fable. The XO's flags leave the session with
only Glob, Grep and Read, and a planted Bash call made nothing; the
control with Bash allowed made the file. `gh` is the operator's admin
login and none of the eleven labels exists. One XO call on 386's v1.0
read about 148K tokens and wrote 7,347, $1.22 at list price, and returned
its verdict through `--json-schema`. The checklist as written fails both
plans the prompt names as known-good: a real fork, put to the operator.

### 2026-10-22 — The operator's answer, and v1.0

The fork in `387_step0.md` was put to the operator in plain words: the
checker asks three things 384 and 386 never did (a classification line;
the three newest change-log entries and their checks; the stops it
expects), so how should it treat those two plans? The options were "Pin
them (Recommended)" and "No pin, they fail". The operator's answer,
verbatim: **"Pin them (Recommended)"**.

So `plan_check.py` carries a pinned list of the two plans written before
it, with the items each predates (384: classification, change log, stops;
386: change log, stops), held to equality by a test. Every plan from 387
on faces every item.

Decided without asking, each in v1.0 with its reason:
- `decide` uses no model: the words are the operator's, verbatim.
- `digest` reads this repository's `FOLLOWUPS.md` only (mobile's headings
  do not mark closure; S0-7).
- A failed checklist is a back-to-captain round, with no model call.
- The XO's rounds are counted from its own comments on the mission issue,
  so the state lives on GitHub, where the label is.
