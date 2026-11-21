# Phase 408 — phase log

**Status:** In progress

## 2026-11-21 16:02 UTC — started, in the operator's project thread

The operator, 2026-11-21, after the advisor put row 408 and its prompt on
master as `4b71dac`: "do this as a thread or in this project so we keep it
altogether". So the prompt, written for a session on the Mac, runs as a
project thread in a cloud checkout. This branch is
`phase-408-the-sites-basics-and-trust`, from `4b71dac`. Row 408 goes 🚧
before Step 0, in the plan commit.

**A guard block before the phase, recorded as rule 6 asks** (from the
prompt): on 2026-11-21 the push guard refused the advisor's first push of
this row's record, because the command sent its output to a file and the
guard read the file's name as a branch it could not resolve. Nothing was
pushed; it went again as a plain push. The guard was not changed.

## 2026-11-21 16:45 UTC — Step 0 and v1.0

- The cloud container cannot reach getmekno.com (its proxy answers 403 for
  the host). The thread read the site instead through the Mac's built-in
  browser pane, and the zip through the operator's grant of the Mac's
  `~/Downloads` (read only; nothing there was changed).
- The zip's nine served files equal the live site by sha256, all nine, and
  its `_headers` equals the live headers (`408_step0.md` S0-2). The zip is
  the source.
- The "Hears the problem" card has no live path behind it (S0-3): rewritten.
- Classification: extension.

Decided here (rule 1, no stop): the FAQ goes on the home page under
`id="faq"`, not at `/faq/`, so the sitemap stays at four pages; a
non-getmekno address in the legal texts stays plain text, so the pages link
no new outside host; the Organization's `logo` is a 512×512 PNG beside the
1200×630 Open Graph image.

**The cloud checkout's test environment, set up before the plan commit.**
The first whole-tree run failed for the checkout, not the code: a shallow
clone (history the closeout and fleet tests read), missing extras
(`fastapi`, `stripe`) and no sibling `moto-diag-mobile`. Fixed by fetching
master's whole history, installing `.[all,dev,push,server,backup,payments]`
into `.venv`, and a read-only clone of the mobile repository beside this
one. pip then chose FastAPI 0.165.0, under which
`tests/test_phase244J_guidance_surface.py` finds only the four docs routes
and `tests/test_phase403_app_copy.py`'s generated schema differs from the
app's copy. Measured: 0.124.4 registers the routes but makes the other
schema; 0.135.0 passes both (124 routes, and `d43910b0…`, the app's copy);
0.140.0 and 0.150.0 make the app's schema but register 4 routes. The
checkout uses 0.135.0. `pyproject.toml` says only `fastapi>=0.110`, so a
fresh install today gets a version this suite fails on; that is filed at
close-out, not fixed here. With that, `wholetree.sh` passed, exit 0.

## 2026-11-21 17:00–17:45 UTC — the build

Each commit after `wholetree.sh`, run on its own, exit 0:
- `a59b876`: `site/` = the zip's ten files, unchanged; the test pins all ten.
- `e274e4c`: the terms and privacy 1.0 pages from `scripts/site_build.py
  legal`; `docs/legal/README.md`'s Publishing names `site/`. Item 14 first,
  as K109 orders.
- `65f5c62`: HSTS, the one header added.
- `38fffd8`: the four pages' heads, the sitemap and robots.txt, `og.png` and
  `logo.png` (`scripts/site_images.py brand`, Pillow 11.3.0 in a separate
  environment, Inter Bold), the home page's words and data.
- `eeb953f`: the mutations, 30/30 red. A first run left the README check
  green (it found `site/` elsewhere in the file); the check now reads the
  Publishing section, and the run is 30/30. COLLECTED_TEST_FLOOR 13099.
- `303579a`: F287.

Decided here (rule 1, no stop): the FAQ's accuracy answer says only what
the phone app shows (`SessionDetailScreen.tsx`'s `DiagnosisCard`: a
diagnosis, its severity and its confidence), not the draft's ranked causes
with evidence; the data answer leaves "below" out of its quote; the top
paragraph's "record how it sounds" goes, for the card's reason. Each went
to the operator as before and after.

`wholetree.sh --full` at `eeb953f`: 5424 passed, 37 skipped, exit 0.

## 2026-11-21 18:10 UTC — the operator's yes, and a second builder

The operator, through the project chat, "yes yes yes" to three questions:
the new wording is good; push 408 and open the pull request; the name and
the line "I'm building Mekno with a few shops, one stuck bike at a time.
Every message to support@getmekno.com comes to me." The photo: the
operator's `founder.jpeg` in the Mac's Downloads, made `site/founder.jpg`
by `site_images.py photo` (400×400, no Exif). Commit `150f057`: the founder
block and `founder` in the Organization data; mutations 32/32;
COLLECTED_TEST_FLOOR 13100.

The first push was refused: `phase-408-the-sites-basics-and-trust` already
held the advisor's Step 0 and v1.0 (`468b789`), after K117 on master ("build
408 on the Mac", 17:36 UTC). Nothing was pushed to that branch. This work
went up as `phase-408-thread-build`, and the operator was asked who
finishes 408: "This thread finishes it" (decision card, 18:17 UTC). The
advisor stopped and recorded K118 (`bb8b112`). Master merged in twice
(`2164c64`, `74c563c`), docs only, clean.

## 2026-11-21 18:37–19:59 UTC — a full run in the cloud

`wholetree.sh --full` at `2164c64`: 5425 passed, 37 skipped, exit 0. Then
`regression.sh` there: 13006 passed, 5 failed, 51 skipped, 38 errors (81
min). The 38 errors and one failure are `test_phase388_fence_boundary.py`
(no bwrap); three are `test_phase257_orchestrator_guards.py` (no osacompile,
no Subconscious login); these pass on the Mac and skip in the fleet's fence.
The fifth is bug fix #1. Not of record; the regression of record ran on the
Mac.

## Bug fixes

### Bug fix #1 — 2026-11-21 — a test's planted date became a real one

**Issue.** The first full run on this branch (at `2164c64`, after master's
K117 merged in) failed
`tests/test_phase392_plan_order.py::TestCheckRefuses::test_each_on_its_own_copy[as-of-undated]`
with "the dated entry of 2026-11-21 does not cite K99". It fails on master
too, from `c144fa7` on, in a checkout of master alone.

**Root cause.** The test plants "As of 2026-11-21, K99." as a date with no
entry in the plan of record's changes. On 2026-11-21 the plan of record
gained an entry with that date (K117's, then K118's), so the planted date
stopped being one with no entry, and `plan_order.check` gave its next
refusal instead.

**Fix.** The planted date is 2001-01-01, which no entry can carry; the
refusal it tests is unchanged.

**Files.** `tests/test_phase392_plan_order.py`.

**Verified.** The file's 49 tests pass; with the old date, the case fails as
above.

**Commit.** `d3b0677`
