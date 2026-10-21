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
