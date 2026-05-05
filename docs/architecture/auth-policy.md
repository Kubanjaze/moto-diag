# F29 — Auth policy: read access doesn't gate on tier; cross-owner reads return 404

**Status:** Accepted (Phase 192 v1.0.1 / 2026-05-05)
**Filed as:** F29 (originally surfaced at Phase 192 plan v1.0; promoted to in-phase deliverable per the v1.0.1 amendment's Section A reshape).
**Affects:** all current + future read endpoints under `/v1/*`.

## Decision

Two coupled rules, articulated together because they reinforce each other:

1. **Read access doesn't gate on tier.** Reading your own data is a base-tier capability; tier gating is for scarce or expensive resources — creation (vehicle/session quotas), writes (work-order edits, invoicing), and compute-intensive operations (Vision analysis, AI diagnosis generation). A free-tier user reading their own session's report, their own vehicle list, their own video metadata pays nothing but gets read access.
2. **Cross-user read attempts on owned resources return 404, not 403.** When user A requests user B's session/vehicle/video/report, the response is `404 Not Found` — indistinguishable from "this resource doesn't exist." This is *enumeration-prevention*: a non-owner can't distinguish "session N exists but isn't yours" from "session N doesn't exist," so they can't enumerate the namespace by probing.

These rules are not new — Track I has implemented them uniformly across vehicles (Phase 188), sessions (Phase 189), videos (Phase 191B), and reports (Phase 182). The ADR canonicalizes the existing convention so future contributors making auth decisions in Phase 193+ inherit the policy by reference rather than re-deriving it from precedent.

## Context

Track I accumulated multiple read endpoints across phases without an explicit cross-cutting auth policy. The convention emerged organically: every phase that added an owned-resource read endpoint chose the same posture — owner-scoped via `get_X_for_owner()` repo function, raises `XOwnershipError` on cross-user access, exception handler maps to 404 in the API layer.

The Phase 192 v1.0.1 reshape surfaced the convention by accident. Plan v1.0 specified a new auth posture for the report viewer (`session_owner_or_shop_tier_member`). Pre-Commit-1 architect-side audit discovered Phase 182's existing report routes already use the stricter owner-only-with-404 pattern. Walking the audit across vehicles + sessions + videos confirmed all four phases use the same posture. The convention exists; the ADR documents it.

The reverse direction — convention without ADR — has a known cost: future contributors making auth decisions during Phase 193+ implementation make ad hoc choices, and the convention drifts. F9-family pattern (per `docs/patterns/f9-mock-vs-runtime-drift.md` subspecies (ii) generalized): two parallel surfaces for the same logical concern. ADR-shape document is the mitigation.

## Why 404, not 403, on cross-owner reads

Standard REST guidance treats 404 ("Not Found") and 403 ("Forbidden") as semantically distinct: 404 means the resource doesn't exist; 403 means it exists but you can't access it. By that guidance, cross-owner reads should return 403 — the resource DOES exist, the requester just doesn't have permission.

Track I deliberately deviates from that guidance for owned resources. The reason is **enumeration-prevention**, and it matters concretely.

### Worked example of the enumeration vector

moto-diag's resource IDs are sequential integers (sessions, vehicles, videos, work orders — every `INTEGER PRIMARY KEY AUTOINCREMENT` table). The `(id, user_id)` shape is the canonical owner-binding.

Suppose `GET /v1/sessions/{id}` returns 403 for "exists but not yours" and 404 for "doesn't exist." A curious or malicious caller with valid auth (their own API key) could iterate:

```
GET /v1/sessions/1   → 403  (someone else's session)
GET /v1/sessions/2   → 200  (their own; renders normally)
GET /v1/sessions/3   → 403
GET /v1/sessions/4   → 403
GET /v1/sessions/5   → 404  (session 5 was soft-deleted; or never existed)
GET /v1/sessions/6   → 403
...
```

What the caller learns from 1000 probes:
- **Total session count**: roughly the highest ID returning 403 or 200 (excluding consecutive 404s past the tail). The platform's user activity is exposed.
- **Creation-density over time**: session IDs are created sequentially with timestamps inferable from response Date headers; the curve of "when did session N exist by" tells the caller the platform's growth curve.
- **Soft-delete patterns**: 404 between a 403 and a 403 means a soft-deleted session in someone else's data — useful for inferring engagement / churn.
- **Specific user activity**: cross-correlating the 200-responses for the caller's own user with the 403-density immediately preceding/following gives a rough ordering of "when did other users create sessions relative to me" — a partial activity timeline.
- **Phishing target identification**: if the caller is a bad actor, knowing "session 4711 exists" lets them target that specific resource via other vectors — compromised credentials, token leakage, social engineering ("I'm helping with session 4711, can you confirm the symptoms?").

**The 404 posture eliminates all of the above.** Every cross-owner probe returns 404 indistinguishable from a never-existed ID. The caller learns nothing about resource population, growth, churn, or specific resources they don't already own. The information leak is sealed by collapsing the response space.

### The trade-off (and why we accept it)

Owner-only-with-404 has one user-facing cost: troubleshooting clarity for legitimate mistakes. A mechanic types the wrong session ID in a deep link, or follows a stale URL, or shares a session URL that gets opened by a non-owner. Under 403, the receiver sees "you can't see that" — they know the session exists; they ask the owner for access. Under 404, the receiver sees "this session is no longer available" — they don't know if it was deleted, never existed, or just isn't theirs. They can't easily ask the owner because they have no signal that the owner has anything to share.

The trade-off was decided in favor of enumeration-prevention because:

1. **Sharing flows are explicit, not implicit.** Cross-user access in moto-diag is currently zero (every read is owner-only). A user sharing their session URL with another user is an out-of-band action that doesn't generate ambiguous receiver experiences in the API itself. When a sharing surface lands (Phase 192B's PDF/Share Sheet, or a future magic-link feature), it'll use a token-scoped read URL — which has its own auth path independent of this policy.
2. **Sensitivity is uniformly high enough.** moto-diag's resources include billing tier (sessions tagged with the user's tier at session-create time), customer information (Phase 172+ shop-mode tracks customer names + phone numbers), Vision-analyzed video content (post-Phase 191B), and AI-generated diagnoses with cost data. Even for resources that *seem* low-sensitivity (a vehicle's make/model/year), enumeration of "user X owns N vehicles" leaks engagement / wealth signals that we don't want to expose.
3. **User-facing error copy can compensate.** The mobile app surfaces a generic "this session is no longer available; it may have been deleted" message — which doesn't speculate on cause (deletion vs cross-owner vs typo) but DOES point the user to recoverable next steps ("Back to sessions"). The compensation works because the legitimate-mistake case is rare; sharing flows that produce ambiguous receivers will be replaced by token-scoped sharing.

403 cross-owner would be acceptable for resources where enumeration is benign — but moto-diag has no such resources today, and the marginal cost of policy uniformity is negligible vs the marginal cost of per-resource sensitivity classification (rejected as A3 below).

## Why read doesn't gate on tier

Reading your own data is a base-tier capability for the same reason most platforms make read free: gating it punishes paying users and restricts non-paying users from accessing data they generated. The product's value proposition is that users own their diagnostic history; tier gating reads contradicts that.

Tier gating is reserved for:

- **Scarce resources at creation time**: per-tier vehicle quotas (Phase 188 `TIER_VEHICLE_LIMITS`), per-tier monthly session quotas (Phase 189 `TIER_SESSION_MONTHLY_LIMITS`), per-tier monthly video quotas (Phase 191B `TIER_MONTHLY_VIDEO_LIMITS`).
- **Writes that create tier-scoped artifacts**: shop-management writes (Phase 172 RBAC), invoice generation (Phase 169), parts ordering.
- **Compute-intensive operations**: Vision analysis (Phase 191B; per-video cost), AI diagnosis generation (Phase 79 / 162.5; per-call cost).

Note the asymmetry: a user can be at their tier's vehicle quota (creation gated) and still read all their existing vehicles freely. A user can have monthly session quota exhausted (creation gated) and still read all their prior sessions + reports freely. The tier gate fires at the moment of resource creation; once a resource exists, the owner reads it forever regardless of current tier.

## Alternatives considered

**A1 — Status quo (no formal policy).** Each phase chooses ad hoc. **Rejected**: drift is the predictable outcome; future contributors implementing Phase 193+ read endpoints would re-derive auth posture from precedent (which works while precedent is consistent) or make ad hoc choices (which breaks consistency once the precedent body is large enough that a new contributor doesn't read all of it).

**A2 — Uniform 403 cross-owner across all read endpoints.** Traditional REST-correct. **Rejected**: leaks enumeration information. The trade-off (troubleshooting clarity vs enumeration-prevention) was decided in favor of enumeration-prevention at every Track-I phase that implemented a read endpoint; ADR formalizes the existing choice rather than overturning it.

**A3 — Per-resource sensitivity classification (404 for sensitive, 403 for non-sensitive).** More nuanced; would let vehicle reads return 403 ("vehicle existence in a multi-tenant garage isn't sensitive") while session reads return 404. **Rejected**: classification-overhead. Every new endpoint needs a sensitivity-classification decision; reviewers need to verify each new endpoint's classification matches the resource's actual sensitivity profile; the wrong classification gets shipped + creates an enumeration vector. Uniform-404-everywhere has no per-endpoint review burden + no misclassification risk. The marginal troubleshooting-clarity cost on non-sensitive resources is acceptable.

**A4 — Magic-link-style share URLs for cross-user read.** Token-scoped read URLs let users explicitly grant cross-user access (e.g., for sharing a report with an insurance adjuster). **Deferred**, not rejected: this is a feature, not an alternative to the auth-on-default-route policy. Phase 192B's Share Sheet integration is the closest current surface; if a future phase adds magic-link sharing, the default-route auth policy is unchanged + the magic-link URL is a separate auth path.

**A5 — Tier-gated reads.** The product would charge for read access to historical reports beyond a window. **Rejected**: contradicts the value proposition. Users own their data; charging to read it is a recipe for churn.

## Consequences

For future contributors implementing read endpoints in Phase 193+:

1. **Default to owner-only-with-404.** Use the established `get_X_for_owner(resource_id, user_id, db_path)` repo pattern. Raise `XOwnershipError` on cross-user access. The exception handler in `motodiag.api.errors` maps the ownership exception to 404. Don't introduce new auth-error response codes for owned resources.
2. **Don't add `require_tier()` to read endpoints.** If a new read endpoint is genuinely tier-scoped (e.g., shop-tier-only feature whose data is only generated by shop-tier users), use shop-tier-membership check (Phase 172 `require_shop_permission`), not `require_tier`. The tier-membership check still permits the resource owner to read regardless of current tier.
3. **Smoke gates must verify the 404 cross-owner behavior.** A free-tier user fetching another user's owned resource should see 404 — verifiable in any phase's smoke checklist. Phase 192's Section G smoke step 7 documents this for the report viewer; subsequent phases inherit the verification template.
4. **User-facing error copy on 404 must not speculate on cause.** Error copy reads "This resource is no longer available" or "This session is no longer available" — not "Permission denied" or "Not your session." Speculation defeats the enumeration-prevention.
5. **Internal logging can distinguish.** Backend logs may include the actual cause (cross-owner vs deleted vs typo) for ops debugging — the policy is about what crosses the API boundary, not about what's recorded internally. `motodiag.api.errors` logs the original `XOwnershipError` even though the response is generic 404.

## Precedent body (existing endpoints implementing this policy)

| Phase | Module | Pattern |
|---|---|---|
| Phase 182 | `motodiag.api.routes.reports` | `get_session_for_owner` → `SessionOwnershipError` → 404 cross-user. Reports are sensitivity-high (may contain billing/tier data). |
| Phase 188 | `motodiag.api.routes.vehicles` | `VehicleOwnershipError` → 404 cross-user. Module docstring: "Cross-user vehicles return 404 (not 403) — standard enumeration-prevention." |
| Phase 189 | `motodiag.api.routes.sessions` | `SessionOwnershipError` → 404 cross-user. Module docstring: "Cross-user sessions return 404 (not 403). Lifecycle transitions (close/reopen) are dedicated routes that preserve the same posture." |
| Phase 191B | `motodiag.api.routes.videos` | `VideoOwnershipError` → 404 cross-user. Includes the binary file-stream route — auth-on-binary inherits the same 404 posture. |
| Phase 192 (this phase) | `motodiag.api.routes.reports` (extension via `build_session_report_doc`) | Inherits Phase 182's pattern; mobile viewer reads `GET /v1/reports/session/{id}` and sees 404 on cross-user. |

Five phases, identical posture. The ADR formalizes a 4-phase convention that was already self-consistent before formalization.

## When this policy doesn't apply

The policy is scoped to **owned resources read by their owner**. It does not apply to:

- **Knowledge-base endpoints** (`/v1/kb/*` per Phase 179) — public-tier read access; DTC codes + symptoms + known-issues are non-owned reference data. No `XOwnershipError` shape; no cross-owner concept; no 404-vs-403 nuance.
- **Health + version endpoints** (`/v1/meta/*` per Phase 175) — no auth, no owner. Returns the same data to every caller.
- **WebSocket live-data endpoints** (`/v1/sessions/{id}/live` per Phase 181) — auth-on-WS-handshake follows a different protocol (custom close codes per Phase 181's `WS_CLOSE_*` constants); the 404-vs-403 framing doesn't apply to WS-frame-level errors.
- **Shop-management writes** (Phase 172) — uses RBAC permission check, not owner-only. Cross-shop access returns 403 (shop existence is sensitive only at the shop-membership-management level).
- **Billing webhook routes** (Phase 176) — Stripe-signed webhook; no user-auth context.

The policy applies to: vehicles, sessions, fault codes, symptoms, diagnoses, videos, video binary files, reports (current scope). It applies to: future read endpoints for owned resources whose existence/non-existence would leak meaningful information to non-owners.

## Related decisions

- **F32 (deferred)**: migrate dict-based `ReportDocument` to typed Pydantic when a third report-consuming surface lands. Independent of this ADR; auth posture is shape-independent.
- **F22 (deferred)**: TAG_CATALOG full FastAPI introspection refactor. Independent of this ADR.
- **Phase 172 RBAC** (shop-tier permissions): shop-membership check is a separate policy axis from owner-only. The two compose: a shop's reports might be shop-tier-member-readable; a session's reports are owner-only-readable. Future phases that add shop-scoped reads should use the RBAC check, not adapt this owner-only policy to handle shop-scope.

## Edge cases

The policy is uniform but not exhaustive. Several boundary cases warrant explicit handling:

**Shop-tier-shared resources** (work orders, invoices, shop-management writes). These resources are NOT owner-only; they're shop-membership-scoped. Phase 172 RBAC is the canonical pattern: cross-shop access returns 403 (shop existence at the shop-management level IS sensitive — non-members shouldn't enumerate which shops exist — but the 403 is correct because the *resource type* membership is the access boundary, not per-resource ownership). Shop-tier-shared resources predate this ADR and follow a different policy axis; the ADR doesn't override them.

**Admin / impersonation auth** (not yet implemented). When a future support-tooling phase adds admin impersonation (e.g., support engineer reading a customer's session for debugging), the impersonation auth path will need its own audit logging — but the response shape from the user-facing route should not expose the impersonation. Impersonated reads return the same 200/404 envelope as the impersonated user would see; impersonation is recorded server-side, not in the wire response.

**Magic-link / token-scoped sharing** (Phase 192B candidate, deferred). When a user explicitly shares a report via magic-link, the receiver's auth context is the link's embedded token, not their personal API key. The link's auth path validates the token + serves the resource regardless of the receiver's user_id. This doesn't violate the owner-only policy because the policy applies to **personal-API-key-authed routes**; magic-link routes are a separate auth surface. If 192B implements magic-link sharing, it should be a NEW route (`/v1/share/{token}`) with explicit policy carve-out, not an existing-route override.

**WebSocket frame-level errors** (Phase 181). Live data streams use custom WS close codes (`WS_CLOSE_INVALID_KEY = 4401`, `WS_CLOSE_SESSION_NOT_FOUND = 4404`, etc.). The 404-vs-403 framing doesn't apply at the frame level; auth-on-WS-handshake follows Phase 181's protocol. The policy's spirit is preserved: cross-owner WS subscription attempts close with `WS_CLOSE_SESSION_NOT_FOUND` (the 4404 close code), not a "forbidden" code.

**Bulk operations** (e.g., `GET /v1/sessions?include_all=true` if such a thing landed). The policy applies per-resource, not per-route. A bulk-read route filters server-side to the owner's resources before returning; non-owner items are silently absent from the response (not surfaced as 403/404 per-item). This is the natural extension — "you don't know what you don't see" is the same enumeration-prevention principle applied to list-shape responses.

**Public-tier knowledge base** (Phase 179). DTC code lookups, symptom catalogs, known-issues — non-owned reference data. No 404-vs-403 nuance because there's no owner; the resources are public to authenticated callers. Cross-resource access is a non-concept.

**Webhook routes** (Phase 176 Stripe). Stripe-signed webhooks have no user-auth context; they're authed by the webhook-signature header. The policy doesn't apply.

## Discovering a phase that violated the policy — remediation playbook

If a future architect finds a Phase 193+ route that uses `require_tier()` for owner-only reads, OR returns 403 on cross-owner of an owned resource, OR otherwise deviates from this policy:

1. **Audit scope**: identify all routes in the offending phase. The deviation may be one route (mistake) or systematic (the contributor didn't read this ADR). One-route fixes are surgical; systematic fixes are phase-shaped.
2. **Severity triage**: tier-gated reads (denying free-tier access to owned resources) is a USER-VISIBLE bug — fix immediately + bump the pyproject patch version + smoke-test. 403-not-404 cross-owner is a SECURITY bug (enumeration vector) — same urgency, may warrant security advisory if the affected route was in production for material time.
3. **Refactor pattern**: replace `require_tier(...)` dependency injection with the owner-only `get_X_for_owner(resource_id, user_id, db_path)` repo pattern. Replace any explicit 403 raise with the `XOwnershipError` exception class from the resource's repo module; the existing exception handler maps to 404.
4. **Test coverage**: add the F29 smoke pattern to the affected phase's test file: cross-owner read → assert 404; free-tier owner read → assert 200.
5. **Documentation**: update this ADR's precedent body with the discovered phase + the refactor commit hash. The ADR's "Maintenance" section explicitly invites these updates.
6. **Lint candidate**: if the deviation surfaced multiple times across phases, file F-ticket candidate (per "Notes on enforcement" below) — recurrence is the trigger for promoting from convention-enforcement to lint-enforcement.

The playbook exists because Phase 192's v1.0.1 reshape was a discovery moment: plan v1.0 specified an auth posture that didn't match the existing convention. The architect-side audit caught it pre-Commit-1, but the same shape could surface mid-implementation in a future phase with less attentive pre-build review. The remediation playbook makes the recovery cheap.

## Notes on enforcement

The policy is currently enforced by convention (every read endpoint uses the same shape). Convention works well today because:

- The precedent body is consistent (4 phases, identical posture).
- The repo pattern (`get_X_for_owner` + `XOwnershipError`) is mechanical and copy-paste-able for new resources.
- The F29 smoke gate (per any phase introducing a read endpoint) catches deviations before merge.

Convention will break when:

- A new contributor implements a read endpoint without reading this ADR or the precedent code (likely; turnover is real).
- A future phase introduces a resource where the `(id, user_id)` ownership model doesn't fit (e.g., shared-team resources without shop-membership semantics) — the new resource needs an auth posture that doesn't match the canonical pattern, and the convention-by-imitation breaks at the moment the new pattern lands.

A lint-style enforcement would catch drift earlier:

- **F-ticket candidate**: extend `scripts/check_f9_patterns.py` with a `--check-auth-policy` mode. AST-walks `src/motodiag/api/routes/**/*.py`, identifies each route's auth dependency injection (`Depends(require_tier(...))`, `Depends(require_api_key)`, `Depends(get_current_user)`, etc.), and flags:
  - Read-shaped routes (`@router.get(...)`) using `require_tier()` (should use owner-only `get_current_user` + repo-level `get_X_for_owner`).
  - Routes that explicitly raise `HTTPException(403, ...)` for cross-owner cases instead of relying on the repo-level `XOwnershipError → 404` mapping.
  - Routes that don't include `Depends(get_current_user)` AND aren't in the public-tier exempt list (`/v1/kb/*`, `/v1/meta/*`, `/v1/billing/webhooks`).

  Per the F9 pattern doc subspecies (ii) generalized: parallel-state stores drift; lint enforcement converts silent drift to noisy findings on the inaugural run. Same shape as Phase 191D's `--check-tag-catalog-coverage` rule.

- **Promotion trigger**: file the F-ticket when a Phase 193+ contributor accidentally adds `require_tier` to a read endpoint AND it ships to master before review catches it. The actual incident is data point 1 toward the lint rule's introduction. Until then, this ADR + the smoke-gate template are the first-line guarantees.

Until lint enforcement lands, ADR + smoke-gate verification are the policy's first-line guarantees. ADR documents intent + remediation playbook; smoke gates verify implementation. The combination has held for 4 phases; the assumption is convention + ADR holds for ~10 more phases before lint becomes worth the implementation cost.

## Maintenance

Update this ADR when:

- A new policy alternative becomes credible (e.g., the project adopts UUID resource IDs, removing the enumeration-prevention rationale; revisit A2/A3).
- A new sensitive resource class emerges that warrants a separate policy axis.
- A future phase deliberately deviates from the policy (e.g., a shop-tier-member-readable shop report; document the deviation alongside the existing precedent body).

The ADR is a working document, not a sealed-history record. Per Phase 191C v1.0.1's audit-trail-preservation principle: append updates to a "Revision history" section at the bottom rather than overwriting earlier content. Future contributors reading the doc see both the current policy and how it evolved.
