# Phase 210B — phase log

**Status: in progress.** Started 2026-11-26 by the advisor session on the
Mac (K145, K146, K147). Built by the operator's own session in
`moto-diag-mobile`, from
`docs/prompts/210B_the_apps_icon_name_and_day_one_fixes.txt`.

## 2026-11-26 — why this phase, Step 0 and v1.0

**How it came up.** The operator asked for Phase 210's step 3, the app on
the shop's phones, laid out read-only.
- **Step 1 of the layout:** 210's own check block ran ALL GOOD on the
  app's main `4c6c1bd`.
- **Step 2:** a new, tested block pointed the Mac's app builds at live. It
  ran ALL GOOD and moved the app's settings file, `.env`, from the Mac's
  old tailnet name to the home desktop's. Since Phase 382 that is the
  server live runs on.
- **Step 3:** the operator created the App Store Connect record: Mekno, iOS
  only, SKU `mekno-ios`, bundle ID `com.bandithero.motodiag`.
- **Then, reading the app for step 4:** the app has no icon, and Apple
  refuses an upload without one (`210B_step0.md`, S0-1).

**The operator's words.**
- K145: "I will take all your recommendations. theyre all on point". That
  was five recommendations: this phase, the name, F303 and F304, internal
  testers, and sharing only the desktop on Tailscale.
- K146: "yes use the website M, and open tailscale for me". Then "cant you
  just remake it and blow it up in a way that dont make it messy", and "so
  file that a way to be accessed when needed".
- K147: "oh word! so can you do that for me". That was the switch of the
  iOS bundle ID to `com.getmekno.app`.
  - The home desktop's main chat advised it after the record had been
    created with the old ID.
  - Apple lets a record's bundle ID change until its first build is
    uploaded, and none has been.
  - Deleting the record would not free the ID, so the record stays.
  - The change itself is the app's, in this phase (Step 0, S0-5).

**The icon.**
- Drawn by `210B_icon/make_app_icon.py`, with this repository's `.venv`
  (Pillow 12.2.0), from the 12 points of `site/favicon.svg`'s M.
- The result is 1024 by 1024, RGB with no alpha, 12951 bytes, sha256
  `09d3db160b451cf2862ef8579f7489ff67f67bac02e798b6ffe5c5a94e1f3430`.
- It is kept in `210B_icon/` beside its script, at the operator's "file
  that a way". The app's session takes it from this branch by that sum.

**The record on master: `00283d5`.** It holds:
- row 210B in progress;
- the prompt and its line in `docs/prompts/README.md`;
- K145, K146 and K147.

Checked before the commit:
- `roadmap_check.py` exit 0, and row 210B is 99 words;
- the plan-order, decisions, prompt and findings tests, 367 passed: the
  `tests/test_phase392_*.py` files, the Yeoman, continuity, legal-text,
  slips and granted-round tests, the scout, the CLI and fleet-git tests,
  and the two findings contracts;
- `wholetree.sh` fast: 3058 passed, 1 skipped, exit 0 (632 s wall, with the Mac under load).

**This branch.** It holds Step 0, v1.0, this log and the icon folder.
- **Not on "Next, in order":** the phase finishes 210's step 3, beside the
  list, so the plan of record and its pins are unchanged.
- **Tailscale, read in the admin console in the operator's Chrome, at
  their word:**
  - The rules already let each member's devices reach only their own, and
    only the Mac reach the ops login, on port 22.
  - Nobody the desktop is shared with can reach anything yet.
  - Step 6 adds one grant, for people it is shared with: `tcp:443` on the
    desktop only.

## 2026-11-26 — after the merge: the app's PR, the phone, App Store Connect and the server

**A record run of `wholetree.sh` on this branch failed once.** On
`d6d7ccf`: 1 failed, 3057 passed. The failure was
`tests/test_phase369_worker_loss.py`, `TestTheAlarmCheck`: its nested
pytest timed out at 180 s, with the Mac's load average about 21. The same
content had passed just before the commit (3058 passed, 719 s), and the
re-run passed (3058 passed, 469 s).

**The app's PR, moto-diag-mobile #15**, from the operator's own session;
its last commit was `7f2d832`.
- Re-run by the advisor on the Mac, in a scratch clone at `7f2d832`, whose
  tree `c19ac3df` is the merge's: `tsc` exit 0; `eslint` 0 errors and 150
  warnings, exit 0; `jest` 118 suites and 1345 tests passed, exit 0. The
  PR's own figures match.
- Its three extras beyond the plan were judged fine:
  - Settings' `keyboardShouldPersistTaps="handled"`, as the four other
    keyboard screens have;
  - "Manage plan" hidden while the plan is still "Checking…";
  - the 404 case also pinning "Is that a Mekno server?".
- `docs/app-store-listing.md` still says MotoDiag in its Name row and its
  description. The plan did not cover it, so it goes to the close-out, for
  Phase 410's listing work.
- Merged by the operator as `3fa252b`, 2026-11-26 19:16 UTC.

**Step 1, the cable install of `3fa252b`.**
- The operator's first run stopped at the app's tests: 1 failed, 1344
  passed. `__tests__/screens/TermsModal.smoke.test.tsx`, "shows the
  version and date", timed out at jest's 5 s limit (the file took 6.2 s),
  right after `npm ci`.
  - In the scratch clone, that file passed 5 times out of 5 on its own, and
    the whole suite passed twice, then once at `--maxWorkers=50%`.
  - The second run left out `npm ci` and ran jest at half the workers.
  - A finding is filed if the timeout comes back.
- The second run ended ALL GOOD: 1345 tests passed; the build was
  `com.getmekno.app`, called Mekno, with its icon; it installed on the
  operator's iPhone and opened. The operator: "it worked!"
- On the phone, the operator answered "yes, yes, yes, yes, done":
  - Mekno with the M icon;
  - the sign-in sheet above the keyboard;
  - the Server box in Settings above the keyboard;
  - the plan screen as planned;
  - the old MotoDiag app deleted.

**Step 2, App Store Connect.** Read by the advisor in the operator's
Chrome, clicking nothing. Mekno's App Information page already showed the
bundle ID `com.getmekno.app` ("XC com getmekno app"), on a fresh load in a
new tab. Its list offers both IDs.

**Step 2, the server's notifications.** The block is
`210B_blocks/2_notifications_check.txt`, and it only reads.
- Tested first on the Mac against stand-ins: 17 cases, and four breaks
  planted on purpose each turned it red.
- The operator ran it on the home desktop, in the Ubuntu window, and
  reported: "The notifications check ran on the home desktop and ended ALL
  GOOD. Both the running server and its settings file have no
  MOTODIAG_APNS_ settings, notifications to phones are off, and no app ID
  is named, so the new ID needs nothing on the server today. Nothing was
  changed."
- So the server needs nothing for the new ID until notifications are
  turned on. Then `MOTODIAG_APNS_TOPIC` names `com.getmekno.app`, and
  `MOTODIAG_APNS_SANDBOX` is `0`, because phones with the TestFlight app
  use Apple's main gateway.

**Next:** step 3, the build and its upload to TestFlight: version 1.0,
build 1.
