# Phase 409 — phase log

**Status:** In progress. Started 2026-11-27 by the builder session K149
names (the home desktop's main chat), from
`docs/prompts/409_a_public_web_address_for_the_server.txt`.

## 2026-11-27 02:35 UTC — why a builder session, and where it starts

**The operator's words.** K149 (2026-11-26): "409: B": a builder session
builds 409 from its draft, pull request 98, with the six answers of
2026-11-25 unchanged; the advisor reviews; the operator merges. The K149
block ran on the Mac and ended ALL GOOD: K149 on master as `a238aa6`,
issue 104's comment posted, its labels `mission`, `needs-hands`,
`step0:done`.

**Where it starts.** A fresh clone of `master` at `a238aa6`, in the cloud.
Branch `phase-409-public-address`, new, from master. The fleet's branch
`phase-409-a-public-web-address-for-the` is the fleet's, so nothing is
pushed to it; its Step 0 commit `4b31ded` comes in by a merge.

**The guards in this session.** The session was started in the clone's
parent directory, so `.claude/settings.json`'s hooks (the push guard and
the edit guard) do not load for it (CLAUDE.md, "Start sessions at this
repository root"). Each is run by hand instead: `wholetree.sh` before
every commit, read by its exit code on its own, and
`pre_push_guard.sh`'s checks before every push. No `sed -i` or redirect
writes into `src/` or `tests/`; edits go through the editor.

## 2026-11-27 02:50 UTC — Step 0, the builder's section

Written into `409_step0.md` below the fleet's report. What it found:
- PR 98 merges onto `a238aa6` with no conflicts, and its tests with 210's
  pass, 146, on FastAPI 0.136.3 (live's line).
- On FastAPI 0.165.0, which the unpinned `fastapi>=0.110` installs today,
  three route-walking tests fail; to be filed.
- uvicorn 0.54 takes the right-most untrusted forwarded address, so a
  caller cannot pick their own bucket through Cloudflare; the desktop's
  version is read by the first block.
- The server takes videos up to 512 MB, so in the app it is videos, not
  manuals, that meet Cloudflare's 100 MB; the app uploads no manuals.
- The login guard's name-wide hold can lock a name's real owner out while
  a stranger guesses at it; written down, kept as built.

Classification: an extension of PR 98's reshape.

## 2026-11-27 03:05 UTC — v1.0, before any code

`409_implementation.md` v1.0 written: PR 98 by a merge, the launch check's
ninth condition, the privacy policy's version 1.2 (the operator's yes on
the words, asked once), the app's half, eight blocks. Committed and pushed
before any code, with the ROADMAP row saying so.

**The whole-tree command before this commit.** First run: 6 failed. Five
were `tests/test_phase293_manuals_api.py` on pypdf 7.0 (`add_js` removed),
the cloud venv's own install; live runs pypdf 6.14.2 and pypdfium2 5.15.2,
so the venv was pinned to those. One was
`tests/test_phase379_wholetree_output.py` under that run's load; it passed
alone. The finding_check's B2 also caught v1.0 citing the next F-number
before it was filed; the sentence now names the script instead. Second
run: `wholetree fast: PASSED — 3048 passed, 11 skipped`, exit 0.
