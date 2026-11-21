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
