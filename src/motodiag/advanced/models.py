"""Phase 148 — FailurePrediction Pydantic models.

The canonical output of :func:`motodiag.advanced.predictor.predict_failures`.
Frozen so a prediction flowing through the Rich table renderer + ``--json``
serializer + test assertions can't accidentally be mutated mid-pipeline.

Design notes
------------

- ``typical_onset_miles`` / ``typical_onset_years`` are the heuristic per-
  severity onset bands used in Phase 148. Phase 149 will swap these for
  real per-issue values from migration 018 columns — the model already
  has the right shape, so the Phase 149 change is data-only.

- ``miles_to_onset`` is signed: negative means the bike is past the
  typical onset window (the prediction is "overdue", not "upcoming").
  The Rich renderer colors negative values red so a mechanic instantly
  sees "this one's already late".

- ``verified_by`` distinguishes forum-consensus fixes from service-manual
  procedures. Per the user-memory rule "every Track B phase must include
  forum-sourced fixes", the renderer surfaces a footer count; Phase 149
  adds an ``--only-verified`` filter flag.

- ``match_tier`` is the provenance label for the mechanic's trust
  decision. ``exact_model`` is the strongest signal (issue matches this
  exact bike model); ``generic`` is the weakest (issue is a make-wide
  reference with no year match). The field is exposed via ``--json``
  only in Phase 148 — the Rich table is already seven columns wide.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class PredictionConfidence(str, Enum):
    """Confidence bucket derived from the scoring pipeline.

    The numeric ``confidence_score`` is the source of truth; this enum
    is a three-band coarsening for renderer color-coding:

    - ``HIGH`` — score ≥ 0.75. Exact-model or narrow-year match with
      mileage and/or age corroboration.
    - ``MEDIUM`` — 0.5 ≤ score < 0.75. Family/make match or broad year
      range; typically missing one of the mileage/age signals.
    - ``LOW`` — score < 0.5. Make-only or generic fallback — still worth
      showing, but the mechanic should weigh the evidence themselves.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FailurePrediction(BaseModel):
    """A single predicted failure emitted by :func:`predict_failures`.

    Instances are ``frozen=True`` so downstream consumers (Rich renderer,
    JSON serializer, test assertions) can pass the model around without
    worrying about in-flight mutation.
    """

    model_config = ConfigDict(frozen=True)

    issue_id: int
    issue_title: str
    severity: str
    make: Optional[str]
    model: Optional[str]
    year_range: Tuple[Optional[int], Optional[int]]
    typical_onset_miles: Optional[int]
    typical_onset_years: Optional[int]
    # Signed — negative means the bike is past the typical onset window.
    miles_to_onset: Optional[int]
    years_to_onset: Optional[float]
    confidence: PredictionConfidence
    confidence_score: float = Field(ge=0.0, le=1.0)
    preventive_action: str
    parts_cost_cents: Optional[int]
    # Provenance signal: "forum" (mechanic consensus), "service_manual"
    # (OEM procedure / TSB), or None when neither marker was found.
    verified_by: Optional[str]
    # Match strength label: "exact_model" | "family" | "make" | "generic".
    match_tier: str
