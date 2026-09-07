"""Phase 204 (Gate 10) — regression guards for the two blockers the gate
surfaced before it could run at all.

Both were found by running the real thing, not by reading code:
  * ffmpeg 9 REMOVED ``-vsync``, so every upload landed in
    ``unsupported`` with a green upload and no visible error.
  * the mobile client re-sent a stale multipart boundary (mobile-side;
    guarded in the mobile suite).
"""

from __future__ import annotations

import subprocess

from motodiag.media import ffmpeg as ffmpeg_mod


class TestFfmpegArgsSurviveModernFfmpeg:
    def test_does_not_use_removed_vsync_flag(self):
        """``-vsync`` was removed outright in ffmpeg 9 — not deprecated.

        It fails with "Unrecognized option" while SPLITTING THE ARGUMENT
        LIST, i.e. before decoding starts, so the failure is total and
        silent-looking: the upload succeeds, the worker marks the video
        ``unsupported``, and nothing says why.
        """
        src = ffmpeg_mod.__file__
        with open(src, "r", encoding="utf-8") as fh:
            body = fh.read()
        # The arg list itself, not the prose explaining the history.
        assert '"-vsync"' not in body, (
            "-vsync was removed in ffmpeg 9; use -fps_mode"
        )
        assert '"-fps_mode"' in body

    def test_installed_ffmpeg_accepts_the_flag_we_pass(self):
        """Pin the contract against the ffmpeg actually on this machine.

        A pure string assertion would still pass if a future ffmpeg
        removed ``-fps_mode`` too; this asks the binary.
        """
        binary = ffmpeg_mod.FFMPEG_BIN
        proc = subprocess.run(
            [binary, "-hide_banner", "-h", "full"],
            capture_output=True, text=True, timeout=30,
        )
        combined = proc.stdout + proc.stderr
        assert "fps_mode" in combined, (
            f"{binary} does not document -fps_mode; frame extraction "
            "will fail at argument-parse time"
        )
