# Phase 360 — F174 powertrain default, and the edit guard — phase log

**Status:** 🚧 In progress
**Branch:** `phase-360` (Opus session, main checkout, the only writer)

---

### 2026-09-28 — Opened

The prompt is `docs/prompts/360_powertrain_and_edit_guard.txt` (merged in
`145d0b6`). The operator's decisions of 2026-09-28, verbatim:

> 1, 2, 3, 5 as recommended.

> add to the F174 phase: enforce the edit rule. 356 and 357 both edited source without the Edit tool — a written rule broken twice. PreToolUse hook on Bash that blocks sed -i, heredoc/redirect writes into src/ and tests/, same fail-closed pattern as the push guard, with a planted positive control per blocked form.

Recommendation 5 was a small phase for F174 before Track O batch 1.

Read first: the 357 handoff (`docs/handoffs/2026-09-28_357_closed.md`),
F174 and 357's amendment, the Track O triage with the decisions at its top,
the deploy skill, and `pre_push_guard.sh` / `_pre_push_guard.py`.

- 360 is the next free number: the highest row was 359, and no phase
  document or handoff names 360.
- Row 360 🚧: `dfb0a9a`, pushed. `roadmap_check.py` green; the row is 61
  words. `wholetree.sh` before the commit: 1480 passed.

### 2026-09-28 — The session's machine slept mid-Step 0

After `dfb0a9a`, the machine slept before any Step 0 document was
written. The operator measured, and this session re-measured:
- only `dfb0a9a` had landed, and it was pushed;
- the tree was clean and `in_progress/` was empty;
- live was untouched: the database file's mtime was still 14:49, and it
  held 10 bikes, all `ice`, at schema 73.

The census and the 17 tables referencing `vehicles` were read again, with
the same result. The per-option test counts had been grep counts of call
sites, not a measurement, so they were measured again by running each
option in a worktree (S0-6).

### 2026-09-28 — Step 0

`360_step0.md`. In short:
- **Six paths store `ice` nobody stated**: the four named, plus the photo
  path when the vision reply omits the key, and the column default, which
  live rows 6–9 very likely came through.
- **Storing NULL changes no reader's output today except `garage list`**,
  which prints NULL as `ice`.
- **The live census is `ice` 10**, every one a petrol-only model. Whether
  anyone stated them cannot be told. No option changes a live row.
- **The fork**: (a) require or ask everywhere; (b) store unknown; (c) the
  CLI asks and the API stores unknown. Recommended: (c), with
  `workflow start` storing the stated value on a bike held as unknown.
  Migration 074's rebuild (the default removed) is common to all three.
- **The guard's design**, with its blocked forms, fail-closed cases,
  allowed forms and known limits. `perl -i` is proposed beyond the
  operator's list.

Decisions made here, not stops:
- **The per-option counts come from a worktree of `dfb0a9a`**, run with
  `PYTHONPATH` set to the worktree's `src`, never from a checkout of this
  tree. Its own 16 baseline failures are subtracted as IDs. They come
  from the worktree's location: the packaging tests' fresh venv, and gate
  11's read of the sibling mobile repo. That ceiling is written in S0-6.
  Measured counts beyond that baseline: (a) 85, (b) 6, (c) 61; every one
  is a test that pins the old default or adds a bike without a
  powertrain.
- `engine_type`'s identical default is out of scope. It is filed as F177
  with this Step 0, because the first `wholetree.sh` run failed B2 on the
  citation before the entry existed.
- The app's `ice` preselection is the mobile repo's finding, for a session
  rooted there.

**Stopped for the operator's pick on part 1** (rule 1: a real fork).
Committed `3dc7022`, pushed.

### 2026-09-28 — The operator's picks, verbatim

> 1: (c). 2: (ii). 3: keep perl -i, and also block cp, mv and patch into src/ and tests/ (git mv stays allowed), each with its own planted positive control.

So:
- **Part 1 is option (c).** `garage add` and `add-from-photo` ask for the
  powertrain when none is given. The API stores NULL when the field is
  absent.
- **`workflow start` is (ii).** On a bike stored as unknown, it stores the
  stated value on the bike and says so.
- **`perl -i` stays blocked.** `cp`, `mv` and `patch` into `src/` or
  `tests/` are blocked too, each with its own planted positive control.
  `git mv` stays allowed. The known limits lose those three.

v1.0: `3f5d0df`, pushed before any code.

### 2026-09-28 — The edit guard

Built first, so the rest of the build runs under it:
- `.claude/skills/closeout/edit_guard.sh`, a wrapper that turns any exit
  status other than 0 into 2;
- `_edit_guard.py`, with a small shell lexer (quotes, `$…`, `$(…)`,
  backticks, heredocs, `((…))`, comments), then a per-command check;
- the second `Bash` `PreToolUse` entry in `.claude/settings.json`, with a
  30 s timeout; the guard's own clock is `LIMIT_S = 5`.

**Tests:** `tests/test_phase360_edit_guard.py`, 139, through the wrapper
with the hook payload on stdin:
- positive controls: `sed -i` 14 spellings; `perl -i` 4; redirects 18,
  357's `cat >> src/… <<'EOF'` among them; `tee` 3; `cp` 5; `mv` 4;
  `patch` 5; script bodies 18, 356's exact-match replace script among
  them; plus an unresolvable body naming `tests/` and a symlink into
  `src/`;
- fail-closed: 9 unreadable or unresolvable lines; a payload that is not
  JSON; an injected exception; a planted slow check past the clock; the
  wrapper converting exit 1;
- negative controls, 42: the commit-message heredoc with `sed -i`,
  `> src/x`, `;` and apostrophes in its body; `git mv`, `checkout`,
  `apply`, `stash pop`; read-only scripts; redirects into the scratchpad
  and `docs/`; `sed -n`; `grep '->'`; `awk '$1 > 5'`; `(( ))` and `[[ ]]`.
  A mobile-repo script naming its own `src/` is allowed, and the same body
  run here is blocked;
- each assertion helper shown red on the other's output first;
- the settings entry and its timeout.

**The replay (`360_replay_guard.py`, committed with the census).** Before
the hook went on, every Bash command in the eight newest session
transcripts was run through the guard. The first pass blocked 665 of
5,675, and reading samples of each class found three guard defects,
fixed before the hook went on:
- **The mention fallback ignored the working directory.** A `node` script
  run in `moto-diag-mobile` was blocked for naming that repo's `src/`. A
  mention now counts only when it resolves into this checkout's
  `src/` or `tests/`.
- **`$'` inside double quotes was read as an ANSI-C string.** That broke a
  `python -c "…'^\]\s*$'…"`.
- **An unquoted heredoc's body was parsed raw.** `$n != 2` is not
  Python. The body is now expanded as the shell would expand it, and so
  is a `-c` word.

Also from the replay, and decided here, not stops:
- **The resolver follows every assignment of a name**, and uses the fixed
  directory of an f-string, a `/` join or a shell word. Under `src/` or
  `tests/` the write is blocked outright; under a directory that cannot
  hold them it is allowed; only a path under the checkout root stays
  unknown.
- **An unterminated heredoc is read as bash reads it**, to the end of
  input, and judged, rather than refused as unparseable.

The final census (5,698 commands, 2026-09-09 to 2026-09-29 UTC):
- 552 real edits blocked, 459 of them Python heredoc bodies;
- 68 blocked by failing closed (1.2%);
- 5 malformed commands blocked;
- the slowest check took 6.3 ms.

**The rule was broken hundreds of times across those sessions, not twice.**

**The hook went live mid-session.** Just after the settings entry was
added, `echo planted >> tests/_planted_live_probe.py` was refused by
`edit_guard.sh` and the file was absent after. The fresh-session proof
follows.

**Known limits:** in the closeout CHANGELOG's 2026-09-28 entry, and here:
- a script file run by name is not opened (the mutation scripts);
- `install`, `rsync`, `dd`, `truncate`, `ln`, `rm` and `git apply` are not
  blocked;
- `subprocess`, `eval`, `os.chdir` and run-time values are not followed;
- only Python and shell bodies are parsed;
- only this checkout is protected;
- a glob or a substitution after a fixed directory is judged by that
  directory.
