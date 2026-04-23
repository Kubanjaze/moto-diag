# MotoDiag Phase 181 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0. Scope: WebSocket transport for live OBD sensor streams.
First non-CRUD endpoint type on Track H. `LiveReadingProvider` ABC +
`FakeLiveProvider` (tests/dev) + Phase 140 `OBDLiveProvider`
(production wiring deferred — hooks in place).

Auth via query param OR `Sec-WebSocket-Protocol: bearer.<key>`.
Cross-user sessions = 4404 close. Custom 4xxx close codes for
auth/sub/notfound errors; 4500 for provider errors. Rate limiter
exempts `/v1/live/*` paths. ~280 LoC + ~18 tests.
