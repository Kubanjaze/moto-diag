# Phase 398 — phase log: the two stalls at the Red Team's clear (F251, F252)

**Status:** In progress

**Started 2026-11-08** (UTC; 2026-11-07 evening EST) on the home desktop
(WSL2), the only writer, on `phase-398-the-two-stalls`. The prompt is
`docs/prompts/398_the_two_stalls.txt` (the operator's words, verbatim);
the operator's word is K67.

## 2026-11-08 01:14 UTC — start

- Master fetched at 01:14 at `f6aead1` (the prompt, row 398 🔲, K67 and
  row 12 of "Next, in order" already on it). `pgrep -x bwrap` empty: no
  fleet stage running.
- Read before planning: `CLAUDE.md`, `docs/decisions.md` (K65–K67),
  F251 and F252 in `docs/FOLLOWUPS.md`, the plan of record's "Changes to
  the order", and the code each finding names.
- F253 was the next free number (`next_f_number.sh`; no `### F25[3-9]`
  or `### F26` on any local or remote branch).
- Issue #54 and its hold untouched.
- Row 398 🚧 on the branch before Step 0.

## 2026-11-08 01:20 UTC — Step 0

`398_step0.md`. (a) A5 fails both refused logs and passes both hand
fixes; reading only lines that begin with the prefix reads the real
record in both refused logs (12186 at `c2b0767`; 12292 at `ca580f6`) and
changes what A5 reads in no closed log (the three bullets that do not
begin their line, 258–260, are on `A5_COMMAND_EXEMPT`). No reason not to
build F251's first fix. (b) The stop path, the due rule and the round
count are as F252 says; the real stop comments on #45 and #50 and the
label events (2 h 8 min, 9 h 13 min) re-measured. Auditing the other
readers of the prefix found Q4's counts read the old way: filed as
**F253**, left.

**Decision (recorded, not a stop):** the hold catches any `Stop` from the
record push, not only the gate's G6, since a failed push or a fast run
held for space leaves the same nothing-due state; the operator's step is
the same (fix, then take `needs-hands` off).
