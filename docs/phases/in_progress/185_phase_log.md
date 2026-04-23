# MotoDiag Phase 185 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-23
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-23 — Plan written

Plan v1.0. **Opens Track I** with a formal architecture decision
record (ADR) capturing 7 mobile-app decisions:
1. React Native (bare, not Expo managed).
2. TypeScript with `strict: true`.
3. Sibling repo at `C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\`.
4. Zustand for client state + TanStack Query for server cache.
5. `openapi-fetch` client auto-generated from Phase 183 spec.
6. TanStack Query persistent cache + op-queue for offline.
7. `react-native-ble-plx` for Bluetooth OBD, feature-flagged
   behind a native-module boundary.

Output: `docs/mobile/ADR-001-framework-choice.md` plus this
phase_log.md + implementation.md. No Python code, no migration.
Project version 0.13.0 → 0.13.1.

Phase 186 (scaffold + CI/CD) will create the actual mobile repo
at the sibling path. Phase 185 is the durable rationale doc
Track I phases reference.
