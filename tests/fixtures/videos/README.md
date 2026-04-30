# Phase 191B test video fixtures

This directory holds tiny synthetic mp4 fixtures used by
`tests/test_phase191b_ffmpeg.py` (and Commit 2's
`tests/test_phase191b_video_analysis_pipeline.py`).

## Why no committed binary?

The fixture mp4 binary is **not** committed to git. Phase 191B
Commit 1's Builder agent runs in a sandbox that may not have ffmpeg
installed, and a placeholder file would break the real-ffmpeg test
class. The architect (or anyone running the test suite locally with
ffmpeg installed) regenerates the fixture per the recipe below; the
test class auto-skips when the fixture is absent, so missing-fixture
runs pass cleanly.

## Regen procedure

```bash
ffmpeg -y \
    -f lavfi \
    -i testsrc=duration=3:size=320x240:rate=30 \
    -c:v libx264 \
    -t 3 \
    sample_3sec.mp4
```

Expected output: `sample_3sec.mp4`, ~50 KB, 320x240, 30 fps, 3 seconds.
The synthetic `testsrc` source produces a moving test pattern with no
audio track on most ffmpeg builds.

## How tests reference this directory

```python
FIXTURE_VIDEO = (
    Path(__file__).parent / "fixtures" / "videos" / "sample_3sec.mp4"
)
```

The `real_ffmpeg` pytest marker in `test_phase191b_ffmpeg.py` skips
the entire `TestRealFFmpeg` class when either the ffmpeg binary or
this fixture file is missing — so a Builder sandbox without ffmpeg
will not block the suite.
