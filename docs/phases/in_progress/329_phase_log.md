# Phase 329 — phase log

**Status:** In progress. Started 2026-11-27 by the builder session K153
names (the home desktop's main chat), from
`docs/prompts/329_self_serve_sign_up.txt` and draft pull request 99.

## 2026-11-27 18:40 UTC — why a builder session, and where it starts

**The operator's words.** K153 (2026-11-27): "go with your picks": a
builder session builds 329 from its draft, pull request 99; the advisor
reviews on the Mac; the operator merges. K152 holds the answers of
2026-11-25 (the form on getmekno.com/signup, Resend, pay first with a
14-day refund by hand); K141 and K150 the two switches.

**Where it starts.** A fresh clone of `master` at `135bde2`, in the cloud.
Branch `phase-329-self-serve-signup`, new, from master. Row 329 made 🚧 in
the first commit (`a37b34a`), pushed before Step 0.

**The guards in this session.** The session was started in the clone's
parent directory, so `.claude/settings.json`'s hooks (the push guard and
the edit guard) do not load for it. Each is run by hand instead:
`wholetree.sh` before every commit, read by its exit code on its own, and
`roadmap_check.py` before every push. No `sed -i` or redirect writes into
`src/` or `tests/`.

**The cloud venv.** The first whole-tree run failed 5 tests of
`test_phase293_manuals_api.py` on pypdf 7.0, the venv's own install; pinned
to live's pypdf 6.14.2 and pypdfium2 5.15.2 as 409 did, and FastAPI to
0.136.3 (F287, F312). Second run: `wholetree fast: PASSED — 3049 passed,
11 skipped`, exit 0.

## 2026-11-27 19:00 UTC — Step 0 and v1.0, before any code

`329_step0.md` written: PR 99 covers the prompt's server steps; nine
measured items, among them a form-action problem in PR 99's pages (the
browser checks a form's redirect targets too, so the staged policies would
block the end of every form) and the wizard's different `owner_user_id`,
filed as F314. Classification: an extension of PR 99.

`329_implementation.md` v1.0 written: PR 99 by a merge, the Resend sender,
the email failures, the per-address cap, the 30-day purge, the form-action
fix, the site's pages, privacy 1.3 in the operator's words (asked once on a
card), eight blocks. Committed and pushed before any code.

**Decided here under rule 1, with the reason:** 5 emails an hour per
address (the pick offered on 2026-11-25, enough for a person retrying, too
few to use the server to mail-bomb someone); the form offers Individual and
Shop only (the site says "talk to us" for Company); no app change (K152:
the app only signs in; a web sign-up link inside the app touches Apple's
rules, which 410 reads first).

**Privacy 1.3's words.** The operator chose "Yes, use them as written" on
the card in this session's thread (2026-11-27, 18:58 UTC), for the three
lines quoted in v1.0 Logic 8 as posted: Resend in "The services it goes
to", sign-ups with the 30 days in "What we keep", and the website's forms.
