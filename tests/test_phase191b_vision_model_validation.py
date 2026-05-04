"""Phase 191B fix-cycle-4 — Vision model-string validation regression guard.

Architect-gate halted at re-smoke step 7 with:

  Vision pipeline error for video 3: Vision SDK call failed:
  Error code: 404 - {'type': 'error', 'error': {'type': 'not_found_error',
  'message': 'model: claude-sonnet-4-5-20241022'}, ...}

The "sonnet" alias in engine/client.py:MODEL_ALIASES resolved to
"claude-sonnet-4-5-20241022" — a fabricated/unreleased model ID
(Anthropic's Sonnet 4 family went 4.0 -> 4.6 with no 4.5 release).
Bug latent since the engine module was first written; surfaced by
Phase 191B's Commit 2 because that's the first phase to do REAL
Anthropic API calls instead of mocked-only test paths.

SIXTH instance of the F9 "snapshot/assumption doesn't match runtime"
failure family on Track I:
  Phase 188:        HVE shape mock vs real backend
  Phase 190:        substring-match-on-error-text
  Phase 191:        closure-state capture (registration time)
  Phase 191B:       serve.py never called init_db (deploy path)
  Phase 191B C1:    timestamp-format mismatch (date-boundary latent)
  Phase 191B C6:    file:// prefix missing on FormData (mock-vs-fetch)
  Phase 191B C2:    model-string fabricated (this one)

This test file is F15: a regression guard at pytest-time that catches
model-ID drift BEFORE a 404 from the live API. The check is structural
(known-good ID set + alias-resolution sanity) — it doesn't make a real
API call. F15-strict (real-API contract test) is filed for a future
phase but isn't worth the per-run cost here.

When Anthropic ships a new generation:
  1. Update engine/client.py:MODEL_ALIASES to point at the new ID
  2. Update engine/client.py:MODEL_PRICING with the new rates
  3. Update KNOWN_GOOD_MODEL_IDS in this file to include the new ID
  4. (Optionally) keep the old ID in KNOWN_GOOD if rolling deployment
     needs to support both for a window
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from motodiag.engine.client import (
    MODEL_ALIASES,
    MODEL_PRICING,
    _resolve_model,
)


# Source of truth for currently-valid Anthropic model IDs the project may
# resolve to. Per CLAUDE.md system context (May 2026):
#   Most recent Claude model family is Claude 4.X. Model IDs:
#     Opus 4.7:   claude-opus-4-7
#     Sonnet 4.6: claude-sonnet-4-6
#     Haiku 4.5:  claude-haiku-4-5-20251001
#
# Update this set when:
#   - Anthropic releases a new generation
#   - The project's MODEL_ALIASES bumps to a new ID
#   - We deliberately add support for a previously-released model (e.g.,
#     for backwards compat during a rolling deploy)
KNOWN_GOOD_MODEL_IDS = {
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
}


# ---------------------------------------------------------------------
# 1. MODEL_ALIASES integrity
# ---------------------------------------------------------------------


class TestModelAliasesResolveToValidIDs:
    """Every alias in MODEL_ALIASES must resolve to a known-good model ID.
    Catches the exact failure mode that broke architect-gate step 7:
    `MODEL_ALIASES['sonnet'] = 'claude-sonnet-4-5-20241022'` (fabricated)."""

    @pytest.mark.parametrize("alias", sorted(MODEL_ALIASES.keys()))
    def test_alias_resolves_to_known_good_id(self, alias):
        resolved = _resolve_model(alias)
        assert resolved in KNOWN_GOOD_MODEL_IDS, (
            f"Alias '{alias}' resolves to '{resolved}' which is NOT in "
            f"KNOWN_GOOD_MODEL_IDS. Either Anthropic released a new model "
            f"and KNOWN_GOOD_MODEL_IDS needs updating, or the alias was "
            f"changed to a fabricated/unreleased ID. Live API would 404."
        )

    def test_sonnet_alias_specifically(self):
        """The exact bug architect-gate step 7 caught: sonnet -> bogus ID.
        Pinned with a dedicated test so the failure mode is unmistakable
        in pytest output."""
        assert _resolve_model("sonnet") == "claude-sonnet-4-6", (
            "The 'sonnet' alias must resolve to claude-sonnet-4-6 per "
            "plan v1.0 B5 + CLAUDE.md system context. If this fails, "
            "MODEL_ALIASES['sonnet'] was changed; verify the new ID "
            "exists in Anthropic's API before merging."
        )

    def test_haiku_alias_specifically(self):
        assert _resolve_model("haiku") == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------
# 2. MODEL_PRICING integrity
# ---------------------------------------------------------------------


class TestModelPricingMatchesAliases:
    """Every model ID that an alias resolves to must have a pricing entry.
    Without this, _calculate_cost falls back to the placeholder
    {'input': 1.0, 'output': 5.0} default and reports wrong cost.
    cost_estimate_usd populated on VisualAnalysisResult would be silently
    incorrect."""

    @pytest.mark.parametrize("alias", sorted(MODEL_ALIASES.keys()))
    def test_resolved_model_has_pricing_entry(self, alias):
        resolved = _resolve_model(alias)
        assert resolved in MODEL_PRICING, (
            f"Alias '{alias}' resolves to '{resolved}' but that ID is "
            f"NOT in MODEL_PRICING. Cost calculation will silently fall "
            f"back to placeholder rates. Add a pricing entry when "
            f"bumping aliases."
        )

    def test_pricing_entries_have_input_and_output_keys(self):
        for model_id, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"{model_id} missing 'input' key"
            assert "output" in pricing, f"{model_id} missing 'output' key"
            assert isinstance(pricing["input"], (int, float))
            assert isinstance(pricing["output"], (int, float))
            assert pricing["input"] > 0
            assert pricing["output"] > 0


# ---------------------------------------------------------------------
# 3. MOTODIAG_VISION_MODEL env var override (Phase 191B fix-cycle-4 ask)
# ---------------------------------------------------------------------


class TestVisionModelEnvVarOverride:
    """The MOTODIAG_VISION_MODEL env var lets ops swap models without a
    code change. Read at module load time. Test reload on change."""

    def test_default_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("MOTODIAG_VISION_MODEL", raising=False)
        # Re-import to pick up env state
        import importlib
        from motodiag.media import vision_analysis_pipeline as mod
        importlib.reload(mod)
        assert mod.DEFAULT_VISION_MODEL == "sonnet"

    def test_env_alias_override(self, monkeypatch):
        monkeypatch.setenv("MOTODIAG_VISION_MODEL", "haiku")
        import importlib
        from motodiag.media import vision_analysis_pipeline as mod
        importlib.reload(mod)
        assert mod.DEFAULT_VISION_MODEL == "haiku"

    def test_env_full_id_override(self, monkeypatch):
        """Env var accepts a full model ID too — for cases where ops want
        to pin an exact ID instead of going through alias resolution."""
        monkeypatch.setenv("MOTODIAG_VISION_MODEL", "claude-sonnet-4-6")
        import importlib
        from motodiag.media import vision_analysis_pipeline as mod
        importlib.reload(mod)
        assert mod.DEFAULT_VISION_MODEL == "claude-sonnet-4-6"

    def test_default_falls_back_to_sonnet_after_env_clear(self, monkeypatch):
        """Sanity: env-var leakage between tests shouldn't bleed into the
        default. monkeypatch's auto-undo + reload reset the module state."""
        # Set then clear
        monkeypatch.setenv("MOTODIAG_VISION_MODEL", "haiku")
        import importlib
        from motodiag.media import vision_analysis_pipeline as mod
        importlib.reload(mod)
        assert mod.DEFAULT_VISION_MODEL == "haiku"
        # Clear + reload
        monkeypatch.delenv("MOTODIAG_VISION_MODEL", raising=False)
        importlib.reload(mod)
        assert mod.DEFAULT_VISION_MODEL == "sonnet"


# ---------------------------------------------------------------------
# 4. Anti-regression: the exact bug architect-gate step 7 caught
# ---------------------------------------------------------------------


class TestNoFabricatedModelIDs:
    """Pin against the specific bogus IDs that have surfaced in this
    codebase. Add to this list if a new fabricated ID slips in and gets
    caught by future architect-gate runs."""

    KNOWN_BOGUS_IDS = {
        # Architect-gate step 7 (2026-05-04): fabricated Sonnet 4.5
        "claude-sonnet-4-5-20241022",
    }

    @pytest.mark.parametrize("alias", sorted(MODEL_ALIASES.keys()))
    def test_alias_does_not_resolve_to_known_bogus(self, alias):
        resolved = _resolve_model(alias)
        assert resolved not in self.KNOWN_BOGUS_IDS, (
            f"Alias '{alias}' resolves to '{resolved}' which is a known-"
            f"BOGUS model ID (would 404 against live Anthropic API). "
            f"This is the exact bug architect-gate step 7 caught on "
            f"2026-05-04."
        )

    def test_pricing_does_not_reference_known_bogus(self):
        for model_id in MODEL_PRICING:
            assert model_id not in self.KNOWN_BOGUS_IDS, (
                f"MODEL_PRICING contains a known-bogus model ID: "
                f"{model_id}. Cost calc would route through it."
            )
