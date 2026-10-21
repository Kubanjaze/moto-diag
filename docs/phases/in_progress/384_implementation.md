# Phase 384 — The Mac runs the PC's steps

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-20

---

## Goal

Since 382, live is on the home desktop and every deploy step ran there by
hand; in 383 the operator carried each step between the two computers. The
operator's words, 2026-10-20: "cant everything i do on the mac just
automatically get done on the pc?" Their pick: a builder on the Mac does the
PC's steps over the tailnet, and the operator only approves (382's option 1C,
whose two costs the operator now accepts).

The operator's picks at Step 0 (verbatim in the log): **1A, 2A (i), 3A**:
- **1A:** an SSH server inside Ubuntu, listening only on the tailnet address
  of a second Tailscale device in Ubuntu, `motodiag-ops`; the Mac proves
  itself twice (the tailnet's rules, and a key accepted only from the Mac).
- **2A:** the key runs a fixed list of named operations and nothing else;
  **(i):** `verify_phase.sh`'s live check, run on the Mac, goes through it.
- **3A:** the PC never commits; the Mac fetches the files the PC writes and
  commits them under its own guards.

Two proofs the operator added after the picks, in their words: "(1) after
the PC restarts with nobody signed in, the Mac can still get in, the same
test 382 did for the server; (2) only the Mac can reach the door, not other
devices on my tailnet: for example, from the PC's Windows side, an attempt
on port 22 of motodiag-ops must fail."

## Logic

### The way in (1A) — `ops/desktop/install_remote.sh`

Run once on the PC by the operator, with sudo, from the development
checkout. In order, and refusing to go on at any step that fails:
1. **Tailscale inside Ubuntu,** from Tailscale's own package repository;
   `tailscale up --hostname=motodiag-ops --advertise-tags=tag:motodiag-ops
   --accept-dns=false --ssh=false` (the operator signs in once in a
   browser). A tagged device's key does not expire. `--accept-dns=false`
   leaves Ubuntu's own name lookups as they are; `--ssh=false` keeps
   Tailscale's own SSH off (S0-2: it cannot hold a fixed list).
2. **OpenSSH,** listening on the device's tailnet IPv4 address only, through
   a drop-in for `ssh.socket` (`ListenStream=` cleared, then
   `ListenStream=<that address>:22`, `FreeBind=yes` so it binds at boot
   before Tailscale has the address). The home network has no such address,
   so it cannot reach the server at all.
3. **`/etc/ssh/sshd_config.d/10-motodiag-ops.conf`** (a drop-in read before
   the main file, so its first values win): `AllowUsers lilcu`,
   `AuthenticationMethods publickey`, `PasswordAuthentication no`,
   `KbdInteractiveAuthentication no`, `PermitRootLogin no`,
   `DisableForwarding yes`, `PermitTTY no`,
   `ForceCommand /usr/local/libexec/motodiag-remote`.
4. **The key:** the operator pastes the public half; the script accepts one
   `ssh-ed25519` line and writes `~lilcu/.ssh/authorized_keys` as
   `restrict,from="<the Mac's tailnet address>",command="/usr/local/libexec/motodiag-remote" <key>`.
   It refuses to replace an existing file it did not write.
5. **The dispatcher** installed root-owned at
   `/usr/local/libexec/motodiag-remote`, so a branch pulled on the PC cannot
   change what the key may run; only a fresh install can.

**The tailnet's rules** (the operator pastes them in the admin console): the
current rules plus `tagOwners` for `tag:motodiag-ops`, a `hosts` entry for
the Mac's tailnet address, and one grant: from the Mac only, to
`tag:motodiag-ops`, `tcp:22` only. If the current rules allow every device
everywhere, that grant is replaced by "each of the operator's devices
reaches the operator's other devices" (`autogroup:member` →
`autogroup:self`), which keeps every path the app uses and leaves the tagged
device to the Mac alone. Written from the rules the operator copies out, not
guessed.

### The fixed list (2A) — `ops/desktop/motodiag_remote.py`

The forced command reads `SSH_ORIGINAL_COMMAND`, splits it with `shlex`, and
runs one operation from the list or refuses (exit 64) without running
anything. Every request and its outcome is appended to
`~/motodiag/remote.log`. Arguments are held by patterns: a phase id
`^\d{3}[A-Z]?$`, a commit `^[0-9a-f]{40}$`, a label `^[a-z0-9_-]{1,32}$`, a
kind `dryrun|live`. No argument reaches a shell.

| operation | what it runs on the PC |
|---|---|
| `status` | read only: host, user, live.json, live's schema and integrity, both checkouts' commit and cleanliness, the service, `/healthz`, the backups |
| `dryrun <phase> <commit>` | the checkout at that commit, then `deploy.py dryrun`; the written diff moves to the outbox |
| `apply-live <phase> <commit>` | the same, `deploy.py apply-live`; the live diff moves to the outbox |
| `verify-live <phase> <commit>` | the same, `deploy.py verify-live` |
| `live-check <phase> <commit>` | `verify_phase.sh`'s live check: schema and row count, read only, then `verify-live` when the phase has a dry-run diff |
| `media-check <commit>` | `media_check.py` at that commit (below) |
| `backup <label>` | `deploy.py backup <label>` |
| `backups` | the backup folder, listed |
| `fetch <phase> <kind>` | the outbox file and its sha256, as JSON |
| `api-stop`, `api-start`, `api-restart` | `sudo -n systemctl … motodiag-api.service` (382's rule) |
| `server-pull` | `git -C ~/motodiag/server pull --ff-only`, refused unless on `master`; its commit |

**"The checkout at that commit":** `git fetch origin`, refuse unless the
development checkout is clean, `git checkout --detach <commit>`, refuse
unless HEAD is that commit. The Mac names the exact commit it has pushed, so
the PC runs what the Mac sees, never "whatever the branch is now".

**The outbox** is `~/motodiag/outbox/`, outside the checkout: the PC's tree
stays clean, so the next checkout never meets an untracked copy (a decision;
Step 0 said the copy would be removed after the Mac's commit, which needs
one more operation for the same effect).

### The Mac's side — `.claude/skills/deploy/remote.py`

The Mac's `live.json` gains `"remote": {"ssh": "lilcu@motodiag-ops",
"key": "~/.ssh/motodiag_ops"}`. `remote.py <operation> [args]` runs
`ssh -o BatchMode=yes -o IdentitiesOnly=yes -o IdentityFile=<key>
-o UseKeychain=yes -o StrictHostKeyChecking=accept-new <host> <operation>`:
- for `dryrun`, `apply-live`, `verify-live`, `live-check`, `media-check` it
  adds the commit itself, and refuses (exit 4) unless the tree is clean and
  `origin` holds HEAD;
- `fetch` writes the file into `docs/phases/in_progress/` only when the
  sha256 of what arrived equals the one the PC sent, and prints both;
- no remote in live.json, or no key file: exit 4, as live.py does.
`accept-new` pins the server's host key on first use; the first use runs
over the tailnet, whose WireGuard keys already prove the peer.

### verify_phase.sh (i)

Check 8: when `live.py` refuses (exit 4) and `remote.py` has a remote, the
check runs `remote.py live-check <phase>` and takes its exit (0 or 2 pass,
anything else fails, as now). With no remote it still fails. Check 9 lists
the backups through `remote.py backups` the same way.

### The video proof — `.claude/skills/deploy/media_check.py`

382's `382_video_serve.py`, as a reusable tool: live copied read-only by the
backup API into a temporary folder, the API built in-process on that copy
with `data_dir` set to live's own folder, each video's owner standing in for
an API key (no key made, live never written), and each video fetched through
`GET /v1/sessions/{id}/videos/{video_id}/file`. A video not soft-deleted
passes only with a 200 whose sha256 equals its file's; a soft-deleted one
only with a 404. Exit 0 only when every row passes.

### The deploy skill

"Where live is" and "The sequence" say the Mac drives each step through
`remote.py`, with the operator's approval still in the phase log before any
live change, and `apply-live` still refusing on its own terms (K18).
`383_desktop_steps.md`'s three hand blocks become: dry run and fetch;
stop, apply, verify, fetch; server-pull and start.

## Tests

- `tests/test_phase384_remote_dispatcher.py`: each operation maps to its
  commands, run through a stand-in; each refusal (an unlisted name, a
  second command after `;`, an empty request, `sftp`/`scp`/`internal-sftp`,
  a phase or commit or label off its pattern, an extra argument) runs
  nothing; the checkout refuses a dirty tree and a HEAD that is not the
  commit; a dry run's file moves to the outbox; `fetch` returns the file and
  its sha256; every request is logged.
- `tests/test_phase384_remote_client.py`: the ssh command carries
  BatchMode, IdentitiesOnly and the key; a missing remote or key exits 4;
  the commit is added, and a dirty tree or an unpushed HEAD refuses; `fetch`
  writes only on an equal sha256, and refuses an unequal one.
- `tests/test_phase384_install_remote.py`: the installer's sshd and socket
  settings, the key line's three restrictions, and the dispatcher installed
  root-owned outside the checkout.
- check 8 and 9 through the remote, with a stand-in `remote.py`: passes on
  0 and 2, fails on 1, 3 and 4; with no remote, fails as before.
- `tests/test_phase384_media_check.py`: a fixture database and data folder:
  a served file equal passes; a missing file, a changed file and a
  soft-deleted video served each fail.
- A mutation run over the guards (the allowlist, each pattern, the clean
  check, the commit check, the sha256 check, BatchMode, check 8's
  fallthrough, the sshd lines).

## The proofs on the real machines

1. **Doors that must fail:**
   - from the Mac, port 22 on the PC's home IPv4 and home IPv6 addresses;
   - from the Mac with Tailscale disconnected (not on the tailnet), port 22
     on `motodiag-ops`;
   - from the PC's Windows side, port 22 on `motodiag-ops` (the operator's
     one paste block);
   - from the Mac, a password login, and a key that is not the Mac's.
2. **Outside the list, refused:** an unlisted command, `status; id`, an
   interactive login, `sftp`, `scp`, a forwarded port, an argument off its
   pattern.
3. **End to end, from the Mac, with only one use of the app by the
   operator:** `status`; `verify-live 383` after the operator has looked at a
   page or two and changed nothing (the API's `api_keys.last_used_at` set
   aside on live, nothing else differing); `media-check`, six videos;
   `dryrun 384` with an empty scope, fetched and committed under the guards;
   `backup`; `server-pull` and `api-restart`, `/healthz` at schema 87.
   `verify-live 383` runs before any new backup, so retain-5 cannot take its
   backup first.
4. **After a restart with nobody signed in** (the operator restarts the PC
   and does not sign in): from the Mac, `status` answers and `/healthz`
   answers.

## Non-goals

- Builders and the regression of record stay on the Mac.
- No migration and no change to live (a rule-1 stop if one appears).
- `apply-live` through the way in is proved with stand-ins only: there is no
  migration to apply. Its first live use is the next data phase's.

## Planned items

- [ ] the installer, the socket and sshd settings, the tailnet rules text
- [ ] the dispatcher and its tests
- [ ] `remote.py` and its tests; the Mac's live.json
- [ ] verify_phase.sh checks 8 and 9 through the remote
- [ ] `media_check.py` and its test
- [ ] the deploy skill and its CHANGELOG
- [ ] the mutation run
- [ ] the operator's one sitting
- [ ] proofs 1 to 4
- [ ] the regression of record, verify_phase.sh, close-out
