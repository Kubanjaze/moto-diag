"""MotoDiag HTTP API (Track H, Phase 175+).

Exposes the Track G shop management console + Track A-F diagnostic
substrate over HTTP. See :func:`create_app` for the factory that
returns a configured FastAPI instance; :mod:`motodiag.api.app` for
the full builder + middleware + handler wiring.
"""

from __future__ import annotations

from motodiag.api.app import APP_VERSION, create_app


__all__ = ["APP_VERSION", "create_app"]
