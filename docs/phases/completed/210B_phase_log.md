# Phase 210B — phase log

**Status:** Complete. Started 2026-11-26 by the advisor session on the
Mac (K145, K146, K147), and closed the same day. Built by the operator's
own session in `moto-diag-mobile`, from
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

## 2026-11-26 — steps 3 to 6, and the close-out

**Step 3, build 1 to TestFlight.** The block is
`210B_blocks/3_testflight_upload.txt` (sha256
`be69159d92bf40e1f48020786f6598d679761955e8665bd068293e247aeb9cf6`).
- Measured on the Mac before it was written:
  - no `/tmp/envfile`, and 489 GB free;
  - the line the app's release check prints, from the cable build's log;
  - version 1.0, build 1;
  - the frameworks' lowest iOS versions (15.0, 12.0 and 15.1), none above
    the app's 15.1;
  - seven privacy manifests in the app, and
    `ITSAppUsesNonExemptEncryption` false;
  - no Apple Distribution identity on the Mac: Xcode makes or uses one in
    the cloud when it exports;
  - the export settings that Xcode 27.2's `-help` lists.
- Tested first in a scratch clone of the app at `3fa252b`, with stand-ins
  for `xcodebuild` and `caffeinate`: 18 cases. Six breaks planted on
  purpose each turned it red:
  - the live-server check removed;
  - Xcode allowed to change the build number;
  - the export without `-allowProvisioningUpdates`;
  - the last clean-folder check removed;
  - a device destination;
  - the version check removed.
- The operator ran it on the Mac, and it ended ALL GOOD: "Built: Mekno
  1.0, build 1 (com.getmekno.app), with its icon, pointed at the live
  server.", then Xcode's "Upload succeeded" at 15:12 EST.
- Read by the advisor in the operator's Chrome at 15:39 EST, clicking
  nothing: TestFlight's iOS builds show version 1.0, build 1, "Ready to
  Submit", "Expires in 90 days", and no Missing Compliance. 90 days from
  2026-11-26 is 2027-02-24.
- Apple's email about build 1, at 20:13 UTC, said the delivery succeeded
  and named ITMS-90683: a missing `NSLocationWhenInUseUsageDescription`.
  The operator opened Phase 210C for it (K148).

**A guard refused one command.** At about 15:05 EST the edit guard
refused the advisor's loop over those planted breaks. A redirect wrote to
a path held in a variable (`ctl_$1.log`); the guard cannot tell where that
writes, and asked for a literal path. The loop ran again with literal
paths. The guard was not changed.

**Step 4, the testers, rehearsed on the operator's own phone.**
- The operator made the first internal group in App Store Connect, with
  build 1. Its "Automatic for Xcode Builds" box stayed ticked. Apple does
  not let that change after creation; a group's name can change.
- At the operator's "can you just add me bruh", the advisor added the
  operator as its one tester, in the operator's Chrome, at about 16:32
  EST.
- The operator signed in on the TestFlight copy, on live. For that, the
  advisor wrote a read-only block listing live's users, in case main chat
  did not have the operator's username, and tested it first (4 cases;
  printing a password hash and a write that changes a row were both
  caught). It was not needed, and it did not run.
- The rehearsal passed. The phone shows Mekno with TestFlight's dot. App
  Store Connect's All Testers lists the operator: Internal, "Installed 1.0
  (1)", iOS 27.2.1. The app is signed in on live.
- At the operator's "you go into my browser and do those steps for ya
  boi", the advisor, in the operator's Chrome at about 16:43 EST:
  - renamed the first group "First look": the operator only, automatic,
    build 1;
  - made a second internal group, "Shop one": no testers yet, build 1,
    "Manual for Xcode Builds", read back on its Settings tab.
- Not done: the shop's people. Each needs an App Store Connect login
  first, on shop one's day.

**Step 5, the Tailscale rule,** at the operator's "yes, save it", after
the advisor showed the exact change and what it opens. Typed by the
advisor in the operator's Chrome, on a fresh load of the policy file:
- `hosts` gained `"motodiag-desktop": "100.75.113.50"`;
- `grants` gained `{"src": ["autogroup:shared"], "dst":
  ["motodiag-desktop"], "ip": ["tcp:443"]}`, under the comment "Phase 210B
  (K145): people the desktop is shared with reach only its web address,
  port 443.".

Save ran the four existing tests (Phase 384's) and said "Saved tailnet
policy file", at about 16:51 EST. Tailscale put the new grant on several
lines. It was read back on a fresh load. Nobody is shared yet, so the rule
reaches no one until the operator shares the desktop with a person.

**Step 6** ran only as the rehearsal on the operator's phone (step 4). The
shop's phones are shop one's day.

**The close-out.**
- `wholetree.sh --full` on `85315cb`: passed, 5539 passed and 15 skipped
  (1622 s wall). The record was written.
- `regression.sh`, first run, 16:59 to 18:10 EST: failed, not of record.
  13271 passed, 1 failed, 49 skipped, 0 errors (70 min 57 s, exit 1).
  - The failure was
    `tests/test_phase258_gate14.py::TestRegression::test_gate_13_still_passes`.
    Its nested serial pytest of `tests/test_phase250_gate13.py` timed out
    after 1800 s.
  - The advisor's 210C checks were running beside it (load 20 to 27).
  - It belongs to F289's family, a nested run outliving its time. It was
    not told apart from plain load.
- Second run, from 18:10 EST on the quiet Mac, with nothing heavy beside
  it:

Regression of record: 13272 passed, 0 failed, 49 skipped, 0 errors at `85315cb` (39 min 24 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase390_space.py:327: bubblewrap is the desktop's
Line coverage of record: 88.66% at `85315cb` (the pin is 88.00%)

- No bug-fix register: none was needed. No code in this repository changed
  in this phase.
- Master's three commits since this branch began are merged in, documents
  only: `5c90cc8` and its merge `47ea328` (row 409), and `77fe1bd` (row
  210C, K148, 210C's prompt). The one conflict was row 210C beside row
  210B, which both sides had changed to the same text. The merge takes
  master's file, which holds every ROADMAP change this branch made.
- The app's tests failed on timing under load once more, in 210C's review:
  two hook tests, each once, with "window.dispatchEvent is not a
  function". This is the same kind of failure as step 1's TermsModal
  timeout. A finding for both is filed at 210C's close-out.
