"""Whether this test run is inside the fleet's fence (Phase 389).

The operator, 2026-10-25, on which runs may count as a regression of record:
"Sandbox counts (Recommended)": the tests that cannot run inside the fence
skip there with a reason naming it, and those skips are accepted only for a
run made inside it. The one definition is the closeout skill's, beside the
pin it serves (`closeout_check.in_fleet_fence`, `FENCE_EXPECTED_SKIPS`).
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / ".claude" / "skills" / "closeout"))

from closeout_check import in_fleet_fence  # noqa: E402, F401
