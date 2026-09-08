# Launch checklist

Everything between "the platform is built" and "someone else is using
it." All of it needs you — hardware, credentials, or a decision. None of
it can be done from a coding session, which is why it is written down
rather than attempted.

Ordered by dependency: each step unblocks the ones under it. Every item
says how you know it worked, because "I set the env var" and "it works"
are different claims.

**Status as of 2026-09-07:** Phases 01–209 complete. Backend 4,902 tests
green, mobile `tsc` clean, 255 CLI commands, 80 API routes, schema v50.
Phase 210 (launch readiness) is deliberately unstarted — it depends on
steps 1–6 below.

---

## 0. Push three phases of work

Phases 207, 208 and 209 are merged locally on `master`/`main` and have
never been pushed. Nothing else here matters if the work only exists on
one machine.

```bash
cd ~/Projects/moto-diag && git push origin master
cd ~/Projects/moto-diag-mobile && git push origin main
```

**Done when:** `git status` says up to date with origin in both repos.

---

## 1. Stand up the host — F64

**The one that unblocks everything else.** Share links, the demo server
App Review requires, the CORS origin, and the rate-limit config all
resolve to "where does this run?" Right now the answer is your laptop,
and a customer share link built from `localhost` resolves to *the
customer's own phone*.

You said this waits until the app is complete. It is.

**What you decided:** the home desktop, once it is out of storage.

**Steps:**

1. Get the desktop up with a fixed LAN address.
2. Give it a public name. Tailscale (a `*.ts.net` name) is the low-effort
   path and was already tried in this project; a real domain with DNS is
   the durable one. `check_public_base_url()` in
   `src/motodiag/core/public_url.py` already knows about `.ts.net` and
   will warn you in prod.
3. Terminate TLS. App Store review will not accept a plain-HTTP backend,
   and share links sent by text should not be HTTP either.
4. Deploy — see step 2 for the container, or `pip install
   "motodiag[api,vision,push]"` and run `motodiag serve --host 0.0.0.0`
   behind the proxy.

**Then set, in the deployed environment:**

```bash
MOTODIAG_ENV=prod
MOTODIAG_PUBLIC_BASE_URL=https://<your-host>
MOTODIAG_BILLING_PROVIDER=stripe        # prod REFUSES to start on `fake`
MOTODIAG_STRIPE_WEBHOOK_SECRET=<secret>
MOTODIAG_API_CORS_ORIGINS=https://<your-host>   # F69 — default is localhost
```

**Done when:** you mint a share link from the shop workflow and open it
on a phone **on cellular data, not the shop wifi**. If it only works on
your network, F64 is not closed — that is the exact failure this ticket
exists to prevent.

**Closes:** F64, F69. **Unblocks:** steps 3, 4, 5, 6.

---

## 2. Build the Docker image — F76

Written in Phase 209 and **never built**; Docker was not installed on the
machine that wrote it. Everything the image *does* was verified outside a
container (the wheel installs with the `api` extra, `motodiag serve`
starts, `/healthz` answers 200), but the container mechanics — multi-stage
copy, non-root user against the volume, healthcheck, `.dockerignore`
coverage — are unreviewed.

```bash
cd ~/Projects/moto-diag
docker build -t motodiag:0.6.0 .
docker compose up
curl localhost:8000/healthz
```

Then check the two things most likely to be wrong:

```bash
# the volume must be writable as the non-root user
docker run --rm motodiag:0.6.0 sh -c 'touch /var/lib/motodiag/probe && echo OK'

# the local database and phase docs must NOT be in the image
docker run --rm motodiag:0.6.0 sh -c 'ls /app 2>/dev/null; find / -name "motodiag.db" 2>/dev/null | head'
```

**Done when:** `/healthz` returns `{"status":"ok",...}` from the
container, the volume probe prints OK, and no `motodiag.db` from your
laptop is inside the image. Then delete the "never built" warnings from
`Dockerfile`, `docker-compose.yml` and `docs/guide/install.md`.

**Closes:** F76. Skip if you deploy with pip instead of a container —
but then say so and drop the Docker files rather than shipping an
unverified path.

---

## 3. Put up a privacy policy

A hard App Store requirement. Submission is blocked without a reachable
URL, and there is currently no page and no URL.

The content is genuinely short, because the honest answer is that
**MotoDiag operates no server** — every deployment is the shop's own, so
"Data Not Collected" is accurate across the entire questionnaire. The
draft answers are in
[`app-store-listing.md`](../../moto-diag-mobile/docs/app-store-listing.md#app-privacy-questionnaire).

A static page on the host from step 1, or a GitHub Pages page, is
sufficient. It must state: what the app accesses (camera, microphone,
photo library, Bluetooth), that data goes only to the operator's own
backend, that no analytics or crash SDK is present, and how to contact
you.

**Done when:** the URL loads in a browser and goes in the App Store
Connect "Privacy Policy URL" field.

**Before you file the questionnaire:** re-check the table against the
shipped binary. It is accurate today; the day anyone adds Sentry or an
analytics SDK, it is wrong.

---

## 4. Stand up a demo instance for App Review

The app is a client. Without a backend it shows a login screen and
nothing else, and **App Review will reject it** — a reviewer cannot
exercise a single feature.

1. Point a second instance (or a second database) at the host from step 1.
2. Seed it with believable data — a shop, two or three customers, a few
   bikes, work orders in different states, one completed job with an
   invoice. The [shop workflow guide](guide/shop-workflow.md) is the
   script; it takes about ten minutes.
3. Mint an API key for the reviewer: `motodiag apikey create --user 1
   --name appreview`.
4. Put the server URL and key in the App Review notes — the template is
   in the listing doc.

**Done when:** you can install the app fresh on a device, paste that
key, and reach a populated work-order list without touching your dev
machine.

---

## 5. Capture screenshots

Six screens, 6.9" and 6.5" displays. The shot list and captions are in
the listing doc. Use the demo data from step 4 — placeholder text reads
as an unfinished app, and reviewers notice.

Capture at the largest required size and let App Store Connect scale.

**Done when:** ten or fewer PNGs per size, uploaded.

---

## 6. TestFlight, then the App Store

The runbook is
[`testflight.md`](../../moto-diag-mobile/docs/testflight.md). The `.ipa`
already builds — `ios/build/export/MotoDiag.ipa`, ~13 MB. Nobody has
ever uploaded one, and nobody can but you.

1. **App Store Connect app record** for `com.bandithero.motodiag`, with
   Push Notifications enabled on the App ID.
2. **Accept the agreements.** A new team usually has an unsigned Paid
   Apps or updated Program Licence Agreement, and uploads *silently
   fail* until it is accepted — budget an hour for this specific
   confusion.
3. **Bump `CURRENT_PROJECT_VERSION`** — it must increase for every
   upload.
4. **Upload** via Xcode Organizer, Transporter, or `xcrun altool`.
5. **Add yourself as an internal tester**, install from TestFlight,
   point it at the host from step 1.
6. Fill in the listing metadata from `app-store-listing.md` — name,
   subtitle, description, keywords are all written and within Apple's
   limits (asserted by test).

**Done when:** the build is installable from TestFlight on a device that
has never had Xcode attached to it. That is the first time the app is
real.

---

## 7. Buy a BLE adapter — F56, optional for launch

**Not a launch blocker.** `OBD_SUPPORT` is `__DEV__`-gated
(`src/config/features.ts:26`), so OBD ships dark — it is absent from
release builds entirely. You can launch without ever touching this.

When you do want it: buy a BLE-class adapter, then run the Phase 196
gate before flipping the flag. The re-scoped F56 already added the
telemetry so that the first real user who tries to connect one reports
it to you rather than silently failing.

`motodiag hardware compat recommend --make Honda --model CBR600F4i`
ranks adapters known to work, from a 24-entry catalog.

---

## 8. Deployment hardening — after it is running

These need a live deployment to test against, which is why they come
last rather than first.

| Ticket | What | Why it waits |
|---|---|---|
| **F71** 🚨 | Anonymous rate limiting keys on the socket address, so behind a proxy every anonymous caller shares one bucket. One client burning the 100/day cap 429s **every customer share link** platform-wide. | The fix is `forwarded_allow_ips` set to your actual proxy. Trusting `X-Forwarded-For` from anywhere else is worse than the current behaviour, so it cannot be guessed. |
| **F72** | Limiter state is per-process while `serve` accepts `--workers N`, so effective limits multiply by worker count. | Only matters once you run more than one worker. |
| **F70** | `/docs`, `/redoc`, `/openapi.json` are unauthenticated. | A decision, not a defect — the routes behind them are gated. Choose deliberately. |
| **F73** | API keys travel in the WebSocket query string. | Not in our access log; it is proxy logs and browser history. |
| **F77** | Dependency floors permit untested versions, and no CVE scan has ever run. | Run `pip-audit`, raise the floors, pin upper bounds on `fastapi`/`starlette`/`pydantic`. |

---

## What is genuinely finished

So you know what you are *not* on the hook for:

- **The product.** 255 CLI commands, 80 API routes, 25 iOS screens,
  745 curated known issues shipped inside the package.
- **Tests.** 4,902 backend, green. Mobile `tsc` and lint clean.
- **Security.** Phase 207 audited it and fixed six defects including a
  cross-tenant data leak. What remains is configuration, listed above.
- **Packaging.** `pip install motodiag` works, seeds its knowledge base,
  and puts your data somewhere sane. Verified by installing a real wheel
  into a clean environment.
- **Documentation.** README, quickstart, shop workflow, API guide,
  install guide, release runbook — with a test that fails if any of them
  names a command or route that does not exist.

---

## The order, in one line

Push → host → (Docker) → privacy policy → demo instance → screenshots →
TestFlight → hardening. Steps 3–6 all depend on step 1, so if you only
do one thing, do the host.
