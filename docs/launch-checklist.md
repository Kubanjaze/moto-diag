# Launch checklist

Everything between "the platform is built" and "someone else is using
it." All of it needs you — hardware, credentials, or a decision. None of
it can be done from a coding session, which is why it is written down
rather than attempted.

Ordered by dependency: each step unblocks the ones under it. Every item
says how you know it worked, because "I set the env var" and "it works"
are different claims.

**Status as of 2026-09-17** (refreshed by Phase 209B): backend 6,500+ tests
green, mobile 1,062 tests and `tsc` clean, 265 CLI commands, 81 API routes,
26 iOS screens, schema v60. Phase 210 (launch readiness) is still
deliberately unstarted — it depends on steps 1–6 below.

**This checklist was first written on 2026-09-09, the day before the 244
series added vision questions, a cost ledger, per-machine memory and passive
capture.** Phase 209B went back through it against the product as it
actually is now. Four things below would have made a launch fail silently —
a server that starts, answers `/healthz`, and can't do its main job:

| | What was wrong | Where |
|---|---|---|
| 🚨 | Every server recipe left out the `ai` extra, so no deployment could call Claude or Whisper | step 1, step 2 |
| 🚨 | PDF reports depended on `reportlab`, which nothing declared | step 1, step 2 |
| 🚨 | The container had no ffmpeg, so every video upload returned 503 | step 2 |
| 🚨 | The app's server address is compiled in, so a reviewer can't point it anywhere | step 4, and **Decisions** below — ✅ **fixed 2026-09-17**, moto-diag-mobile `49270ba` |

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

✅ **Done.** Both repos have been level with origin since 2026-09-10.

---

## 1. Stand up the host — F64

**The one that unblocks everything else.** Share links, the demo server
App Review requires, the CORS origin, and the rate-limit config all
resolve to "where does this run?" Right now the answer is your laptop,
and a customer share link built from `localhost` resolves to *the
customer's own phone*.

You said this waits until the app is complete. It is.

**What you decided (2026-09-17): Fly.io.** The API runs at `api.<domain>`
on SQLite, stored on a Fly persistent volume and replicated continuously by
**Litestream** to object storage from day one. The site and waitlist go on
Vercel at the bare domain. **Domain: TBD** (being bought this week). **F64 is
now the deploy ticket.** Full record: 209B implementation doc → *Decisions §2*.

> *Superseded:* the earlier plan here was "the home desktop, once it is out
> of storage". **Steps 1–4 below were written for that plan** and get
> rewritten for Fly.io as part of F64. Fly terminates TLS and provides the
> public name, which replaces steps 2–3.

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
   "motodiag[server]"` and run `motodiag serve --host 0.0.0.0` behind the
   proxy. **Install ffmpeg on the host too** (`apt install ffmpeg` /
   `brew install ffmpeg`). It's a system binary, so pip can't provide it,
   and without it every video upload returns 503.

   `[server]` is the whole server: `api`, `ai`, `vision`, `push` and
   `reports`. Use it
   rather than listing extras by hand. Before 209B every hand-written recipe
   in this repo left out `ai`, which gives a server that starts cleanly and
   can't do a single AI task.

**Then set, in the deployed environment:**

```bash
MOTODIAG_ENV=prod
MOTODIAG_PUBLIC_BASE_URL=https://<your-host>
MOTODIAG_BILLING_PROVIDER=stripe        # prod REFUSES to start on `fake`
MOTODIAG_STRIPE_WEBHOOK_SECRET=<secret>
MOTODIAG_API_CORS_ORIGINS=https://<your-host>   # F69 — default is localhost
ANTHROPIC_API_KEY=<key>                  # diagnosis, vision sweep, Ask — all of it
OPENAI_API_KEY=<key>                     # Whisper voice transcription
```

**Without the two AI keys** the server runs and every AI feature fails at
request time. Nothing checks for them at startup.

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

# Phase 209B: the three things the first version of this image couldn't do
docker run --rm motodiag:0.6.0 ffmpeg -version | head -1          # video uploads
docker run --rm motodiag:0.6.0 python -c "import anthropic, openai"  # every AI feature
docker run --rm motodiag:0.6.0 python -c "import reportlab"          # PDF reports
```

The last three are new. The ffmpeg install was added to the Dockerfile by
Phase 209B **and is as unverified as the rest of the file**: Docker still
wasn't installed on the machine that wrote it. The `[server]` extra and the
`reportlab` declaration *are* verified — a clean-wheel install test builds
that exact recipe and renders a PDF from it.

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
photo library, Bluetooth), that no analytics or crash SDK is present, how
to contact you, and **where the data goes.**

⚠ **Corrected by Phase 209B.** This step used to say the policy should
state *"that data goes only to the operator's own backend."* That hasn't
been true since vision and voice shipped. The backend sends:

- **video frames and the technician's typed questions → Anthropic**
  (diagnosis, the vision sweep, Ask)
- **voice recordings → OpenAI** (Whisper transcription)

The policy has to say so. **Whether this changes the App Privacy
questionnaire** is a decision for you, and possibly counsel. The draft
answers in `app-store-listing.md` were written before either data flow
existed, and they claim "Data Not Collected" across the board. Re-check
them against the current backend, not just the binary.

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

   ✅ **Unblocked 2026-09-17 — the server is set in the app**
   (moto-diag-mobile `49270ba`, Decisions §1 below). The app uses the
   address saved in **Settings → Server**, and falls back to `API_BASE_URL`,
   the default compiled in from `.env`. With neither, it says *"No server
   set — go to Settings."*

   - **If the demo instance is the build's default,** the reviewer only
     pastes the key.
   - **If it isn't,** the notes must tell the reviewer to open Settings →
     Server, enter the demo URL and tap Save before pasting the key.
   - **Save checks the server before storing it.** The address must be
     `https://` (plain http is refused for anything but `localhost`,
     `127.0.0.1` and `10.0.2.2`) and `/healthz` must answer `ok`. The demo
     instance has to be up and publicly reachable when the reviewer tries.
   - **The build won't archive without a real server.** A "Check release
     server URL" build phase fails any Release build whose `API_BASE_URL`
     is missing, isn't https, or is still `.env.example`'s
     `https://api.<your-domain>`. The domain is still TBD, so choose it
     before step 6.

   Verified on a device on 2026-09-17: a Release build installed, the
   address saved through Settings (the health check reached the server),
   and Home connected afterwards.

   *History (found by Phase 209B):* until then the app had no field for a
   server URL. `api/client.ts` compiled `API_BASE_URL` into the binary, with
   a hardcoded emulator address behind it, so a reviewer could paste a key
   but never change which server the app talked to.

**Done when:** you can install the app fresh on a device, set the demo
server in Settings if the build's default isn't it, paste that key, and
reach a populated work-order list without touching your dev machine.

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

## Decisions the 244 work surfaced

✅ **All resolved on 2026-09-17.** The full record, with reasons and the
alternatives rejected, is in the **209B implementation doc → Decisions**.
In short:

| | Decision | Tracked in |
|---|---|---|
| §1 | **Runtime server-URL setting.** The default comes from config (`API_BASE_URL`), the Settings screen overrides it, and a live health check runs on save. Plain http only for `localhost` / `127.0.0.1` / `10.0.2.2`. A build-time assertion requires `API_BASE_URL` in production. | ✅ **Shipped** — moto-diag-mobile `49270ba` |
| §2 | **$25/month per shop**, enforced via `shop_cost_this_month` | F78 |
| §3 | **Recompile memory on session close** | F79 |
| §4 | **The policy must reflect collected data** before submission — owner Kerwyn | F80 |
| §5 | **Build none of the unreachable features now; fix the gate instead** (CLAUDE.md phase completion item 6) | F82, F83 |
| — | **Hosting: Fly.io + SQLite + Litestream**; Postgres deferred | F64, F81 |

The original questions are kept below as they were asked.

**1. One binary, or one server per shop?** *(blocks step 4)*
The app talks to exactly one server, fixed at build time. Step 3 says
"every deployment is the shop's own", and those two don't fit together.
The options:

- a runtime server-URL setting (the app asks for a URL as well as a key)
- a single hosted MotoDiag service every shop's app talks to — which
  changes step 3's privacy premise entirely
- a separate build per shop

**2. A spending ceiling.**
`cost_cap_monthly_usd_cents` exists and nothing reads it, and the read path
for monthly spend (`shop_cost_this_month`) has no caller either. The first
real prices: **~1¢ per text diagnosis, ~13¢ per vision question, ~5¢ per
automatic sweep.** Before launch, decide what should happen to a shop that
hits a ceiling mid-job. `motodiag costs report` shows real spend so far.

**3. When per-machine memory refreshes.**
Memory (Phase 244M) only compiles when someone runs
`motodiag memory compile`. On a live server it goes stale unless something
runs it — a schedule, a hook when a session closes, or a documented
operator task.

**4. What the captured data means for the privacy policy.**
Phase 244N stores technicians' questions, answers and corrections on the
operator's server, and `session_overrides` records who made each
correction. Nothing reports per technician, but the data is there.
Technician-monitoring law — consent, works councils, two-party-consent
recording — was flagged in 244M's research as **never looked at**.

**5. 32 built features no user can reach.** *(33 when first written; #30
was reclassified as `superseded` on 2026-09-17 — it was wired in once and
then replaced.)*
Phase 209B walked the import graph from every entry point: **38 of 256
modules (~15%) are unreachable**, and 47 more public functions inside
reachable code have no caller. Each is classified in
`tests/support/integration_gaps_allowlist.py`, and a test fails if the list
and the tree disagree. Of the 32 marked `unwired-feature`, the ones worth a
decision before launch:

| | |
|---|---|
| **Track C2 audio intelligence** (10 modules) | Engine-sound analysis, anomaly detection, coaching, fusion, reports — all tested, all marked ✅ on the roadmap, and nothing can reach them |
| **`core.logging`** | The served app never sets up its own structured logging |
| **`validate_video`** | Uploads are checked for size and quota, but the file is never probed; the server trusts the client's metadata |
| **`pricing`** (4 modules) | A non-AI rate table and repair-plan builder |
| **Guided workflows** | No-start, charging and overheating workflows |

The rest are `substrate` (built ahead for Phases 275, 293–302, 308–310
and 316), `superseded`, `test-infra` or `public-api`.

## What is genuinely finished

So you know what you are *not* on the hook for:

- **The product.** 265 CLI commands, 81 API routes, 26 iOS screens,
  1060 curated known issues shipped inside the package. *Qualified by
  Phase 209B:* about 15% of the backend's modules can't be reached from any
  of those commands or routes — see **Decisions §5**.
- **Tests.** 6,500+ backend and 1,062 mobile, green. Mobile `tsc` and lint
  clean.
- **Security.** Phase 207 audited it and fixed six defects including a
  cross-tenant data leak. What remains is configuration, listed above.
- **Packaging.** `pip install motodiag` works, seeds its knowledge base,
  and puts your data somewhere sane. Verified by installing a real wheel
  into a clean environment — and since Phase 209B, by installing
  `motodiag[server]` and checking that it can reach the AI SDKs and render a
  PDF. The earlier test covered only the bare install and `[api]`, which is
  how three broken server recipes passed.
- **Documentation.** README, quickstart, shop workflow, API guide,
  install guide, release runbook — with a test that fails if any of them
  names a command or route that does not exist.

---

## The order, in one line

Push → host → (Docker) → privacy policy → demo instance → screenshots →
TestFlight → hardening. Steps 3–6 all depend on step 1, so if you only
do one thing, do the host.
