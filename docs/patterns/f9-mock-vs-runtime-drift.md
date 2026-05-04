# F9 — Mock-vs-Runtime Drift Failure Family

> Earlier closure docs from Phase 191B refer to "6 instances" of this family. That count merged the two distinct bugs fixed in commit 832579d (deploy-path-missing-wiring and format-coincidence-latent / self-validating-test-setup) into a single instance. Going forward, this catalog tracks them as separate subspecies. **Total instances: 7.**

## Problem statement

Tests pass against assumptions baked into mocks; production fails when reality diverges.

The shape repeats with depressing regularity. A test stubs out a boundary — an HTTP call, a native module, a database write, an environment-coupled side effect — and asserts on the stub's behavior. The stub honors a contract the test author *believes* the real system enforces. The real system enforces a different contract, or a related contract with a subtly different shape (an extra envelope key; a snake_case field where the mock used camelCase; a `Promise<unknown>` where the mock returned a fully-typed `Promise<T>`; a callback fired at time T2 instead of T1, after closed-over state has mutated). Pytest is green. Jest is green. Production is broken the moment a real client hits the system.

The pattern is *not* "the test author was lazy." Every instance below was authored by an engineer who understood the test's purpose and made a deliberate stub choice. The drift is structural: a mock is a model of reality, and models exist to *omit* details. The exact details that get omitted are the ones the bug exploits. Without an explicit catalog of where drift has historically lived in this codebase, every new test author re-imports the same omissions on a fresh boundary, and the family of bugs reproduces under a new banner.

This doc is the explicit catalog. It also documents the lint rules that catch four of the five subspecies statically, and the doc-only recognition heuristic that catches the fifth — because the fifth subspecies is structurally non-lintable and the only mitigation is reviewer attention against a written pattern.

The broader software-engineering literature names neighboring patterns: "the test-double trap," "mocking the wrong thing," "tests that pass against themselves." The F9 family overlaps each of those but is narrower: F9 specifically describes the gap between *what the test believed about a boundary* and *what the system actually does at that boundary in production*. Subspecies (i) — (v) below partition that gap by mechanism.

## Why this matters

Each F9 bug costs roughly four to six architect-hours per fix-cycle: the time from smoke halt → diagnosis → fix → re-verify → re-smoke, including the architect-context cost of pausing whatever feature work was in flight. Across seven instances on Track I (Phase 188 / Phase 190 / Phase 191 / Phase 191B four instances), the cumulative budget exhausted is somewhere in the 28-to-42 architect-hour range, plus the soft cost of trust erosion in the mobile + backend test suites every time a green build ships a regression to a smoke runbook.

The cost of building the intervention infrastructure (this pattern doc + the lint rules in Phase 191C's other commits) is roughly five commits and six-to-ten architect-hours. The math says: ship the intervention now to cap future loss. After the seventh instance crossed the line where the cumulative cost of *not having infrastructure* now exceeds the cost of *building infrastructure*, the architect's PASS-handoff observation at Phase 191B finalize was: "the pattern is robust enough to merit dedicated mitigation infrastructure." Phase 191C is the discharge of that observation.

The lint rules cover six of the seven instances (subspecies i, ii, iii, iv together catch instances #1, #2, #3, #4, #6, #7). The seventh (instance #5, subspecies v "self-validating-test-setup") is structurally non-lintable; this doc's recognition heuristic is the only mitigation. The honest claim is **6 of 7 caught by lint, 1 by doc.**

## The 7 subspecies (case study catalog)

Each instance is presented with: the bug as it appeared in production, the mock-vs-runtime gap (the F9 essence), an anti-example derived from the actual buggy code, the fix pattern derived from the fix commit, a recognition heuristic for spotting the same shape in unfamiliar code, and the lint coverage that catches it.

### Instance #1 — Phase 188 Commit 7 [2026-04-26]

**Subspecies**: (iii) loose-typed async mock returns

**The bug**: HVE (HTTPValidationError) wrapper assumed a Phase 175 ProblemDetail envelope (`{title, status, detail?}`). FastAPI's 422 response body is `{detail: [{loc, msg, type, ...}]}` — not wrapped in the Phase 175 envelope. `isProblemDetail` returned false; `describeError` fell through to `String(err)` and rendered `"[object Object]"` to the user.

**The mock-vs-runtime gap**: tests mocked the API client's error responses with the Phase 175 envelope shape because that is the shape the rest of the codebase had standardized on. The *actual* FastAPI 422 path bypasses Phase 175's middleware envelope (validation errors are raised before the envelope wraps them). Tests passed against a shape that production's validation path never produces.

**Anti-example code**:

```ts
const mockApi = {
  POST: jest.fn().mockResolvedValue({
    data: undefined,
    error: {
      title: 'Validation error',
      status: 422,
      detail: 'Invalid input',
    } as any,  // Mock matches Phase 175 envelope
  }),
};

// Production:
// FastAPI's 422 returns {detail: [{loc, msg, type, ...}]}
// describeError(err) treats it as ProblemDetail; isProblemDetail returns false;
// fallback path renders String(err) = "[object Object]"
```

**Fix pattern**:

```ts
import type {components} from '../../src/api-types';
type HTTPValidationError = components['schemas']['HTTPValidationError'];

function isHTTPValidationError(value: unknown): value is HTTPValidationError {
  return (
    typeof value === 'object' &&
    value !== null &&
    Array.isArray((value as HTTPValidationError).detail) &&
    (value as HTTPValidationError).detail.every(
      d => typeof d === 'object' && d !== null && 'loc' in d && 'msg' in d,
    )
  );
}

function describeError(err: unknown): string {
  if (isProblemDetail(err)) return formatProblemDetail(err);
  if (isHTTPValidationError(err)) return formatValidationError(err);
  return 'Unknown error';  // never falls through to String(err)
}
```

**Recognition heuristic**: any function that handles errors from a typed API client should branch on *every* error shape the typed client can produce, not just the project's "preferred" error envelope. If you find yourself writing `} catch (err) { return String(err); }` or returning a generic message for "anything else," ask: have I enumerated *every* error type the OpenAPI spec declares for this endpoint? Mocks that return only the preferred shape don't exercise the unenumerated branches.

**Lint coverage**: subspecies (iii) — `motodiag/no-loose-typed-async-mock-returns` would have caught this. The mock's `as any` cast on the error object is the surface the rule fires on; the mock would have been forced to declare an explicit `Promise<{data: ..., error: HTTPValidationError | ProblemDetail}>` type, which would have forced the test author to enumerate the branches in `describeError` to satisfy the type check.

**Fix commit**: `eb42c21` (Phase 188 Commit 7)

---

### Instance #2 — Phase 190 Commit 7 [2026-04-28]

**Subspecies**: (iii) loose-typed async mock returns

**The bug**: KB endpoints (`kb.py`) raised stock FastAPI `HTTPException(404, detail=...)` whose body shape is `{detail: string}`, not Phase 175's `{title, status, detail?}` envelope. The Phase 190 mobile commit-1 code distinguished 404 from generic errors via substring-match on the rendered message: `error.toLowerCase().includes('not found')`. With "[object Object]" as the message (from the same describeError fallback as Instance #1), the substring check failed and the screen showed the generic-error branch (Retry/Back) instead of the dedicated "DTC code not found" UX.

**The mock-vs-runtime gap**: tests mocked the 404 response with `{title: 'Not found', status: 404, detail: 'DTC code not found'}` (Phase 175 shape) because that's how all the *intentionally raised* errors in the codebase look. FastAPI's stock `HTTPException` skips the envelope. Substring-match-on-error-text is itself a fragile contract — even with a correct envelope, the substring "not found" is a presentation detail, not a discriminator. The mock asserted the assumption into place.

**Anti-example code**:

```ts
// useDTC hook
return useQuery({
  queryKey: ['dtc', code],
  queryFn: async () => {
    const {data, error} = await api.GET('/v1/kb/dtc/{code}', {params: {path: {code}}});
    if (error) throw new Error(formatError(error));
    return data;
  },
});

// DTCDetailScreen
if (error) {
  if (error.message.toLowerCase().includes('not found')) {
    return <NotFoundUI />;  // BUG: substring-match assumes wire format
  }
  return <GenericErrorUI />;
}
```

**Fix pattern**:

```ts
// hooks/dtcErrors.ts (NEW)
export type DTCError =
  | {kind: 'not_found'; message: string}
  | {kind: 'server'; message: string}
  | {kind: 'network'; message: string}
  | {kind: 'unknown'; message: string};

export function classifyDTCError({status, body, thrownError}: ClassifyArgs): DTCError {
  if (thrownError) return {kind: 'network', message: 'No connection to backend'};
  if (status === 404) return {kind: 'not_found', message: extractErrorMessage(body) ?? 'DTC code not found'};
  if (status >= 500) return {kind: 'server', message: 'Server error'};
  return {kind: 'unknown', message: extractErrorMessage(body) ?? "Couldn't load DTC"};
}

export function extractErrorMessage(body: unknown): string | null {
  // Handles BOTH Phase 175 ProblemDetail (title + optional detail) AND
  // FastAPI HTTPException default ({detail: string}); falls back to null
  // for unrecognized shapes so callers synthesize a meaningful fallback.
  if (isProblemDetail(body)) return body.detail ?? body.title;
  if (isFastAPIDetailString(body)) return body.detail;
  return null;
}

// DTCDetailScreen
const titleMap: Record<DTCError['kind'], string> = {
  not_found: 'DTC code not found',
  network: 'No connection to backend',
  server: 'Server error',
  unknown: "Couldn't load DTC",
};
return <ErrorUI title={titleMap[error.kind]} retry={error.kind !== 'not_found'} />;
```

**Recognition heuristic**: any error UX branched on a string predicate (`includes`, `startsWith`, `match`) is a smell. Discriminator the error at the network layer where the status code + body shape are still typed; pass a discriminated union to the UI. Substring-match across the network → render boundary is always a mock-vs-runtime hazard because the mock can produce *any* string the test author wants.

**Lint coverage**: subspecies (iii) — the underlying issue is that the test mocked an error with a substring-friendly string. A typed-Promise mock would have forced the response shape to declare `{detail: string}` (FastAPI HTTPException) vs `{title, status, detail?}` (ProblemDetail) as separate types, which would have made the substring shortcut visibly wrong at the type level.

**Fix commit**: `744becf` (Phase 190 Commit 7)

---

### Instance #3 — Phase 191 Commit 3 follow-up [2026-04-28]

**Subspecies**: (i) closure-state capture in native callbacks

**The bug**: `cameraRef.current?.startRecording({onRecordingFinished: video => {...}})` registers a callback that closes over `state` from `useReducer`. By the time `onRecordingFinished` fires (seconds or minutes later, after the user has backgrounded the app and the AppState handler has dispatched a transition into `state.kind === 'stopping'` with `state.reason === 'interrupted'`), the closed-over `state` is still the registration-time snapshot. The callback always sees `wasInterrupted = false` even when production runtime semantically implies `wasInterrupted = true`. The "⏸ Paused at 0:14" badge never rendered on the saved-preview tile when AppState backgrounded mid-record.

**The mock-vs-runtime gap**: jest tests for VideoCaptureScreen mocked `cameraRef.current.startRecording` and immediately invoked the passed `onRecordingFinished` synchronously. With synchronous invocation, the closure captured the *most recent* dispatch — which the test had set up immediately before. So the closure's view of `state` matched the test's expectation. In production, the callback fires *asynchronously* after the user-driven transition, and the closure's view of `state` is stale.

**Anti-example code**:

```ts
const [state, dispatch] = useReducer(recordingTransition, initialRecordingState);

useEffect(() => {
  const sub = AppState.addEventListener('change', next => {
    if (next === 'background' && state.kind === 'recording') {
      dispatch({type: 'INTERRUPT'});  // transitions to {kind: 'stopping', reason: 'interrupted'}
      cameraRef.current?.stopRecording().catch(() => undefined);
    }
  });
  return () => sub.remove();
}, [state.kind]);

const handleStartRecording = () => {
  cameraRef.current?.startRecording({
    onRecordingFinished: video => {
      // BUG: state captured at registration time. By the time
      // onRecordingFinished fires, state may have transitioned via
      // AppState handler — but THIS callback sees the snapshot.
      const wasInterrupted = state.kind === 'stopping' && state.reason === 'interrupted';
      dispatch({type: 'FINISHED', video, wasInterrupted});
    },
    onRecordingError: err => dispatch({type: 'ERROR', err}),
  });
};
```

**Fix pattern** (commit `ffa383c`):

```ts
const [state, dispatch] = useReducer(recordingTransition, initialRecordingState);
const interruptedRef = useRef<boolean>(false);

useEffect(() => {
  const sub = AppState.addEventListener('change', next => {
    if (next === 'background' && state.kind === 'recording') {
      interruptedRef.current = true;  // set BEFORE stopRecording
      cameraRef.current?.stopRecording().catch(() => undefined);
    }
  });
  return () => sub.remove();
}, [state.kind]);

const handleStartRecording = () => {
  interruptedRef.current = false;  // reset at every start
  cameraRef.current?.startRecording({
    onRecordingFinished: video => {
      const wasInterrupted = interruptedRef.current;  // reads at fire time, not registration time
      dispatch({type: 'FINISHED', video, wasInterrupted});
    },
    onRecordingError: err => dispatch({type: 'ERROR', err}),
  });
};

const handleStopRecording = () => {
  interruptedRef.current = false;  // user-initiated, not interrupted
  cameraRef.current?.stopRecording().catch(() => undefined);
};
```

**Recognition heuristic**: any callback function literal passed *into* a native module's `.current.method({...})` call is suspect. Native modules (Camera, BLE, Bluetooth, NFC, fetch with abort signal, IntersectionObserver, etc.) routinely fire callbacks at times the React render cycle does not anticipate. If the callback body reads any `useState` / `useReducer` getter from an enclosing scope, the closure captures the registration-time value, not the fire-time value. The fix is `useRef` for the values the callback needs to read at fire time.

**Lint coverage**: subspecies (i) — `motodiag/no-closure-state-capture-in-native-callback` fires when (1) a callback function literal is passed as a property value to a `*.current.*` member call, AND (2) the function body references at least one identifier resolving to a `useState` / `useReducer` getter binding in an enclosing scope, AND (3) the identifier isn't a `.current` ref access on a `useRef`-declared binding, AND (4) no `// eslint-disable-next-line motodiag/no-closure-state-capture-in-native-callback` opt-out is present.

**Fix commit**: `ffa383c` (Phase 191 Commit 3 follow-up)

---

### Instance #4 — Phase 191B Commit 1 fix-cycle-1 [2026-05-01]

**Subspecies**: (iv) deploy-path missing wiring

**The bug**: `motodiag serve` command launched uvicorn but never invoked `init_db()`. `init_db()` is the function that applies pending Alembic migrations and brings the SQLite schema up to `SCHEMA_VERSION`. Backend code was at `SCHEMA_VERSION = 39`; the on-disk database was at v38; pytest passed because pytest fixtures called `init_db()` on every test setup, masking the gap. Production smoke ran `motodiag serve`, hit the unmigrated DB, and `/v1/version` returned `schema_version=38` against v39 code paths. Latent since Phase 175.

**The mock-vs-runtime gap**: every test that talked to the database initialized a fresh DB via a fixture that called `init_db()`. Every CLI subcommand that touched the DB called `init_db()` as a precondition. The *only* code path that bypassed `init_db()` was the long-running server entry — and no test exercised the long-running server entry from the same code path the production deploy uses. The "test reality" had `init_db()` in the setup; the "production reality" had the unwired serve_cmd skipping it.

**Anti-example code**:

```py
# src/motodiag/cli/serve.py
@cli_group.command('serve')
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=8000, type=int)
def serve_cmd(host: str, port: int) -> None:
    """Launch the FastAPI server."""
    settings = get_settings()
    uvicorn.run(
        'motodiag.api:create_app',
        host=host,
        port=port,
        factory=True,
    )
    # BUG: no init_db() call. Schema stays at whatever version was last
    # applied — possibly stale relative to SCHEMA_VERSION in code.
```

**Fix pattern** (commit `832579d`):

```py
@cli_group.command('serve')
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=8000, type=int)
def serve_cmd(host: str, port: int) -> None:
    """Launch the FastAPI server."""
    settings = get_settings()
    init_db(settings.db_path, apply_migrations=True)  # required before serve
    uvicorn.run(
        'motodiag.api:create_app',
        host=host,
        port=port,
        factory=True,
    )
```

**Recognition heuristic**: every CLI subcommand that launches a long-running process (uvicorn, daemon, worker, scheduler, websocket server) must perform the same precondition setup that the rest of the system performs. Audit by asking: what setup functions does *every other CLI subcommand* call before doing real work? Are they all called from this long-running entry point too? Common omissions: `init_db()`, `apply_migrations()`, `load_seed_data()`, `validate_config()`, `connect_secrets_manager()`, `register_signal_handlers()`. Tests that mock the long-running entry point or skip it entirely will not catch the omission.

**Lint coverage**: subspecies (iv) — `scripts/check_f9_patterns.py --check-deploy-path-init-db` AST-walks `src/motodiag/cli/` for `*_cmd` Click commands invoking `uvicorn.run` / `app.run` / similar serve-the-API patterns. If found AND no `init_db(` call exists in the same function body, the script fires. Exempt clause: `# f9-noqa: deploy-path-init-db` comment on the line of the run invocation, with reason.

**Fix commit**: `832579d` (Phase 191B Commit 1 fix-cycle-1 — same commit as instance #5, different subspecies)

---

### Instance #5 — Phase 191B Commit 1 fix-cycle-1 [2026-05-01]

**Subspecies**: (v) self-validating-test-setup [DOC-ONLY]

**The bug**: `session_repo._month_start_iso()` returned a Python `datetime.isoformat()` string with `T` as the date-time separator (`'2026-05-01T00:00:00'`). Production code stored `created_at` via SQLite's `datetime('now')` default, which produces a space-separated format (`'2026-05-01 12:34:56'`). The read path compared `created_at >= month_start` lexicographically (string comparison on ISO-like prefixes). Lex comparison is correct *as long as both sides agree on the separator character*. ASCII `'T'` (0x54) is greater than ASCII space (0x20), so `'2026-05-01T00:00:00' > '2026-05-01 23:59:59'`, which means a session created at 23:59:59 on the first of the month was excluded from the month's quota check. Same-day-prefix lex comparison broke at the day-boundary and silently undercounted quota usage.

**The mock-vs-runtime gap (the F9 essence)**: test fixtures used the same `_month_start_iso()` helper to build the comparison data they then queried against. The function-under-test produced format X; the fixtures produced format X; the test passed because format-X compared cleanly with format-X. Production storage produced format Y (SQLite's `datetime('now')`); production reads compared format-Y data against format-X month_start; the format mismatch exposed the bug at the same-day-prefix boundary. **The test setup never crossed the language boundary that production crosses.** SQLite was never invoked in the test setup; only in production runtime.

**Anti-example code**:

```py
# repos/session_repo.py
def _month_start_iso(now: datetime | None = None) -> str:
    now = now or datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_start.isoformat()  # 'T' separator

def get_session_count_this_month(self, user_id: int) -> int:
    month_start = _month_start_iso()
    return self.db.execute(
        'SELECT COUNT(*) FROM sessions WHERE user_id = ? AND created_at >= ?',
        (user_id, month_start),
    ).fetchone()[0]

# tests/test_session_repo.py
def test_get_session_count_this_month(repo, user_id):
    # Insert via Python helper — uses datetime.isoformat() ('T' separator)
    repo.db.execute(
        'INSERT INTO sessions (user_id, created_at) VALUES (?, ?)',
        (user_id, datetime(2026, 5, 1, 12, 0, 0).isoformat()),  # '2026-05-01T12:00:00'
    )
    assert repo.get_session_count_this_month(user_id) == 1  # PASSES

# Production code path:
# CREATE TABLE sessions (..., created_at TEXT NOT NULL DEFAULT (datetime('now')))
# INSERT INTO sessions (user_id) VALUES (?)  -- created_at = '2026-05-01 12:00:00' (SPACE separator)
# get_session_count_this_month compares '2026-05-01 12:00:00' >= '2026-05-01T00:00:00' → FALSE
# Returns 0 — quota check undercounts.
```

**Fix pattern** (commit `832579d`):

```py
def _month_start_iso(now: datetime | None = None) -> str:
    now = now or datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_start.strftime('%Y-%m-%d %H:%M:%S')  # SPACE separator, matches SQLite datetime('now')

# tests/test_session_repo.py — fixtures rewritten to insert via SQLite default
def test_get_session_count_this_month(repo, user_id):
    # Insert via raw SQL using SQLite's datetime() — exercises production format
    repo.db.execute(
        "INSERT INTO sessions (user_id) VALUES (?)",  # created_at defaults to datetime('now')
        (user_id,),
    )
    assert repo.get_session_count_this_month(user_id) == 1
```

**The deeper insight**: any time a value crosses a boundary where the OTHER side stamps / transforms / parses, and the test setup stays on the function-side rather than reaching across, you have a self-validating test setup. The test passes because the function is being asked to compare its OWN output against its OWN output. Production fails because the OTHER side of the boundary produces a different shape.

**Cross-boundary categories where this pattern bites** (enumerate explicitly so future readers recognize at the next boundary):

- **Python ↔ SQLite**: helper produces ISO-T datetime; SQLite `datetime('now')` produces space-separated. Test writes via helper; production writes via SQLite default. (This instance.)
- **JS ↔ Android native**: jest mocks return JS-shaped objects; production receives native-bridge-marshaled responses with subtly different shapes (camelCase vs snake_case; nullable handling differing across the bridge; numeric overflow at 32-bit boundaries; arrays-as-NSArray vs arrays-as-JS-array; `undefined` round-tripping as `null`).
- **JSON serialize ↔ Date round-trip**: `JSON.stringify(new Date())` produces an ISO string; `JSON.parse(...)` returns a string, NOT a Date. Tests that round-trip via the same serializer never see the parse-side type loss. Production code that expects a Date instance after `JSON.parse` then calls `.getTime()` on a string and crashes.
- **OpenAPI spec ↔ FastAPI route handlers**: the spec is generated FROM the handlers, so a test that uses generated TypeScript types is effectively testing the handlers against themselves. Real wire shape differences (Pydantic `alias_generator` + `by_alias` serialization config; `Field(default=...)` vs `Field(default_factory=...)` semantics for null vs missing; envelope middleware that runs *after* the handler returns) only surface when a real client hits the real backend.
- **Frontend ORM ↔ database column**: ORM model declares `created_at: Date` (TS type); database stores `TIMESTAMP WITH TIME ZONE`; ORM driver returns a string in UTC; frontend code that constructs `new Date(row.created_at)` works in the ORM's test fixtures (which stamp via `new Date()` already) but produces unexpected timezone offsets in production where the database stamped via `now()` server-side.

**Recognition heuristic**: ask the reviewer-question: **"Did the test setup invoke the same code path that production WRITES through? Or did the test setup invoke the function-under-test to build the data the function-under-test will then consume?"** If the answer is the second, the test is self-validating and a format-coincidence bug is latent.

**Mitigation by category** (no lint rule possible — too case-specific; doc-only catch):

- **SQLite ↔ Python**: test fixtures should `INSERT` via raw SQL using `datetime('now')`, not via Python helpers that produce different formats. Co-locate the test-setup builder with the production write path.
- **JS ↔ native**: jest tests should invoke the native module's actual signature OR the test-setup builder should be co-located with the production write path. Avoid `as any` mock returns (subspecies iii's lint rule helps here).
- **JSON ↔ Date**: serialize with the same library production uses, not `JSON.stringify(new Date())` shortcuts in tests.
- **OpenAPI ↔ FastAPI**: smoke tests must hit a running backend with the actual production client (Phase 184's Gate 9 `Test API` setup pattern). Type-safety from generated types is necessary but NOT sufficient.
- **Frontend ORM ↔ database column**: integration tests must round-trip through the actual database driver, not the ORM's in-memory adapter or a faked driver.

**Lint coverage**: DOC-ONLY. Static analysis can't tell whether a test fixture was set up "from the right side" of an integration boundary — the bug shape is a runtime semantic mismatch between two valid code paths, neither of which is "wrong" in isolation. The mitigation is reviewer attention + the recognition heuristic above + the cross-boundary category enumeration that makes the next instance recognizable at the next boundary.

**Fix commit**: `832579d` (Phase 191B Commit 1 fix-cycle-1 — same commit as instance #4, different subspecies)

---

### Instance #6 — Phase 191B Commit 6 fix-cycle-2 [2026-05-03]

**Subspecies**: (iii) loose-typed async mock returns

**The bug**: `useSessionVideos.addRecording` passed `recording.sourceUri` AS-IS to `FormData.append`. On Android, `react-native-vision-camera` v4 returns `VideoFile.path` *without* the `file://` scheme. RN's networking layer requires the scheme for FormData multipart file uploads on Android. The upload failed with "Network request failed" and never reached the backend (no POST line in access log).

**The mock-vs-runtime gap**: jest tests mocked `api.POST` with a lazy `as any` return, so the real FormData → fetch path was never exercised. `FormData.append('file', {uri: ..., type: ..., name: ...})` is the React Native multipart contract; the URI must include the scheme on Android. The mock didn't care about the URI shape because the mock didn't actually do anything with it. Tests passed; production failed at the first real upload attempt.

**Anti-example code**:

```ts
// __tests__/hooks/useSessionVideos.test.ts
const mockApi = {
  POST: jest.fn().mockResolvedValue({data: {} as any, error: undefined}),  // BUG: lazy type
};
// Test passes; production fails because the real api.POST has a typed
// contract the mock doesn't honor, AND the real FormData → fetch path is
// never exercised so the file:// scheme bug is invisible.

// hooks/useSessionVideos.ts
const formData = new FormData();
formData.append('file', {
  uri: recording.sourceUri,  // BUG on Android: missing 'file://' scheme
  type: 'video/mp4',
  name: `recording-${recording.id}.mp4`,
} as any);
const {data, error} = await api.POST('/v1/sessions/{session_id}/videos', {
  params: {path: {session_id: sessionId}},
  body: formData as any,
});
```

**Fix pattern** (commit `7e9702e`):

```ts
// __tests__/hooks/useSessionVideos.test.ts
import type {paths} from '../../src/api-types';
type UploadResponse = paths['/v1/sessions/{session_id}/videos']['post']['responses']['201']['content']['application/json'];

const mockApi = {
  POST: jest.fn<
    Promise<{data: UploadResponse | undefined; error: unknown}>,
    [string, unknown]
  >().mockResolvedValue({
    data: {video_id: 1, status: 'uploaded'} satisfies UploadResponse,
    error: undefined,
  }),
};

// hooks/useSessionVideos.ts
const fileUri = Platform.OS === 'android' && !recording.sourceUri.startsWith('file://')
  ? `file://${recording.sourceUri}`
  : recording.sourceUri;
const formData = new FormData();
formData.append('file', {
  uri: fileUri,
  type: 'video/mp4',
  name: `recording-${recording.id}.mp4`,
} as any);
```

**Recognition heuristic**: every `jest.fn().mockResolvedValue(...)` call should have an explicit `Promise<T>` type argument where T is imported from the module being mocked. If you find yourself reaching for `as any` in a mock's return value, ask: what is the actual return type of the function I'm mocking, and why am I unable to satisfy it? Usually the answer is "I haven't bothered to import the type" — and importing it would expose a contract the mock isn't honoring, which is exactly the contract production will enforce.

**Lint coverage**: subspecies (iii) — `motodiag/no-loose-typed-async-mock-returns` fires on `jest.fn().mockResolvedValue(X)` where X contains `as any` / `as unknown as Y` / has no inferable type. The mock would have been forced to declare `Promise<UploadResponse>`, which would have surfaced the typed contract — and once a real typed mock was in place, an integration test (or even a more ambitious unit test that constructs a real FormData) would have surfaced the file:// scheme bug.

**Fix commit**: `7e9702e` (Phase 191B Commit 6 fix-cycle-2)

---

### Instance #7 — Phase 191B Commit 2 fix-cycle-4 [2026-05-04]

**Subspecies**: (ii) hardcoded source-of-truth values in tests

**The bug**: `MODEL_ALIASES['sonnet']` mapped to `'claude-sonnet-4-5-20241022'` — a fabricated model ID that does not exist in the Anthropic API's published model list. Vision analysis pipeline calls failed at the API boundary with model-not-found. The architect-gate Step 7 (Vision-failure path) fired correctly (because the call legitimately failed), masking the underlying bug as "Vision returned an error" until inspection of the request body revealed the bogus ID.

**The mock-vs-runtime gap**: 14 hardcoded test references to the bogus ID across 5 files were effectively *pinning the bug into place*. The tests ASSERTED the wrong value: `assert _resolve_model("sonnet") == "claude-sonnet-4-5-20241022"`. Pytest passed every run because the function returned exactly what the tests asserted. The tests were not checking that `_resolve_model("sonnet")` returned a *valid* model ID; they were checking that it returned the *same string the test author wrote down*. No test exercised the boundary between "what we resolve to" and "what the Anthropic API accepts." The mock-vs-runtime gap is the entire test suite agreeing with itself about a value that production rejects.

**Anti-example code**:

```py
# src/motodiag/engine/client.py
MODEL_ALIASES = {
    'sonnet': 'claude-sonnet-4-5-20241022',  # BUG: fabricated, not in Anthropic API
    'haiku': 'claude-haiku-4-5-20251001',
    'opus': 'claude-opus-4-7',
}

# tests/test_phase79_engine_client.py
def test_resolve_sonnet_alias():
    assert _resolve_model('sonnet') == 'claude-sonnet-4-5-20241022'  # ASSERTS THE BUG INTO PLACE

# tests/test_phase120_vision_pipeline.py
@pytest.fixture
def vision_model() -> str:
    return 'claude-sonnet-4-5-20241022'  # 14 references like this across 5 files
```

**Fix pattern** (commit `c453872`):

```py
# src/motodiag/engine/client.py
MODEL_ALIASES = {
    'sonnet': 'claude-sonnet-4-6',  # corrected per CLAUDE.md system context
    'haiku': 'claude-haiku-4-5-20251001',
    'opus': 'claude-opus-4-7',
}

# tests/test_phase191b_vision_model_validation.py (NEW — anti-regression pin)
KNOWN_GOOD_MODEL_IDS = {
    'claude-opus-4-7',
    'claude-sonnet-4-6',
    'claude-haiku-4-5-20251001',
}
KNOWN_BOGUS_IDS = {
    'claude-sonnet-4-5-20241022',  # explicit anti-regression guard
}

def test_resolve_sonnet_alias_is_known_good():
    resolved = _resolve_model('sonnet')
    assert resolved in KNOWN_GOOD_MODEL_IDS, f'{resolved} not in CLAUDE.md May-2026 known-good set'
    assert resolved not in KNOWN_BOGUS_IDS, f'{resolved} is the architect-gate Step 7 anti-regression ID'

# All 14 hardcoded references across 5 files scrubbed — replaced with imports
# from MODEL_ALIASES or with KNOWN_GOOD_MODEL_IDS membership checks.
```

**Recognition heuristic**: any test that asserts a literal string equal to a configuration value is suspect. The test answers: "did the function return the string I wrote down?" — not "did the function return a *valid* value?" Either (a) the test should import the constant from the source-of-truth module and assert equality with the import (which makes the test essentially tautological but at least the source-of-truth update propagates), OR (b) the test should assert *membership* in a known-good set defined separately from the production code (which catches cases where the source-of-truth constant itself is wrong). The combination of (a) + (b) is the strongest pattern.

**Lint coverage**: subspecies (ii) — mobile `motodiag/no-hardcoded-model-ids-in-tests` fires on regex match `claude-(haiku|sonnet|opus)-\d` against literal strings inside `__tests__/**/*.{ts,tsx}`; backend `scripts/check_f9_patterns.py --check-model-ids` fires on the same regex against `tests/**/*.py`. Both rules exempt: strings appearing as values in `KNOWN_GOOD_MODEL_IDS` / `KNOWN_BOGUS_IDS` / `MODEL_ALIASES` / `MODEL_PRICING` set/dict literals. The hardcoded `'claude-sonnet-4-5-20241022'` in 14 test references would have lit up the rule on every file.

**Fix commit**: `c453872` (Phase 191B Commit 2 fix-cycle-4)

---

## The 5 subspecies + their mitigations

The seven instances above partition into five subspecies by mechanism. Lint coverage exists for four; the fifth is doc-only.

### Subspecies (i) — Closure-state capture in native callbacks

**Pattern**: callback function literals passed as values inside `*.current.*` member calls capture useState/useReducer values at registration time, not fire time.

**Lint rule (mobile)**: `motodiag/no-closure-state-capture-in-native-callback`

**Heuristic**: rule fires when (1) callback function literal is passed as a property value to a `*.current.*` member call, AND (2) the function body references at least one identifier resolving to a `useState` / `useReducer` getter binding in an enclosing scope, AND (3) the identifier isn't a `.current` ref access on a `useRef`-declared binding, AND (4) no `// eslint-disable-next-line motodiag/no-closure-state-capture-in-native-callback` opt-out is present.

**Exempt**: skip the rule entirely if the callback doesn't reference any non-ref state binding. **"Non-ref state binding" is scoped narrowly to bindings declared via `useState` or `useReducer` only** — not external store subscriptions (Redux / Zustand / Jotai / TanStack Query / etc.). External store subscriptions aren't the F9 subspecies this rule targets; their reactivity model is fundamentally different from local React state and they don't suffer the registration-time-capture bug shape because the subscription is itself a reactive read, not a closure capture.

**Fix pattern**: `useRef`. The ref's `.current` is read at fire time; the ref identity is stable across renders so the closure captures a stable reference, not a stale value.

```ts
// Anti-example — closure captures state
const [recording, setRecording] = useState(false);
cameraRef.current?.startRecording({
  onRecordingFinished: () => {
    if (recording) console.log('finished while recording');  // stale!
  },
});

// Fix — useRef reads at fire time
const recordingRef = useRef(false);
const handleStart = () => {
  recordingRef.current = true;
  setRecording(true);
};
cameraRef.current?.startRecording({
  onRecordingFinished: () => {
    if (recordingRef.current) console.log('finished while recording');  // current!
  },
});
```

### Subspecies (ii) — Hardcoded source-of-truth values in tests

**Pattern**: tests hardcode literal values that should reference a centralized source-of-truth set. When the value drifts (e.g., model ID gets renamed; route name gets versioned; schema field gets renamed), the tests ASSERT THE BUG INTO PLACE.

**Lint rule (mobile)**: `motodiag/no-hardcoded-model-ids-in-tests`
**Lint rule (backend)**: `scripts/check_f9_patterns.py --check-model-ids`

**Heuristic** (both stacks): regex match against literal strings matching the model-ID shape `claude-(haiku|sonnet|opus)-\d` appearing inside test files. Mobile scope: `__tests__/**/*.{ts,tsx}`. Backend scope: `tests/**/*.py`.

**Exempt** (both stacks): skip if the string appears as a value in an explicit allowlist set or pinned constants module. Backend exempt set: `KNOWN_GOOD_MODEL_IDS` / `KNOWN_BOGUS_IDS` / `MODEL_ALIASES` / `MODEL_PRICING`. Mobile exempt set: same conceptual list, in `as const` array literals whose name matches `KNOWN_*_MODEL_IDS`. Both stacks honor `// eslint-disable-next-line` (mobile) / `# f9-noqa: model-id` (backend) for one-off overrides with reason.

**Fix pattern**: import the constant from the source-of-truth module AND check membership in a known-good set defined separately.

### Subspecies (iii) — Loose-typed async mock returns

**Pattern**: `jest.fn().mockResolvedValue(X)` calls where X is `as any` / `as unknown as Y` / has no inferable type. Mocked async functions MUST return `Promise<T>` where T is the imported return type from the module being mocked.

**Lint rule (mobile)**: `motodiag/no-loose-typed-async-mock-returns`

**Heuristic**: AST match for `jest.fn().mockResolvedValue(...)` where the type argument to `jest.fn` is missing OR the resolved value contains `as any` / `as unknown as` (without a subsequent typed annotation matching `paths[...]` or `components['schemas'][...]` import from `api-types.ts`).

**Exempt**: the `as any` / `as unknown as` is followed by a TS-typed annotation matching a `paths[...]` or `components['schemas'][...]` import from `api-types.ts`. Also exempt: explicit `// eslint-disable-next-line` opt-out with reason.

**Fix pattern**: import the response type from the generated `api-types.ts` (or equivalent OpenAPI-generated types module) and pass it as the `jest.fn` type argument.

### Subspecies (iv) — Deploy-path missing wiring

**Pattern**: a CLI command that launches a long-running process (uvicorn, daemon, worker, scheduler) doesn't invoke the setup function the rest of the system relies on (`init_db`, `apply_migrations`, `load_seed_data`, `validate_config`). The setup function gets called implicitly in tests + via other CLI subcommands, masking the gap until production deploys hit the unwired path.

**Lint rule (backend)**: `scripts/check_f9_patterns.py --check-deploy-path-init-db`

**Heuristic**: AST walk over `src/motodiag/cli/` files. Find function definitions decorated with `@cli_group.command(...)` (or similar Click decorator). Inside the function body, check for `uvicorn.run` / `app.run` / similar serve-the-API patterns. If found AND no `init_db(` call exists in the same function body, fail.

**Exempt**: explicit `# f9-noqa: deploy-path-init-db` comment on the line of the run invocation, with reason.

**Fix pattern**: call `init_db(settings.db_path, apply_migrations=True)` immediately before `uvicorn.run(...)` in every long-running CLI entry.

### Subspecies (v) — Self-validating test setup [DOC-ONLY]

**Pattern** (the load-bearing recognition):

> The test exercised the function against itself instead of against the system the function integrates with.

**The deeper insight**: any time a value crosses a boundary where the OTHER side stamps / transforms / parses, and the test setup stays on the function-side rather than reaching across, you have a self-validating test setup. The test passes because the function is being asked to compare its OWN output against its OWN output. Production fails because the OTHER side of the boundary produces a different shape.

**Cross-boundary categories** (enumerate explicitly so future readers recognize at the next boundary): see Instance #5 above for the full list — Python ↔ SQLite, JS ↔ Android native, JSON ↔ Date round-trip, OpenAPI ↔ FastAPI, Frontend ORM ↔ database column.

**Recognition heuristic**: ask the reviewer-question: **"Did the test setup invoke the same code path that production WRITES through? Or did the test setup invoke the function-under-test to build the data the function-under-test will then consume?"** If the answer is the second, the test is self-validating and a format-coincidence bug is latent.

**Mitigation by category** (no lint rule possible — too case-specific; doc-only catch): see Instance #5 above for the per-category mitigation list.

**Lint coverage**: DOC-ONLY. Static analysis can't tell whether a test fixture was set up "from the right side" of an integration boundary — the bug shape is a runtime semantic mismatch between two valid code paths, neither of which is "wrong" in isolation. The mitigation is reviewer attention + the recognition heuristic above.

## When you suspect F9 in your code

A decision tree for new-code review. Walk it on every PR that touches a test file or a network/native/database boundary.

1. **Is the code a callback registered with a native module?** Camera, BLE, Bluetooth, NFC, fetch with abort signal, IntersectionObserver, MutationObserver, ResizeObserver, geolocation watch, push notifications, deep link handlers, in-app purchase listeners — anything where the callback fires asynchronously on an event the React render cycle doesn't drive. → Check **subspecies (i) closure-state capture**. Are you reading any `useState` / `useReducer` getter from the enclosing scope? Convert to `useRef`.

2. **Is the code a test asserting on a literal value that came from production config?** Model ID, route name, schema field name, environment variable name, feature flag name, error code string. → Check **subspecies (ii) hardcoded source-of-truth**. Either import the constant from the source module, or assert membership in a known-good set defined in the test, or both.

3. **Is the code a mock returning `as any` / `as unknown` typing?** `jest.fn().mockResolvedValue(...)`, `vi.fn().mockResolvedValue(...)`, hand-written stub objects with `as any` casts. → Check **subspecies (iii) loose-typed mock returns**. Import the real return type from the module being mocked. If the type is genuinely untyped third-party, narrow with a Zod / io-ts / similar validator and mock the validated shape.

4. **Is the code a CLI command launching a long-running process?** uvicorn, gunicorn, hypercorn, a custom worker loop, a scheduler, a websocket server, a daemon. → Check **subspecies (iv) deploy-path missing wiring**. Audit by asking: what setup functions does *every other CLI subcommand* call before doing real work? Are they all called from this long-running entry point too?

5. **Did the test setup write data via the function-under-test?** Did the test build its fixtures by calling the helper that the test then asserts against? Did the test mock the boundary the production code is supposed to integrate with, then assert that the mock returned what the mock was set up to return? → Check **subspecies (v) self-validating test setup**. Where does production WRITE that data, and is the test exercising THAT write path?

If you can't answer any of the above with confidence: pause and read the case study for that subspecies above. The mock-vs-runtime gap that bites you is almost always one you've seen before — the catalog exists so you don't have to rediscover it.

## Cross-references

- **Mobile copy of this doc**: `[link to mobile repo's docs/patterns/f9-mock-vs-runtime-drift.md]`
- **Phase 191C plan v1.0 + v1.0.1**: [link to backend repo's `docs/phases/completed/191C_implementation.md` once finalized]
- **Lint rule sources**:
  - `scripts/check_f9_patterns.py` (backend, this repo)
  - `eslint-plugin-motodiag/` (mobile, sibling repo)
- **Fix commits referenced**:
  - Phase 188 commit `eb42c21` (HVE shape mock — Instance #1)
  - Phase 190 commit `744becf` (substring-match discriminator — Instance #2)
  - Phase 191 commit `ffa383c` (closure-state capture — Instance #3)
  - Phase 191B commit `832579d` (deploy-path missing wiring + self-validating-test-setup — Instances #4 and #5, two subspecies same commit)
  - Phase 191B commit `7e9702e` (file:// scheme + loose-typed mock — Instance #6)
  - Phase 191B commit `c453872` (hardcoded model IDs across 14 references — Instance #7)
- **Architect-handoff observations** (Phase 191B finalize): "Pattern is robust enough that the architectural-pattern doc + lint rule should be Phase 192's lead ticket" — this doc is the discharge of that observation, scoped into Phase 191C as the substrate-then-feature precedent (Phase 191 → 191B → 191C as feature-then-meta-tooling-fix-from-lessons-learned).
