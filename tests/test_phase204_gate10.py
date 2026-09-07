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

from pydantic import BaseModel

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


class _PresetBody(BaseModel):
    """Module-level on purpose.

    Defined inside the test function, FastAPI cannot resolve the
    annotation via get_type_hints and falls back to treating the
    parameter as a QUERY field — the error then reads
    ``loc: ('query', 'body')`` and never names ``preset``, which makes
    the test look like a code failure when it is a fixture bug.
    """

    preset: str


class TestValidationFailuresAreLogged:
    """The 422 logging must not change the RESPONSE shape.

    Phase 204 added a RequestValidationError handler so malformed
    requests stop being invisible server-side. The first version also
    replaced the body with an RFC 7807 envelope carrying a stringified
    detail — which broke Phase 192B's contract test, because clients
    parse `detail` as the structured list of field errors. The handler
    now logs and delegates to FastAPI's own handler; this pins both
    halves so a future edit cannot quietly trade one for the other.
    """

    def test_logs_the_field_errors(self, caplog):
        import logging

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from motodiag.api.errors import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)

        @app.post("/echo")
        def echo(body: _PresetBody) -> dict:  # pragma: no cover
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        with caplog.at_level(logging.WARNING, logger="motodiag.api.errors"):
            response = client.post("/echo", json={})

        assert response.status_code == 422
        assert any(
            "422 validation failure" in r.message for r in caplog.records
        ), "a rejected request must leave a trace server-side"

        # ...and the body is still FastAPI's structured shape, so the
        # field that failed stays machine-readable by the caller.
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any("preset" in str(err.get("loc", [])) for err in detail)
