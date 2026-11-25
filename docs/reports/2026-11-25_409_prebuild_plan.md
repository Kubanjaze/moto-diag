# Phase 409 — A public web address for the server: the prebuild plan

**Version:** 1.0 (prebuild draft) | **Tier:** Standard | **Date:** 2026-11-25

Written while Phase 210 builds, at the operator's ask (2026-11-25: "can we do that and get that part prebuilt parallel to what the fleet is currently working on?"). It is **not** 409's Step 0 or its v1.0 of record: row 409 is still 🔲 on master, its row pull request and Step 0 are the fleet's once 210 merges and the operator says go (K140: the fleet asks before opening each). This page lives in `docs/reports/` for that reason, so the ledger checks (R1 to R8) see no phase documents for a row that has not started. When 409 opens, the Captain takes this page as its starting draft, moves it to `docs/phases/in_progress/409_implementation.md`, and re-checks it against the tree.

It is written from `docs/prompts/409_a_public_web_address_for_the_server.txt` (the scope), ROADMAP row 409, `ops/desktop/motodiag-api.service`, and the code on master at `21bf8f4`. The scope's content is not changed.

---

## Goal

The live server answers at one https name on the internet, so a phone on any network reaches it without Tailscale, and nothing else on the home desktop becomes reachable (the scope's definition). Before it is put there, the server is made ready for anonymous callers from anywhere.

## The way in: the pick

**Pick: a Cloudflare Tunnel from the home desktop, at `api.getmekno.com`.**

| | Cloudflare Tunnel (picked) | Small rented server in front |
|---|---|---|
| What runs | `cloudflared` as a systemd service inside the desktop's Ubuntu, dialling out to Cloudflare; Cloudflare's edge answers `api.getmekno.com` and forwards to `http://127.0.0.1:8000` | A $5–6/month server running Caddy on a public IP, forwarding over the tailnet to the desktop |
| Ports open on the home network | None (outbound only) | None at home; 22 and 443 open on the rented server |
| Certificates | Cloudflare's, automatic | Caddy's Let's Encrypt, automatic |
| Cost | $0 (getmekno.com is already on Cloudflare) | $60–75 a year |
| New machine to patch and watch | No | Yes: its OS, its SSH, its Tailscale login |
| Tailscale in the product's path | No | Yes, between the rented server and the desktop |
| Biggest request body | **100 MB** (Cloudflare Free) | Unlimited |
| Who sees the traffic decrypted | Cloudflare (TLS ends at its edge) | Only the operator's server |
| When the server later leaves the desktop | `cloudflared` moves with it; the name stays | The rented server could become the host |

Why the tunnel: the operator's direction is that a private network is a stopgap, not the product (K136). The tunnel takes the tailnet out of the public path entirely, opens nothing on the home network, adds no machine, and costs nothing. Cloudflare already holds getmekno.com's DNS and site, so the name is one record the tunnel's own setup writes. The rented server only wins on the upload size and on privacy from Cloudflare, and both have answers below. Moving the server off the desktop is out of this phase (the scope's "Not in this phase").

**Its one real cost: 100 MB.** K119 allows manual uploads up to 300 MB a file. Through Cloudflare Free, any request over 100 MB is refused at the edge with 413 before it reaches the server. That is decision 5 below. Everything else the app sends is far smaller.

**Funnel and the LAN stay out**, as the record says (`docs/handoffs/2026-10-19_382_closed.md`). The tailnet address keeps working beside the public one for shop one's phones until 410 moves them.

## What the internet would reach: the audit, done on master at `21bf8f4`

Measured by walking every route `create_app()` mounts and the dependencies each one needs (the same walk is now a test, below).

| What | Found | Needed for the internet | Done here |
|---|---|---|---|
| Routes with no credential | 7 plus the live socket: `/healthz`, `/v1/version`, `POST /v1/auth/login`, `GET /v1/terms`, `POST /v1/billing/webhooks/stripe` (Stripe's signature), `GET /v1/share/{token}` (off on live, K74), **`GET /v1/shops/{id}`**; `/v1/live/{id}` checks its own key | `/v1/shops/{id}` answered anyone, for any id, with the whole shop row: address, phone, email, **tax id**. The app does not call it (only its generated types name it); `/v1/shop/profile/{id}` is the app's | **Closed:** it now needs a signed-in active member; anyone else is 401/403, and a shop that does not exist is 403 too, so ids cannot be walked. A test pins the exact list of the other six |
| Auth on every other route | 125 routes need a key or a session | None | Pinned by the same test |
| Sign-in guessing | Only the anonymous rate limit: 30 a minute, 100 a day per address, nothing per name | A guard per name | **Added:** 10 failed logins for one name from one address in 15 minutes, then 429 with Retry-After; 50 for one name from every address together. A held name is refused before its password is checked; a good login clears only its own pair |
| The caller's address behind a proxy | uvicorn trusts `X-Forwarded-For` from 127.0.0.1 by default, so behind `cloudflared` on loopback each caller is counted by its own address | `cloudflared` must reach `127.0.0.1`, not `localhost` (which can be `::1`, not trusted), and must run inside Ubuntu, not Windows | **Pinned:** a test that `serve` never turns proxy headers off, and that two forwarded addresses get separate buckets. The handoff points the tunnel at `http://127.0.0.1:8000` |
| Security headers | None | nosniff, no framing, no referrer; HSTS over https | **Added**, on every answer, HSTS only on https requests (`X-Forwarded-Proto` from Cloudflare). Switch: `MOTODIAG_SECURITY_HEADERS_ENABLED` |
| Answering only to its names | Any Host header | The public name, the tailnet name, loopback | **Added, off until set:** `MOTODIAG_API_ALLOWED_HOSTS`; any other Host is 400 |
| Request size | Each upload route bounds its file (Phase 207); a JSON body had no bound | A cap before parsing | **Added:** a declared body over 1 MiB that is not a file upload is 413. `MOTODIAG_API_MAX_BODY_BYTES` (0 = off). Cloudflare caps everything at 100 MB in front |
| `/docs`, `/redoc`, `/openapi.json` | On in every environment | The operator's call (scope, Step 0 question 3) | **Switch added, default on (unchanged):** `MOTODIAG_API_DOCS_ENABLED=false` takes all three away |
| `/healthz` | A broken database answered `db unreachable: <the error>`, which can name the file's path | Nothing internal to an anonymous caller | **Fixed:** the reason goes to the log; the answer says `db unreachable` |
| `/v1/version` | Package and schema version | The app reads it at start-up | Kept |
| CORS | Development defaults (`localhost:3000`, `localhost:5173`), credentials allowed | Named origins. The app is native and does not use CORS; only a browser page would | Config only: `MOTODIAG_API_CORS_ORIGINS=https://getmekno.com` in the handoff |
| Cookies | None set anywhere (tokens go in headers) | Nothing | Nothing |
| Public base URL, share links | `public_base_url` empty; share links off (K74, F257) | The public base URL set; share links stay off unless decision 4 | Config only, in the handoff |
| OpenAPI servers list | `http://localhost:8000` | The public name | Config only: `MOTODIAG_API_SERVERS` |
| WebSocket `/v1/live` | Takes its key in the query string; uvicorn's logs filter it (`cli/serve.py`) | Cloudflare passes WebSockets through | Nothing |

## Logic: the code, in this branch

All of it is in files Phase 210's plan does not touch (210 writes `src/motodiag/launch/`, `src/motodiag/cli/launch.py`, two lines of `src/motodiag/cli/main.py`, its own tests and the counts):

- `src/motodiag/core/config.py`: six settings (`api_docs_enabled`, `api_allowed_hosts` with its list property, `security_headers_enabled`, `login_failure_limit`, `login_failure_window_s`, `api_max_body_bytes`), each defaulting to today's behaviour except the login guard, the headers and the body cap.
- `src/motodiag/auth/login_throttle.py` (new): the guard; `LoginThrottledError` is a `RateLimitExceededError`, so the existing 429 handler answers it with Retry-After.
- `src/motodiag/api/routes/auth.py`: the login checks the guard, then counts a failure or clears its pair.
- `src/motodiag/api/middleware.py`: `SecurityHeadersMiddleware`, `BodySizeLimitMiddleware`.
- `src/motodiag/api/app.py`: the docs switch, the two middlewares, the host check, and the guard reset per app (as the rate limiter is).
- `src/motodiag/api/routes/meta.py`: `/healthz` logs its reason.
- `src/motodiag/api/routes/shops.py`: the smoke route needs a member.

## Tests

- `tests/test_phase409_public_hardening.py` (new, 22 tests): the anonymous surface pinned exactly; the login guard (429 even with the right password, its pair cleared by a good login, other names untouched, case does not reset it, the window, the name-wide total); the headers and HSTS; the host check off and on; the docs switch; the body cap and its multipart exemption; `/healthz` naming nothing; the proxy address.
- **Red on master's code:** 12 of the 22, each a new guard (run with `src/` put back to master's). The other 10 are controls that pass on both: the defaults left as they are, the live socket's own check, and the proxy behaviour uvicorn already has.
- **Changed old tests**, each because the open shop route closed: `tests/test_phase175_api_foundation.py` (the smoke route's five tests now sign in a member; one new case for 401) and `tests/test_phase176_auth_billing.py` (the rate-limit test used `/v1/shops/999` as its anonymous route; it now uses `/v1/terms`).

## When 210 merges (the rebase)

- Rebase on master. `COLLECTED_TEST_FLOOR` is raised then, by a diff of collected ids, not now: 210 raises the same line, and raising it here would only make a conflict. The floor test refuses only a floor above the count, so it is green meanwhile.
- 210's launch check gains the condition the scope asks for: the public name answers over https with a valid certificate, and nothing it should not reach answers. It goes in `src/motodiag/launch/check.py`, which 210 creates, so it is written after the merge, not before.
- The findings this page names get their F-numbers then, through the `finding` skill, after 210's own (the sequence is shared, and 210 files one at its Step 0).
- The quality counts at their pins, `wholetree.sh` and the regression of record, as CLAUDE.md's rules 3 and 6 ask, inside the fence.

## Rule-1 stops: the operator's decisions

1. **The way in.** Recommended: Cloudflare Tunnel, as above.
2. **The name.** Recommended: `api.getmekno.com`.
3. **The API pages.** Recommended: off in prod (`MOTODIAG_API_DOCS_ENABLED=false`). The app's types are generated from a local server, not live.
4. **Share links.** Recommended: stay off for now; turning them on is its own small step after the address works (K74, the app's F64).
5. **Manual uploads over 100 MB.** Cloudflare Free refuses them at the edge. Recommended: lower the per-file limit to 100 MB (a change to K119's threshold, so the operator's), and say so in the app; a bigger manual is split or compressed. The alternative is that big manuals upload over the tailnet only.
6. **The open shop route closed.** Done here because it hands out a shop's tax id to anyone; the operator confirms it, as the scope's stops name "anything the census finds open that the operator has not decided".

## Non-goals

Self-serve sign-up (329), the App Store (410), moving the server off the desktop, Stripe's webhooks to the new address (the feed keeps asking Stripe, K65), share links back on unless decision 4 says so.

## Version history

| Version | Date | What |
|---|---|---|
| 1.0 (prebuild draft) | 2026-11-25 | Written while 210 builds; the code on branch `prebuild-409-public-address`. Waits for 210's merge and the operator's go. |
