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
