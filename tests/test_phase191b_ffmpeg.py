"""Phase 191B — ffmpeg subprocess wrapper tests.

Two test families:

1. **Mock-based tests** (no skip): exercise the wrapper logic — module-
   load detection with override, FFmpegMissing raised when binary is
   absent, exception types preserve stderr. These run on any host.

2. **Real-ffmpeg tests** (skip when ffmpeg or fixture is absent): drive
   actual frame extraction + audio sidecar + validate_video against a
   3-second synthetic mp4 fixture. The fixture is regenerated on demand
   per ``tests/fixtures/videos/README.md``.

Per Phase 191B v1.0.1, fixture binary is NOT committed by Builder —
the architect/CI generates it locally if ffmpeg is installed.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from motodiag.media import ffmpeg as ffmpeg_mod
from motodiag.media.ffmpeg import (
    FFmpegFailed,
    FFmpegMissing,
    extract_audio,
    extract_frames,
    validate_video,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


FIXTURE_VIDEO = (
    Path(__file__).parent / "fixtures" / "videos" / "sample_3sec.mp4"
)


def _have_ffmpeg() -> bool:
    """True iff a real ffmpeg binary is on PATH."""
    return shutil.which("ffmpeg") is not None


def _have_fixture() -> bool:
    return FIXTURE_VIDEO.exists()


real_ffmpeg = pytest.mark.skipif(
    not (_have_ffmpeg() and _have_fixture()),
    reason="real ffmpeg binary or fixture mp4 not available",
)


# ---------------------------------------------------------------------------
# 1. Module-load detection (no skip — fully mock-based)
# ---------------------------------------------------------------------------


class TestModuleLoadDetection:

    def test_module_load_detection_with_override_empty(self, monkeypatch):
        """FFMPEG_BIN_OVERRIDE='' → module-load resolves to None."""
        monkeypatch.setenv("FFMPEG_BIN_OVERRIDE", "")
        # Re-run the detection function directly (avoiding a full
        # module reload, which can interact badly with pytest).
        result = ffmpeg_mod._detect_ffmpeg()
        assert result is None

    def test_module_load_detection_with_nonexistent_path(self, monkeypatch):
        """FFMPEG_BIN_OVERRIDE pointed at a missing path → None."""
        monkeypatch.setenv("FFMPEG_BIN_OVERRIDE", "/no/such/path/ffmpeg")
        result = ffmpeg_mod._detect_ffmpeg()
        assert result is None

    def test_module_load_detection_with_real_path(
        self, monkeypatch, tmp_path,
    ):
        """FFMPEG_BIN_OVERRIDE pointed at an existing file → that path."""
        stub = tmp_path / "fake_ffmpeg"
        stub.write_text("#!/bin/sh\nexit 0\n")
        monkeypatch.setenv("FFMPEG_BIN_OVERRIDE", str(stub))
        result = ffmpeg_mod._detect_ffmpeg()
        assert result == str(stub)


# ---------------------------------------------------------------------------
# 2. Missing-binary error path (no skip)
# ---------------------------------------------------------------------------


class TestFFmpegMissingPath:

    def test_extract_frames_raises_FFmpegMissing_when_absent(
        self, monkeypatch, tmp_path,
    ):
        monkeypatch.setattr(ffmpeg_mod, "FFMPEG_BIN", None)
        with pytest.raises(FFmpegMissing):
            extract_frames(
                Path("/nonexistent.mp4"),
                tmp_path / "frames",
            )

    def test_extract_audio_raises_FFmpegMissing_when_absent(
        self, monkeypatch, tmp_path,
    ):
        monkeypatch.setattr(ffmpeg_mod, "FFMPEG_BIN", None)
        with pytest.raises(FFmpegMissing):
            extract_audio(
                Path("/nonexistent.mp4"),
                tmp_path / "out.mp3",
            )

    def test_validate_video_raises_FFmpegMissing_when_absent(
        self, monkeypatch,
    ):
        monkeypatch.setattr(ffmpeg_mod, "FFMPEG_BIN", None)
        with pytest.raises(FFmpegMissing):
            validate_video(Path("/nonexistent.mp4"))


# ---------------------------------------------------------------------------
# 3. Subprocess error handling (no skip — uses mock subprocess.run)
# ---------------------------------------------------------------------------


class TestSubprocessErrorHandling:

    def test_extract_frames_raises_on_nonzero_exit(
        self, monkeypatch, tmp_path,
    ):
        monkeypatch.setattr(ffmpeg_mod, "FFMPEG_BIN", "/fake/ffmpeg")
        fake = mock.MagicMock(returncode=1, stderr="something broke")
        with mock.patch.object(
            subprocess, "run", return_value=fake,
        ):
            with pytest.raises(FFmpegFailed) as exc:
                extract_frames(
                    Path("/x.mp4"),
                    tmp_path / "frames",
                )
        assert exc.value.stderr == "something broke"
        assert "ffmpeg exited 1" in str(exc.value)

    def test_extract_frames_raises_on_timeout(
        self, monkeypatch, tmp_path,
    ):
        monkeypatch.setattr(ffmpeg_mod, "FFMPEG_BIN", "/fake/ffmpeg")
        with mock.patch.object(
            subprocess, "run",
            side_effect=subprocess.TimeoutExpired(
                cmd="ffmpeg", timeout=120,
            ),
        ):
            with pytest.raises(FFmpegFailed) as exc:
                extract_frames(
                    Path("/x.mp4"),
                    tmp_path / "frames",
                )
        assert "timeout" in str(exc.value).lower()

    def test_extract_audio_raises_on_nonzero_exit(
        self, monkeypatch, tmp_path,
    ):
        monkeypatch.setattr(ffmpeg_mod, "FFMPEG_BIN", "/fake/ffmpeg")
        fake = mock.MagicMock(returncode=2, stderr="audio failure")
        with mock.patch.object(
            subprocess, "run", return_value=fake,
        ):
            with pytest.raises(FFmpegFailed) as exc:
                extract_audio(
                    Path("/x.mp4"),
                    tmp_path / "out.mp3",
                )
        assert exc.value.stderr == "audio failure"

    def test_validate_video_raises_on_invalid_data_marker(
        self, monkeypatch,
    ):
        monkeypatch.setattr(ffmpeg_mod, "FFMPEG_BIN", "/fake/ffmpeg")
        fake = mock.MagicMock(
            returncode=1,
            stderr="x.mp4: Invalid data found when processing input",
        )
        with mock.patch.object(
            subprocess, "run", return_value=fake,
        ):
            with pytest.raises(FFmpegFailed):
                validate_video(Path("/x.mp4"))


# ---------------------------------------------------------------------------
# 4. _parse_probe_stderr helper (no skip — pure function)
# ---------------------------------------------------------------------------


class TestParseProbeStderr:

    SAMPLE_STDERR = """
ffmpeg version 4.4.2 ...
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'sample.mp4':
  Duration: 00:00:03.00, start: 0.000000, bitrate: 100 kb/s
    Stream #0:0(und): Video: h264 (Constrained Baseline), yuv420p, 320x240, 30 fps, 30 tbr, 30k tbn
"""

    def test_parses_duration(self):
        result = ffmpeg_mod._parse_probe_stderr(self.SAMPLE_STDERR)
        assert result["duration_seconds"] == pytest.approx(3.0, abs=0.01)

    def test_parses_resolution(self):
        result = ffmpeg_mod._parse_probe_stderr(self.SAMPLE_STDERR)
        assert result["width"] == 320
        assert result["height"] == 240

    def test_parses_codec(self):
        result = ffmpeg_mod._parse_probe_stderr(self.SAMPLE_STDERR)
        assert result["codec"] == "h264"

    def test_parses_fps(self):
        result = ffmpeg_mod._parse_probe_stderr(self.SAMPLE_STDERR)
        assert result["fps"] == 30.0

    def test_empty_stderr_returns_zero_defaults(self):
        result = ffmpeg_mod._parse_probe_stderr("")
        assert result["width"] == 0
        assert result["height"] == 0
        assert result["duration_seconds"] == 0.0
        assert result["codec"] == ""
        assert result["fps"] == 0.0


# ---------------------------------------------------------------------------
# 5. Real ffmpeg integration (skip when ffmpeg or fixture absent)
# ---------------------------------------------------------------------------


@real_ffmpeg
class TestRealFFmpeg:

    def test_extract_frames_real_video_returns_sorted_paths(
        self, tmp_path,
    ):
        out = tmp_path / "frames"
        result = extract_frames(FIXTURE_VIDEO, out)
        assert len(result) > 0
        # Sorted by name (frame_001 < frame_002 < ...)
        names = [p.name for p in result]
        assert names == sorted(names)
        # All under output_dir.
        for p in result:
            assert p.parent == out
            assert p.name.startswith("frame_")
            assert p.suffix == ".jpg"

    def test_extract_frames_respects_max_cap(self, tmp_path):
        out = tmp_path / "frames_cap"
        result = extract_frames(FIXTURE_VIDEO, out, max_frames=3)
        assert len(result) <= 3

    def test_extract_audio_creates_mp3(self, tmp_path):
        out = tmp_path / "audio.mp3"
        result = extract_audio(FIXTURE_VIDEO, out)
        assert result.exists()
        assert result.stat().st_size > 0
        # Synthetic testsrc has no audio track on some ffmpeg builds;
        # if the file is created at all the wrapper succeeded.

    def test_validate_video_returns_metadata(self):
        result = validate_video(FIXTURE_VIDEO)
        assert result["width"] > 0
        assert result["height"] > 0
        assert result["duration_seconds"] > 0

    def test_validate_video_raises_on_truncated(self, tmp_path):
        truncated = tmp_path / "trunc.mp4"
        truncated.write_bytes(b"\x00" * 100)  # 100 random-ish bytes
        with pytest.raises(FFmpegFailed):
            validate_video(truncated)
