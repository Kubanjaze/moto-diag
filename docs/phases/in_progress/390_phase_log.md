# Phase 390 — phase log: the fleet resumes where it left off

**Status:** In progress
**Branch:** `phase-390-resume`
**Prompt:** `docs/prompts/390_resume.txt`

## 2026-10-25 — start

- Read the plan: row 389A and the rows around it, `ROADMAP_AUTHORITY.md`
  (390 is backend, 205+), the newest handoff
  (`2026-10-25_389_closed.md`), F219, the `fleet` skill and the whole of
  `dispatcher.py`.
- **Row 390, 🚧, committed on `master` and pushed** (`6f32013`), before
  Step 0, as 389A's row was: a planted mission is run only when its
  phase's row on `master` is 🚧 (`dispatcher.py` l. 1144). 103 words by
  `roadmap_words.py`; `roadmap_check.py` ok; `wholetree.sh` exit 0
  (2085 passed, 10 skipped) before the commit.
- Branch `phase-390-resume` from `6f32013`, pushed.
- The service was in #14's Red Team round 2 (`dispatcher.log` 15:54:46,
  no end line). Nothing on the service, #14, PR #15 or the 389A branch was
  touched; no restart.

## 2026-10-25 — Step 0

`390_step0.md`. Every kill point per rank, what each leaves behind, what
the next start does with it today, and which of 389's resume code is
reused. Reported to the operator before v1.0, as the prompt asks; not a
stop (rule 1 names none here).

- **A guard block, recorded (rule 6):** `git commit … && git push` in one
  command was refused by `pre_push_guard.sh` ("Run `git commit` and `git
  push` as separate commands"). Run separately: Step 0 committed as
  `9197117` and pushed. The guard was not touched.

## 2026-10-25 — the operator on Step 0

"Step 0 checked against dispatcher.log and git ls-remote: it holds. Carry
on: v1.0, plan commit pushed, then build. The rule stands: no service or
Ubuntu restart while any #14 stage is running (the Engineer's fix round 2
started 16:02, then its regression and Red Team round 3). Run your one
small --resume measurement whenever suits, and write the whole-Ubuntu
restart as my paste block only when there is a gap."

## 2026-10-25 — S0-5 measured: `--resume` after a kill, in the fence

The probe (the session's scratchpad, `resume_probe.py`): a Haiku call
through `fence.sh` with the token on fd 3, the Read tool, six files to open
one at a time, in its own process group; the group SIGKILLed (what the
unit's control-group kill does); the session id read from the transcript's
file name; a second fenced call with `--resume <id>` and a `--json-schema`.

| killed | killed call's stdout | transcript | resumed call |
|---|---|---|---|
| at 3.5 s, after 2 assistant lines | empty | `155dc771-….jsonl` | exit 0, the **same** session id, the same one file, `structured_output` `{'opened': ['README.md']}`, 2 turns, $0.0038 |
| at 1.5 s, no assistant line yet | empty | `87152a3c-….jsonl` (the prompt only) | exit 0, the same id, `{'opened': []}`, 2 turns, $0.0028 |

So: a killed call's id is always on disk once its transcript exists, and
`--resume` keeps that id (no new file), so the newest transcript that was
not there before a call is that call's session. A schema call resumes with
its schema. A first probe without tools finished in 13.5 s before the kill:
a one-turn answer is written to the transcript only when complete. Total
model cost of the measurement under one cent.

The service was not touched: the probe used its own run directory in the
scratchpad and a clone of the mirror (read).
