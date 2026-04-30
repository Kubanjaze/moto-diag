# Anthropic Vision response fixtures (Phase 191B)

Fixtures here are **synthesized** from the Anthropic Python SDK's
`anthropic.types.Message` + `anthropic.types.ToolUseBlock` type
definitions. They are **NOT** recorded from real API calls.

The Phase 191B Commit 2 unit tests in
`tests/test_phase191b_video_analysis_pipeline.py` build their fake
`Message` shapes inline via `SimpleNamespace` rather than loading these
JSON files. The JSON fixtures here are for:

1. **Eyeball-level documentation** of the SDK shape the pipeline expects
   (so a future maintainer can read the JSON and understand what a real
   `tool_use` response with `report_video_findings` looks like without
   running a real API call themselves).
2. **Future test expansion** — integration-level tests in Phase 191B
   Commit 3+ may load these directly to mock the SDK at a higher
   fidelity than `SimpleNamespace`.

For production-grade fidelity (e.g., before a Phase 191B production
deploy or a major SDK upgrade), regenerate these via:

```
.venv\Scripts\python.exe tests\fixtures\anthropic_responses\_regen.py
```

Requires `ANTHROPIC_API_KEY` and 1-3 motorcycle JPEG frames at
`tests/fixtures/sample_frames/*.jpg`. See the regen script's docstring
for full instructions.

## Files

- `_regen.py` — regen script (architect-side, requires API key)
- `video_analysis_happy.json` — synthetic finding-rich response
  (3 findings: smoke + wear + gauge_reading)
- (Future) `video_analysis_clean.json` — no-findings response

## Phase 190 Bug 2 reminder

Mocked SDK responses pulled from real API calls catch shape drift that
hand-authored fixtures miss. The synthetic fixtures here are good
enough for Commit 2's unit-level pipeline tests, but any gate-level
test that exercises the full upload -> analyze -> findings round-trip
should regenerate these from a live API call before relying on them.
