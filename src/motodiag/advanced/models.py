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

from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional, Tuple

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
    # Phase 154: OEM TSB numbers that apply to this bike. Empty when the
    # TSB subsystem is unavailable (pre-migration-022) or no matching
    # TSBs pass the keyword-overlap filter. Additive — existing
    # consumers ignore it. Sorted for deterministic output.
    applicable_tsbs: list[str] = Field(default_factory=list)
    # Phase 155: NHTSA campaign IDs that apply to this bike. Empty when
    # the recall subsystem is unavailable (pre-migration-023) or no
    # open recalls match. Additive — existing consumers ignore it.
    applicable_recalls: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 151 — Service-interval scheduling
# ---------------------------------------------------------------------------


class ServiceInterval(BaseModel):
    """A single per-bike maintenance-interval row from ``service_intervals``.

    Dual-axis: ``every_miles`` OR ``every_months`` may be set; the DB
    CHECK constraint ensures at least one is non-NULL. ``last_done_*``
    captures the most recent completion; ``next_due_*`` caches the
    computed next due-point so queries can ORDER BY directly without
    re-deriving on every read.

    Non-frozen (unlike the other advanced models) because the repo
    layer mutates these rows in-place on ``record_completion``. Consumers
    that need immutability can call ``.model_copy(deep=True)``.
    """

    model_config = ConfigDict()

    # id is optional so callers can construct an instance pre-INSERT.
    id: Optional[int] = None
    vehicle_id: int
    item_slug: str
    description: str
    every_miles: Optional[int] = None
    every_months: Optional[int] = None
    last_done_miles: Optional[int] = None
    last_done_at: Optional[str] = None
    next_due_miles: Optional[int] = None
    next_due_at: Optional[str] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 152 — Service history tracking
# ---------------------------------------------------------------------------


# The event_type vocabulary. Mirrors the CHECK constraint on
# service_history.event_type verbatim so the Pydantic validator and the
# DB reject the same set of strings. Growth requires a paired migration
# + Literal update (documented in implementation.md risks).
ServiceEventType = Literal[
    "oil-change",
    "tire",
    "valve-adjust",
    "brake",
    "diagnostic",
    "recall",
    "chain",
    "coolant",
    "air-filter",
    "spark-plug",
    "custom",
]


class ServiceEvent(BaseModel):
    """A single completed service event from ``service_history``.

    Non-frozen: the repo layer bumps ``id`` post-INSERT on a returned
    instance is not the pattern here (we just return the lastrowid),
    but leaving off ``frozen=True`` keeps the model consistent with
    Phase 151's ``ServiceInterval``.

    Notes
    -----
    - ``event_type`` is a ``Literal[...]`` of the 11 DB-enforced values;
      Pydantic rejects anything outside the set with a ValidationError.
    - ``at_date`` is a Python ``date`` (not a string). The repo layer
      serializes to ISO-8601 at INSERT time.
    - ``at_miles`` is optional — a diagnostic event may have no reading.
      When present, the repo layer monotonically bumps
      ``vehicles.mileage`` in the same transaction.
    - ``mechanic_user_id`` is the FK attribution; None means "no
      logged-in user" (the Phase 112 auth layer is soft-coupled).
    - ``parts_csv`` is free-form (e.g. ``"O-125,FILT-9"``); the storage
      format lets Phase 153 parts indexing parse without schema churn.
    - ``completed_at`` is populated by the DB's ``DEFAULT
      CURRENT_TIMESTAMP``. Callers don't need to set it.
    """

    model_config = ConfigDict()

    id: Optional[int] = None
    vehicle_id: int
    event_type: ServiceEventType
    at_miles: Optional[int] = None
    at_date: date
    notes: Optional[str] = None
    cost_cents: Optional[int] = None
    mechanic_user_id: Optional[int] = None
    parts_csv: Optional[str] = None
    # ISO-8601 string from the DB. Optional so callers can construct
    # pre-INSERT instances without populating it.
    completed_at: Optional[str] = None
