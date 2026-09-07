# HTTP API

80 routes over 103 operations. The iOS app runs on this; so can anything
else.

## Start it

```bash
motodiag serve
```

Binds `127.0.0.1:8000` and applies any pending schema migrations before
accepting traffic. Useful flags:

```bash
motodiag serve --host 0.0.0.0 --port 8080   # reachable from the LAN
motodiag serve --reload                     # development autoreload
motodiag serve --skip-migrations            # only if migrated out-of-band
```

Interactive docs at `/docs`, the schema at `/openapi.json`, and a
liveness check that needs no key:

```bash
curl -s localhost:8000/healthz
```

```json
{"status": "ok", "schema_version": 50, "detail": null}
```

```bash
curl -s localhost:8000/v1/version
```

```json
{"package": "0.6.0", "schema_version": 50, "api_version": "v1"}
```

## Authentication

Every route except `/healthz`, `/v1/version`, the docs and the public
share route needs an API key.

```bash
motodiag apikey create --user 1 --name laptop
```

The plaintext key is printed **once** and never again — only a SHA-256
hash is stored, so a lost key is regenerated, not recovered. Send it as
a header:

```bash
curl -s localhost:8000/v1/sessions -H "X-API-Key: mdk_live_..."
# Authorization: Bearer <key> also works
```

Manage them with `motodiag apikey list --user 1`, `apikey show
<prefix>`, and `apikey revoke <prefix>` — revocation takes effect on the
next request.

Without one:

```json
{
  "type": "https://motodiag.dev/problems/invalid-api-key",
  "title": "Invalid or missing API key",
  "status": 401,
  "detail": "valid API key required (X-API-Key header or Authorization: Bearer <key>)",
  "request_id": "a01f389d4ebc4b79bf5c2cb76a67b533",
  "instance": "/v1/sessions"
}
```

## Errors

Every error is [RFC 7807](https://www.rfc-editor.org/rfc/rfc7807)
`application/problem+json` with the shape above. `type` is a stable
URI you can branch on — prefer it to string-matching `title` or
`detail`, which are for humans and may be reworded.

`request_id` also comes back in the `X-Request-ID` response header and
appears in the server log for the same request. Quote it in a bug
report.

| Status | Means |
|---|---|
| 401 | No key, or a revoked one |
| 402 | Your tier doesn't include this, or you're out of quota |
| 403 | Authenticated, but not a member of that shop |
| 404 | Not found — *or* not yours. The two are deliberately indistinguishable |
| 413 | Upload too large |
| 422 | Request body or path failed validation |
| 429 | Rate limited |

## Tiers and limits

Your key's tier comes from the owning user's subscription.

| Tier | Per minute | Per day |
|---|---|---|
| anonymous | 30 | 100 |
| individual | 60 | 1,000 |
| shop | 300 | 10,000 |
| company | 1,000 | 50,000 |

Shop-management routes need `shop` or above. `motodiag tier` shows where
you stand; `motodiag subscription show` shows the subscription behind it.

## The routes

`/openapi.json` is authoritative. By area:

| Area | Ops | What |
|---|---|---|
| `sessions` | 9 | Diagnostic sessions — create, list, update, close |
| `videos` | 5 | Video attached to a session, plus AI analysis state |
| `vehicles` | 6 | The garage |
| `knowledge-base` | 8 | DTCs, symptoms, known issues, bulk export |
| `shop-management` | 26 | Shops, members, customers, intakes, work orders |
| `parts` | 12 | Part lines on a work order, requisitions |
| `time-tracking` | 5 | Clock in and out against a work order |
| `work-order-photos` | 6 | Photos, normalised server-side |
| `voice-transcripts` | 6 | Voice notes and their transcriptions |
| `reports` | 7 | Composed reports, HTML and PDF |
| `share` | 4 | Customer share links |
| `billing` | 3 | Subscription, checkout, portal |
| `push` | 2 | APNs device registration |
| `diagnostics` | 1 | OBD adapter failure telemetry |
| `meta` | 2 | `/healthz`, `/v1/version` |

## Conditional GET

The knowledge-base export supports `ETag` / `If-None-Match`. Send back
the `ETag` you were given and an unchanged KB answers `304` with no
body:

```bash
curl -s localhost:8000/v1/kb/export -H "X-API-Key: $KEY" -D-  -o/dev/null | grep -i etag
curl -s localhost:8000/v1/kb/export -H "X-API-Key: $KEY" -H 'If-None-Match: "<etag>"' -w '%{http_code}\n' -o /dev/null
```

The mobile app uses this to avoid re-downloading a KB it already has.

## Share links

A share link is a **capability URL**: possession of the URL is the
authorisation, so there is nothing to log into.

```bash
curl -X POST localhost:8000/v1/reports/session/1/share \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"preset": "customer", "expires_in_days": 14}'
```

- 256-bit token; expiry and revocation are re-checked on **every** read
- The preset is fixed server-side at mint time — the holder cannot widen
  `customer` into `full`
- `GET /v1/share/{token}` is the only unauthenticated data route, and it
  is rate limited
- A bad, expired or revoked token gets a generic 404 that does not
  distinguish "wrong" from "never existed"

Revoke early with `DELETE /v1/reports/shares/{share_id}`; list what's
outstanding with `GET /v1/reports/session/{id}/shares`.

Set `MOTODIAG_PUBLIC_BASE_URL` to an origin the customer's phone can
reach before you send any of these. It defaults to localhost, which
works on your machine and nowhere else.

## Uploads

Photos and video go up as `multipart/form-data` with a JSON `metadata`
part. Ceilings are per request — 512 MB for a video, 25 MB for a photo —
and exceeding one gets a `413` mid-stream rather than after the whole
body has been read. Per-session and per-work-order aggregate quotas
apply on top.

Photos are decoded and re-encoded server-side, so the stored file is a
real image regardless of what the `Content-Type` claimed. Stored
filenames derive from database ids; the client's filename never reaches
disk.

## Generating a client

The schema drives the iOS app's TypeScript types, and can drive yours:

```bash
curl -s localhost:8000/openapi.json > openapi.json
npx openapi-typescript openapi.json -o api-types.ts
```

Regenerate after any backend contract change. Stale generated types are
a lie your compiler will enforce — see
[contributing](../contributing.md#api-contract-changes).

## Deployment

Beyond `motodiag serve` on a laptop, before it faces anything real:

- `MOTODIAG_ENV=prod` — the app **refuses to start** in prod on the fake
  billing provider, whose webhook signature check is a hardcoded string
- `MOTODIAG_BILLING_PROVIDER=stripe` plus `MOTODIAG_STRIPE_WEBHOOK_SECRET`
- `MOTODIAG_API_CORS_ORIGINS` — the default is localhost dev origins
- `MOTODIAG_PUBLIC_BASE_URL` — a real reachable origin
- Terminate TLS in front of it, and know that rate limiting currently
  keys on the socket address: behind a proxy without forwarded-header
  handling, every anonymous caller shares one bucket
