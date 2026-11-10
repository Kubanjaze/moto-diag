# Phase 402 — phase log: customer share links off, and the Stripe return pages (K74)

**Status:** In progress

**Built 2026-11-09** by the Chief Engineer, in the fleet's fence, on
`phase-402-share-links-off-and-return-pages`, from the plan
`402_implementation.md` v1.0 (approved by the Executive Officer on issue
#61). No migration; this phase closes out on the branch.

## 2026-11-09 — start

- **The row's status.** The prompt
  (`docs/prompts/402_share_links_off_and_return_pages.txt`) says row 402 is
  🔲; on master it already reads 🚧, put there by K76's commit ("row 402, 🚧
  on master from this commit"). The row is left 🚧 until the close-out; the
  difference is recorded here and changes nothing.
- **K77**, the operator's words, character for character: "Mekno,
  getmekno.com". The sentence of its record this phase rests on: "It is the
  site that introduces the app, links to its download, and serves K74's
  thank-you page, so it replaces K75's "free host for now"."
- **K78**, character for character: "402 is an extension, not a reshape:
  its two settings are new and their defaults keep today's behaviour; the
  only rule it changes is the live start-up check that K74 already
  approved. Correct the fleet's report and let the fleet build it."
- **K79**, character for character: "402: while share links are off, every
  link stops opening, old ones too."
- **The open route**, named from the code: `GET /v1/share/{token}`,
  `view_shared_report` in `src/motodiag/api/routes/share.py`. Minting is
  `create_session_share` in the same file.

## 2026-11-09 — the build: items 1 to 6

- **Item 1.** `config.py`: `share_links_enabled` (default true),
  `stripe_return_page_url` (default empty), the module tuple
  `STRIPE_RETURN_URL_FIELDS` naming the six, and the after-validator
  `apply_stripe_return_page`. Measured before relying on it: pydantic-settings
  does put environment-given fields in `model_fields_set` (a `Settings()`
  with `MOTODIAG_STRIPE_RETURN_PAGE_URL` and `MOTODIAG_CHECKOUT_CANCEL_URL`
  set gave five of the six as the page and `checkout_cancel_url` its own),
  so the plan's fallback (reading the environment by name) was not needed.
- **Item 2.** `public_url.py`: `startup_public_url_problems(settings)`;
  `check_public_base_url` unchanged. `serve.py` calls it, prints the plan's
  one line to stderr when the switch is off, and keeps its loop and its
  refusal as they were.
- **Items 3 and 4.** `share.py`: `SHARE_LINKS_OFF_MESSAGE`; the mint answers
  403 before the ownership check; the open route answers the "Report links
  are off" 404 page before `resolve_share`. The page's body writes the
  apostrophe as `&#39;`, as the route's other pages do; it renders as the
  plan's sentence.
- **Item 5.** The mint declares its 403; the 404's description gains one
  sentence. `tests/test_phase205_gate11.py` passes against the committed
  snapshot (`../moto-diag-mobile/api-schema/openapi.json`), with
  `tests/test_f64_public_url.py`, `tests/test_phase200_share.py` and
  `tests/test_phase191b_serve_migrations.py`: 78 passed, none changed.
- **Item 6.** `tests/test_phase402_share_links_off.py`, 59 tests, all pass.
  - **Against master's code** (`402_mutate.py --old`: master's four
    modules, with stand-ins only for the names the tests import, keeping
    master's behaviour): **18 failed, 41 passed.** The 18 are every test of
    a changed behaviour; the 41 are the controls and pins: the 32 identity
    cases, and nine more (the six's defaults, the six named, the page empty
    with one given, mint on, the message's text, list and revoke, an
    unknown token on, prod with the switch on still blocking, and serve
    refusing with the switch on).
    One test first mixed a new setting's default into the six's defaults
    control and went red on master for that reason; it was split in two
    before this count.
  - **Mutations** (`402_mutate.py`, on a copy, output in `402_mutate.out`):
    **13/13 red**, the plan's nine plus four: a refused open that still
    records a view, serve calling the old check directly, the mint refusing
    after the ownership check, and the 403 not declared.
- **The floor.** A diff of collected ids against master at `67ef2da`
  (12513), each side read with its own `src/`: +59 −0, all in the new file.
  `COLLECTED_TEST_FLOOR` 12513 → 12572.
- **A guard block, recorded:** the edit guard refused a debugging `cp` into
  a folder named by a shell variable ("cannot tell where `cp` `$W/`
  writes"). Re-run with a literal path under `/fleet/run`; the guard is
  unchanged.

## 2026-11-09 — item 7: the documents

`README.md` (two rows in the settings table), `docs/guide/install.md`
("Before it faces anything real"), `docs/guide/api.md` ("Share links" gains
a paragraph on the switch; "Deployment" gains both settings),
`docs/launch-checklist.md` (the prod settings block), `docker-compose.yml`
(the commented example) and `docs/guide/payments.md` (a new section, "The
thank-you page"). The finish line's `git grep -n
MOTODIAG_SHARE_LINKS_ENABLED -- README.md docs/guide
docs/launch-checklist.md docker-compose.yml` finds README.md 1,
docker-compose.yml 1, docs/guide/api.md 2, docs/guide/install.md 1 and
docs/launch-checklist.md 1.
