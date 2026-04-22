"""API v1 router registry (Phase 175+).

Each submodule exposes an ``APIRouter`` named ``router``. The
app factory in :mod:`motodiag.api.app` imports them lazily so
``from motodiag.api import create_app`` stays fast.
"""

from __future__ import annotations

__all__: list[str] = []
