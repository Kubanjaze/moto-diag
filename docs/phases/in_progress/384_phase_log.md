# Phase 384 — The Mac runs the PC's steps — phase log

**Status:** 🚧 In progress
**Branch:** `phase-384` (Opus session on the Mac, the only writer)

---

### 2026-10-20 — Opened, Step 0, and the stop

The prompt is `docs/prompts/384_the_mac_runs_the_pcs_steps.txt` (merged
`a4d94ce`). Row 384 went 🚧 before Step 0. Read first: the deploy skill,
"Where live is (Phase 382)"; 382's options 1A to 1C
(`382_phase_log.md`); `383_desktop_steps.md`; 383's handoff; open findings
F207, F209, F210 (none touches the way in; F210's column list is what the
proof's verify-live exercises on live for the first time).

The operator's words, from the prompt: "cant everything i do on the mac
just automatically get done on the pc?"; the pick: a builder on the Mac does
the PC's steps over the tailnet, the operator only approves; 382's option
1C, whose two costs ("it opens SSH on this machine and makes every deploy
depend on two machines being up") the operator now accepts.

`384_step0.md` S0-1 re-verifies the prompt's facts from the Mac: all that
can be measured from the Mac hold (three tailnet nodes, all the operator's;
no answer on 22 or 2222 on the tailnet, the home IPv4 or the home IPv6
address; `/healthz` at schema 87 over the tailnet; live.json null). The
PC-side facts are from the record; the way in's first use reads them.

**What changed the recommendation:** Tailscale's own page says its SSH
server does not run on Windows, serves file transfer itself, and does not
fit command restriction (S0-2). So Tailscale SSH can only be a full shell;
a fixed list needs OpenSSH's forced command.

**CLAUDE.md rule 6** gained the operator's plain-English rule, with their
words and the date, and a change-log entry.

The prompt asks for a stop at Step 0 with four questions: the way in, what
it allows (and verify_phase.sh's live check), how the diff files reach the
branch, and the one-sitting list of sign-ins. They are in `384_step0.md`
S0-4, with the recommendation 1A, 2A with (i), 3A. Waiting for the
operator's picks.

### 2026-10-20 — The operator's picks, two more proofs, v1.0

**The operator's words:** "1A, 2A (i), 3A".

Then, before v1.0: "Two more proofs, please: (1) after the PC restarts with
nobody signed in, the Mac can still get in, the same test 382 did for the
server; (2) only the Mac can reach the door, not other devices on my
tailnet: for example, from the PC's Windows side, an attempt on port 22 of
motodiag-ops must fail." Both are in v1.0's proofs: the Windows attempt is
in proof 1 (doors that must fail), the restart is proof 4.

**A slip, corrected before the push:** v1.0 was first committed without
`wholetree.sh` before it (rule 3). The commit was unpushed; the check was
run and the commit amended.

Decided at v1.0, without a stop:
- **Every operation that runs repository code names the exact commit** the
  Mac has pushed, and the PC checks it out detached. Step 0's list had a
  separate "pull a branch"; pinning the commit makes the PC run what the Mac
  sees, so the separate pull is dropped.
- **The outbox is outside the PC's checkout** (`~/motodiag/outbox/`), so the
  tree stays clean between runs. Step 0 said the PC's copy would be removed
  once the Mac's commit matched; the outbox does the same with no extra
  operation.
- **The dispatcher is installed root-owned outside the checkout**, so what
  the key may run changes only by a fresh install.
- **`verify-live 383` runs before any new backup** in the proof, so retain-5
  cannot remove its backup first.
- **The host key is pinned on first use** (`accept-new`): the first
  connection already runs inside the tailnet, whose keys prove the peer.

### 2026-10-20 — The build: the dispatcher, the Mac's client, the video check, check 8

Written: `ops/desktop/motodiag_remote.py` (the fixed list),
`ops/desktop/install_remote.sh`, `.claude/skills/deploy/remote.py`,
`.claude/skills/deploy/media_check.py`; `verify_phase.sh` checks 8 and 9;
the deploy skill and its CHANGELOG. Tests: `test_phase384_remote_dispatcher.py`
(45), `test_phase384_remote_client.py` (13), `test_phase384_install_remote.py`
(9), `test_phase384_media_check.py` (8): 75 added, 0 removed, by a diff of
collected ids against v1.0 (10923 → 10998); the floor raised to 10998.

Decided, without a stop:
- **The video check compares each served body with the sha256 its row
  recorded at upload**, not with the file on disk. 382's script compared the
  body with the file the route had just read, so a changed or swapped file
  passed. `test_a_changed_file_fails` holds it.
- **382's check-8 text test** (`test_phase382_live_location.py`) pinned
  "live not here, the check fails". The operator's (i) changes that rule on
  purpose: live elsewhere asks the way in and fails when that fails. The
  test now pins the new rule; the behaviour is run by
  `test_phase384_install_remote.py` (0 and 2 pass; 1, 3, 4, 255 fail; live
  here never uses the way in).
- **A phase script's own `migrate`** (382's V-A shape) is not reachable
  through the fixed list. The skill says so; such a phase adds an operation
  first.

**244G's scanner** over `tests/`: 0 hits. Its scope is assertions on Python
source (a `read_text` naming `.py`); a planted case of that shape was found,
so the 0 is a real one. `test_phase384_install_remote.py` reads a shell
script, outside the scanner's scope; its assertions are on the heredoc
blocks and code lines, and the mutation run is their check.

**A guard blocked a command:** a `sed -i` on a scratch file (the scanner's
planted case) was refused by the edit guard, which blocks `sed -i`
wherever it points. Rewritten with the Write tool; the guard is unchanged.

### 2026-10-20 — Mutations 40/40 red

`384_mutate.py` (383's harness): 40 mutations over the dispatcher (14), the
Mac's client (8), the video check (3), verify_phase.sh's checks 8 and 9
(3) and the installer (12); each turned its test file red
(`384_mutate.out`, `40/40 red`). Writing the plan found one gap first: no
test made a soft-deleted video that still serves fail, so M2 would have
survived; `test_a_soft_deleted_video_that_still_serves_fails` was added
before the run. The floor 10998 → 10999 for it.

### 2026-10-20 — The operator's setup: the Mac's part, the tailnet's rules

**The Mac's part, ALL GOOD** (the operator, and the advisor session's
report). The operator's first copy of the rules took the whole web page, so
the advisor saved them from inside the editor to
`~/motodiag_tailnet_rules_before.txt` (the default policy: allow-all grants,
the default Tailscale SSH check rule); the block's first line was not run.
The operator made `~/.ssh/motodiag_ops`, typing the passphrase; it is in
the keychain (`ssh-add -l`: "motodiag-ops, the Mac"; SHA256
`szamQPJVmUH7UPyQ6mZYjXT95Ly+gdiLYG1l2Fkj4ok`).

**The tailnet's rules** (`384_tailnet_rules.hujson`, written from the saved
copy): the allow-all grant became "each of the operator's devices reaches
the operator's other devices" (`autogroup:member` → `autogroup:self`) plus
the Mac alone to `tag:motodiag-ops` on `tcp:22`; `tagOwners` and a `hosts`
entry for the Mac added; the Tailscale SSH rule unchanged; four rule tests
(the Mac accepted on the tag's port 22; the PC's Windows node and the iPhone
denied; the operator's devices still reach the PC's 443). The operator saved
them in Access controls > JSON editor (`console.tailscale.com/admin/acls/file`;
the console has moved, per the advisor), with no error, so Tailscale's own
check of the four tests passed. `/healthz` over the tailnet answered at
schema 87 afterwards, from the advisor at 22:04 and from here.

**Decided:** the installer takes the Mac's public key as a second argument,
so the PC's step is one paste block and nothing the install runs (apt,
Tailscale's installer) can read the key from the terminal first. Without it,
the script still asks.

**A guard blocked a command:** `git commit` and `git push` in one command
were refused by the push guard (it judges the push before the commit
exists). Run as two commands; the guard is unchanged.
