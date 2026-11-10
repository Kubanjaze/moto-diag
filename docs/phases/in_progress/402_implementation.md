# Phase 402 — Customer share links off, and the Stripe return pages (K74)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-11-09

---

## Goal

Live payments wait on a public web address the server cannot have. A live Stripe key is used only with `MOTODIAG_ENV=prod` (`refuse_live_key`, `src/motodiag/payments/stripe_api.py`), and in prod `motodiag serve` refuses to start unless `MOTODIAG_PUBLIC_BASE_URL` is a public https address a customer's phone can open (`check_public_base_url`, `src/motodiag/core/public_url.py`, called from `src/motodiag/cli/serve.py`). The server stays tailnet-only (K65), so 371's live step stops at its check and live Stripe has not been switched on (F257).

The operator answered on 2026-11-09, K74: "The six Stripe return addresses point at a plain public thank-you page; customer share links are switched off until a public front door exists; the server stays tailnet-only." K78 calls the phase an extension: its two settings are new, their defaults keep today's behaviour, and the only rule it changes is the live start-up check, for share links switched off only. K79 answers the one fork Step 0 found: "402: while share links are off, every link stops opening, old ones too."

After this phase:

1. `MOTODIAG_SHARE_LINKS_ENABLED=false` switches customer share links off. Minting a link (`POST /v1/reports/session/{session_id}/share`) and opening any link (`GET /v1/share/{token}`, old ones included) are refused with a plain message. The prod start-up check no longer asks for `MOTODIAG_PUBLIC_BASE_URL` while the switch is off. With the switch on (the default), every route and the start-up check behave exactly as today.
2. `MOTODIAG_STRIPE_RETURN_PAGE_URL`, empty by default, is one address for the six Stripe return settings. When it is set, each of the six takes it unless that one is set on its own. Empty, the six keep their defaults.
3. 371's live step (its handoff's steps 2 to 4) is rewritten in this phase's handoff with the new settings list and a check that reads the new rule, so the operator can switch live Stripe on from one paste block once the thank-you page exists.
4. F257 is closed by the close-out.

The two setting names are fixed by the prompt and K76: `MOTODIAG_SHARE_LINKS_ENABLED` and `MOTODIAG_STRIPE_RETURN_PAGE_URL`. The operator writes them in `server.env` from the prompt; this plan does not rename them.

## Logic

Causes and the census: `402_step0.md`. The row already reads 🚧 on master although the prompt says 🔲; the phase log's first entry records the difference, and quotes K78 and K79 character for character.

The open route, named from the code as Step 0 asks: `GET /v1/share/{token}`, `view_shared_report` in `src/motodiag/api/routes/share.py` (line 244). Minting is `create_session_share` in the same file (line 131). The four readers of the six return settings are `src/motodiag/api/routes/billing.py`, `src/motodiag/cli/billing.py`, `src/motodiag/payments/invoice_payments.py` and `src/motodiag/payments/connect.py`; none of them changes.

1. **The two settings.** `src/motodiag/core/config.py`, class `Settings`:
   - `share_links_enabled: bool = True`, beside `public_base_url`, with a comment naming K74 and K79.
   - `stripe_return_page_url: str = ""`, beside the six return settings.
   - A `model_validator(mode="after")`, `apply_stripe_return_page`: when `stripe_return_page_url` is not empty, each of `checkout_success_url`, `checkout_cancel_url`, `billing_portal_return_url`, `invoice_payment_return_url`, `connect_return_url` and `connect_refresh_url` is set to it unless that field's name is in `self.model_fields_set` (the field was given by the environment or the `.env` file). Empty, the validator changes nothing. If the test in item 6 shows that pydantic-settings does not report environment-given fields in `model_fields_set`, the Engineer reads the `MOTODIAG_`-prefixed names from the environment and the `.env` file instead; the rule is the same and it is a build choice, not a stop.
   - `motodiag config show` (`src/motodiag/cli/main.py`) prints every setting from `model_dump`, so both new settings and the six resolved addresses show there with no change to it.
   - **Finish line:** `Settings()` with no environment gives `share_links_enabled` true, `stripe_return_page_url` empty and the six at today's `localhost:3000` defaults; with `MOTODIAG_STRIPE_RETURN_PAGE_URL=https://example.org/thanks` and `MOTODIAG_CHECKOUT_CANCEL_URL=https://example.org/cancel`, five of the six equal the page and `checkout_cancel_url` keeps its own value.

2. **The start-up check, for share links off only.** `src/motodiag/core/public_url.py` gains `startup_public_url_problems(settings: Settings) -> list[PublicUrlProblem]`: an empty list when `settings.share_links_enabled` is false, else `check_public_base_url(settings.public_base_url, settings.env)`. `check_public_base_url` itself does not change by one character: `tests/test_f64_public_url.py` pins it, and K74's approval covers the switched-off case only. `src/motodiag/cli/serve.py` (lines 213 to 224) calls the new function in place of the direct call, keeps its loop and its `ClickException` as they are, and when the switch is off prints one line to stderr: `Customer share links are off (MOTODIAG_SHARE_LINKS_ENABLED=false): MOTODIAG_PUBLIC_BASE_URL is not checked.`
   - **Finish line:** `motodiag serve` with `MOTODIAG_ENV=prod`, the switch off and `MOTODIAG_PUBLIC_BASE_URL` empty reaches `uvicorn.run` (patched) and prints the line; the same with the switch on refuses with the same message as today; in prod with the switch on, the new function returns exactly what `check_public_base_url` returns for every case `tests/test_f64_public_url.py` lists.

3. **Minting refused while off.** `src/motodiag/api/routes/share.py`: one module constant, `SHARE_LINKS_OFF_MESSAGE = "Share links are switched off for now. You can still send the report as a PDF."`, and in `create_session_share`, before `build_session_report_doc` and before any row is written, `raise HTTPException(status_code=403, detail=SHARE_LINKS_OFF_MESSAGE)` when `get_settings().share_links_enabled` is false. The refusal comes before the ownership check on purpose: it says nothing about whether the session exists, and it is the same answer for every session. The route's `responses` declares the 403 with that sentence, so the OpenAPI document says it. `list_session_shares` and `revoke_session_share` are unchanged: a shop can still see and revoke what it minted earlier (K79 names minting and opening, nothing else).
   - **Finish line:** with the switch off, the mint answers 403 with `detail` equal to the constant and `report_shares` gains no row; with the switch on, the mint answers 201 as today.

4. **Opening refused while off, old links too (K79).** In `view_shared_report`, before `resolve_share` is called, when the switch is off the route answers `_message_response(404, "Report links are off", "This shop isn't sending report links right now. Ask them for a copy of the report.")`. The token is not looked up, so no view is recorded, a real token and a made-up one get the same page, and the token space cannot be walked while the switch is off. The 404 keeps the route's generic-404 posture and the response code the OpenAPI document already declares; its description gains one sentence. Switching back on restores every link that is still live and unrevoked: the switch changes no row.
   - **Finish line:** a link minted while on, with the switch then set off, answers 404 HTML carrying the page's title, and its `view_count` is unchanged; a made-up token gets the same page; with the switch on again the same link answers 200.

5. **The OpenAPI document and the phone app.** The document changes: the mint operation gains a declared 403, and two descriptions change. Gate 11 (`tests/test_phase205_gate11.py`, `TestContractSnapshot`) compares the sets of operations and the component schemas, with prose stripped; neither changes, so the committed snapshot at `../moto-diag-mobile/api-schema/openapi.json` stays valid and no refresh is forced by this phase. The handoff still names the refresh (`npm run refresh-api-schema`, then `npm run generate-api-types`, in a session rooted in the mobile repository) as the app's own step, together with showing the 403's `detail` (today `useReportShareLink.ts` folds a 403 into "unauthorized"). No file in the mobile repository changes in this phase.
   - **Finish line:** `tests/test_phase205_gate11.py` passes on the branch against the committed snapshot.

6. **The tests, the control and the mutations.** `tests/test_phase402_share_links_off.py` and `402_mutate.py` (under Tests). The new tests are run once against master's `config.py`, `public_url.py`, `serve.py` and `share.py`; every test of a changed behaviour is red there and every control is green.
   - **Finish line:** the file passes on the branch; the count of tests red on master's code is in the phase log; `402_mutate.py` prints every mutation red.

7. **The documents that name the settings.** The two new names, the rule for the six, and "with share links off, the public address is not checked" go where `MOTODIAG_PUBLIC_BASE_URL` is named today for an install: `README.md` (the settings table), `docs/guide/install.md` ("Before it faces anything real"), `docs/guide/api.md` ("Share links" and "Deployment"), `docs/launch-checklist.md` (the prod settings block) and `docker-compose.yml` (the commented example). `docs/guide/payments.md` gains one paragraph on the thank-you page: it holds no data, Stripe sends a customer or a shop owner there after Checkout, the portal, an invoice payment and Connect onboarding, and `MOTODIAG_STRIPE_RETURN_PAGE_URL` is the one setting to change when it moves (K75).
   - **Finish line:** `git grep -n MOTODIAG_SHARE_LINKS_ENABLED -- README.md docs/guide docs/launch-checklist.md docker-compose.yml` finds each file once at least.

8. **The handoff: 371's live step rewritten.** `docs/handoffs/<close date>_402_closed.md`, written at the close-out before the merge, carries the operator's steps in plain English, each with the computer and the window, one paste block ending in ALL GOOD or SOMETHING IS OFF, no internal labels, and every `gh` call naming `-R Kubanjaze/moto-diag` (R8):
   - **Before the steps**, what the operator does by hand: publish the thank-you page on a free host (K75) with the wording agreed, and note its https address.
   - **Step 1:** put the server on the merged code and restart it, as 371's step 1 did, checking `healthz` and that the new setting is known to the installed code.
   - **Step 2, changes nothing:** the settings file is private; it has `MOTODIAG_SHARE_LINKS_ENABLED=false` and a `MOTODIAG_STRIPE_RETURN_PAGE_URL=` line whose value starts with `https://`; under `MOTODIAG_ENV=prod` the server's own rule, `startup_public_url_problems(Settings())`, finds no blocking problem. It no longer looks for `MOTODIAG_PUBLIC_BASE_URL`.
   - **Step 3:** the settings list the operator fills in by hand gains `MOTODIAG_SHARE_LINKS_ENABLED=false`, `MOTODIAG_STRIPE_RETURN_PAGE_URL=` and `MOTODIAG_STRIPE_PRICES_ARE_PLACEHOLDERS=false` (the real prices), and loses `MOTODIAG_PUBLIC_BASE_URL`: ten lines, counted once each by the block, which then runs step 2's check again, restarts the server, installs the payments feed and asks its status, as 371's step 3 did.
   - **Step 4:** the alarm test, as 371's step 4, unchanged in substance (K72).
   - "What is open" names the app's own step (item 5), the public front door as option C of 2026-11-09 for a later decision, and F259 as the operator's. "After the merge" is left for whoever merges.
   - **Finish line:** `roadmap_check.py` R6 and R8 pass with the handoff in place; a reader following the steps needs nothing from this plan.

9. **The close-out.** `docs/FOLLOWUPS.md`: F257 marked closed by Phase 402, with the closing sentence naming the switch and the handoff. `COLLECTED_TEST_FLOOR` in `tests/test_phase255B_collected_test_floor.py` raised by a diff of collected ids, the reason in the commit message. `wholetree.sh` alone before every commit, its exit code read; `wholetree.sh --full` and then `regression.sh` for the regression of record; the phase folder moves to `docs/phases/completed/`; row 402 closes ✅ with `**CLOSED YYYY-MM-DD.**` and the regression line; this document goes to v1.1 with Deviations and Results.
   - **Finish line:** `verify_phase.sh 402` reports every check as it should be; the pull request is opened for the operator to merge by hand (K76).

No migration: the phase adds no table, column or index, and changes no row.

## The change log's three newest entries

- **2026-10-29 — rule 6: the code's counts only improve, and the weekly page (Phase 393, K54).** Became `tests/test_phase393_quality_ratchet.py`: the six measured counts against their pins both ways, and the coverage gate wired into `.claude/skills/closeout/regression.sh`. This phase adds no finding to any count and lowers no pin.
- **2026-10-26 — R8: an operator paste block's `gh` names its repository (before Phase 391, F222).** Became R8 in `.claude/skills/closeout/roadmap_check.py`, run with every suite and on every push. Item 8's paste blocks are written to it.
- **2026-10-22 — `fleet` joins the procedure folders (after Phase 387).** No check: the entry says the row is text only and no check reads the table.

## The plan of record

402 is not in the plan of record's "Next, in order" (`docs/reports/2026-10-12_plan_of_record.md` does not name 402). The K-id that puts it in order is K76 (2026-11-09), the operator's words: "402: start it now, the fleet builds it." Its record: "Starts Phase 402 (row 402, 🚧 on master from this commit; prompt `docs/prompts/402_share_links_off_and_return_pages.txt`), built by the fleet rather than a builder session. 402 is not in the plan of record's 'Next, in order', so the fleet does not open it by itself: at the operator's request ("Put the plan on the fleet's issue") the advisor opens its mission issue with the prompt on it, and the Science Officer starts at the fleet's next cycle. The prompt fixes the two settings the phase adds, MOTODIAG_SHARE_LINKS_ENABLED and MOTODIAG_STRIPE_RETURN_PAGE_URL, for the operator to write in server.env. The operator merges by hand, as for every phase; issue #59 (372) keeps its hold."

What it builds is K74 (2026-11-09): "The six Stripe return addresses point at a plain public thank-you page; customer share links are switched off until a public front door exists; the server stays tailnet-only." K78 (2026-11-09) corrects the classification to extension and lets the fleet build it; K79 (2026-11-09) decides the fork under Rule-1 stops.

The phase is a shop phase, not fleet-only: it changes `src/motodiag/core`, `src/motodiag/cli` and `src/motodiag/api`, and nothing under `.claude/skills/fleet/`. It unblocks the operator's own step of switching live Stripe on, which 371's handoff left waiting on F257; no "Unblocks:" line under K43 applies.

## Rule-1 stops anticipated

- **A real fork: decided.** Whether a link minted before the switch still opens was the fork Step 0 found; K79 (2026-11-09) decides it: "402: while share links are off, every link stops opening, old ones too." Item 4 applies those words literally and the Engineer does not raise it again.
- **A threshold or a rule's definition: one change, approved in scope; anything beyond it is a stop.** The prod start-up check stops asking for `MOTODIAG_PUBLIC_BASE_URL` while share links are off. K74 is the operator's approval of that change, for share links switched off only, and K78 repeats it. With the switch on, `check_public_base_url` stands exactly as today. Any other change to a check's definition is a stop, and two are foreseeable: making the server refuse to start in prod when `MOTODIAG_STRIPE_RETURN_PAGE_URL` is empty or not https (this plan puts that check in the handoff's paste block only), and refusing the list or revoke routes while the switch is off (this plan leaves them as they are). If the Engineer finds either necessary, it stops with kind `threshold-or-rule`.
- **A test that cannot be made green: none known.** The one unverified assumption is whether `model_fields_set` reports environment-given fields (item 1 names the fallback, which is a build choice). If an existing test pins a behaviour this phase must change and the Engineer cannot make it green within K74's scope, it stops.
- **A login or a credential: none.** The live key, the real prices and the page's address are the operator's, typed into `server.env` by hand after the merge; no test and no step of the build reads them.
- **A live-database change that alters or deletes rows: none.** No migration; the switch changes no row in `report_shares`.

## Tests

- `tests/test_phase402_share_links_off.py`, new, every case through a fresh `Settings()` or `reset_settings()` with `monkeypatch.setenv`, and the API through `TestClient(create_app(db_path_override=...))` as `tests/test_f64_public_url.py` does:
  - **The settings.** Defaults: the switch true, the page empty, the six at today's values (the exclusion's control). `MOTODIAG_SHARE_LINKS_ENABLED=false` is read. The page set alone: all six equal it. The page set with one of the six given on its own: that one keeps its own value and the other five take the page. The page empty with one of the six given: that one is as given and the others at their defaults.
  - **Minting.** Off: 403, `detail` equal to the constant, no new `report_shares` row, and the answer is the same for a session id that does not exist. On: 201 as today (control).
  - **Opening.** A link minted while on; the switch set off; the link answers 404 HTML with the page's title and its `view_count` is unchanged; a made-up token gets the same body; the switch set on again, the same link answers 200 (K79's old-links case and its control). Off, list and revoke still answer as today.
  - **The start-up rule.** `startup_public_url_problems`: off, an empty list in prod for an empty URL and for a `.ts.net` URL; on, the same list as `check_public_base_url` for each URL `tests/test_f64_public_url.py` parametrises (the identity, in prod and in dev). `motodiag serve` through `CliRunner` with `uvicorn.run` patched, as `tests/test_phase191b_serve_migrations.py` does: prod, off, empty URL starts and prints the one line; prod, on, empty URL refuses with today's message and a non-zero exit.
  - **The document.** The mint operation's declared responses include 403 with the constant's sentence; `tests/test_phase205_gate11.py` passes unchanged against the committed snapshot.
  - **The handoff.** `tests/test_roadmap_continuity.py` (R6, R8) passes with the handoff in place at the close-out.
- **Old code:** the new file run against master's four changed modules; the behaviour tests red, the controls green; the counts in the phase log.
- **Mutations, `402_mutate.py`** (in the phase folder, its output in `402_mutate.out`), each applied to a copy and run against the new tests, each red: the switch ignored at mint; the switch ignored at open; the open route looks the token up before refusing (a view recorded); the start-up check still runs with the switch off; the new function returns an empty list with the switch on; the switch's default flipped to false; the page ignored; a field given on its own overridden by the page; `serve` prints nothing when the check is skipped.
- `tests/test_f64_public_url.py` and `tests/test_phase200_share.py` pass unchanged: they pin the switched-on behaviour.
- `COLLECTED_TEST_FLOOR` raised by a diff of collected ids.
- `wholetree.sh --full`, then the regression of record through `regression.sh`, its line in the phase log with the counts, the hash, the wall time and the command; coverage not below its pin.

## Non-goals

- The thank-you page itself, its wording and its host: the operator's, on a free host for now (K75). Moving it later changes one setting.
- A public front door for share links or self-booking (option C of 2026-11-09): a later decision of the operator's. The server stays tailnet-only.
- Switching live Stripe on, the live key, the real prices, the Sentry email rule, the alarm test: the operator's steps after the merge, from the handoff.
- Any change in the mobile repository: how the app shows the 403's message and the snapshot refresh are the app's own session.
- Refusing the list and revoke routes, or any share route beyond mint and open.
- A new start-up rule in code for `MOTODIAG_STRIPE_RETURN_PAGE_URL`; the paste block checks it.
- Any change to `check_public_base_url`, to the four readers of the six return settings, or to `_share_url`.
- A migration, a change to any live row, and any seed data: none. No data path, no split and no eval protocol belong to this phase.
- Phase 401 (webhooks at 100 shops, paused), F259 (the feed's writes at the next deploy) and F238 (the size of `migrations.py`): left as they are.

## Planned items

- [ ] The phase log's first entry: the 🚧-versus-🔲 difference, K78 and K79 quoted, the open route named
- [ ] Item 1: the two settings and the validator in `config.py`
- [ ] Item 2: `startup_public_url_problems` and `serve.py` calling it
- [ ] Items 3 and 4: the mint and the open route refused while off, old links too
- [ ] Item 5: the OpenAPI document and gate 11 checked
- [ ] Item 6: the tests, the run against master's code, the mutations
- [ ] Item 7: the documents that name the settings
- [ ] `COLLECTED_TEST_FLOOR` raised; `wholetree.sh --full`; the regression of record
- [ ] Item 8: the handoff with 371's live step rewritten
- [ ] Item 9: F257 closed, the close-out, v1.1, the pull request for the operator

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-11-09 | the plan |
