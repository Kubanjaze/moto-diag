"""Phase 148 — mileage/age-based failure prediction.

``predict_failures(vehicle, horizon_days, min_severity, db_path)`` is the
single public entry point. It cross-references the ``known_issues``
table against a vehicle's current mileage + age (derived from
``year``), ranks candidates by a heuristic confidence pipeline, and
returns up to 50 :class:`FailurePrediction` rows sorted by urgency.

The scoring pipeline is deterministic, documented, and side-effect
free — every score contribution is a constant documented below, so a
mechanic who disagrees with a prediction can reason about why it
surfaced. No AI calls, no network I/O, no migrations.

Severity-to-onset heuristic
---------------------------

Phase 148 ships without migration 018 (the column set that will hold
real per-issue onset data), so we derive a rough "typical onset"
miles-and-age band from the issue's ``severity``:

=============  =================  ===============
severity       typical_onset_mi   typical_onset_y
=============  =================  ===============
critical       15 000             3
high           30 000             5
medium         50 000             8
low            80 000             12
=============  =================  ===============

Calibrated against TC88 cam chain tensioner failures (high, ~30k mi),
Harley stator failures (high, ~3-5 yr), KLR doohickey (critical, 15-30k
mi), and Honda CCT (high, ~20-40k mi). These are the four "canonical"
forum-consensus failure rows whose onset bands we know; everything else
inherits by severity band.

Match-tier scoring
------------------

=============  ==============  ========================================
match_tier     base score      criteria
=============  ==============  ========================================
exact_model    1.00            issue.model == vehicle.model (CI)
family         0.75            issue.model is None + make match + year
                               in [year_start, year_end]
make           0.50            issue.model is None + make match + year
                               out of [year_start, year_end]
generic        0.30            otherwise
=============  ==============  ========================================

Plus:

- **Year-range tightness bonus** — narrow year ranges indicate a
  better-targeted issue. ``+ min(0.2, (30 - width) / 150)`` clamped
  at 0. A one-year issue gets +0.193, a 10-year range gets +0.133,
  a 30+-year range gets 0.
- **Mileage bonus** — if ``current >= onset * 0.8`` add +0.1; if
  ``current >= onset`` add another +0.1 (cumulative +0.2 at the
  full onset band). Missing mileage contributes nothing.
- **Age bonus** — same ±0.1/0.2 on ``age_years`` vs ``onset_years``.

Final ``confidence_score`` is clamped to ``[0.0, 1.0]``. Bucketing to
:class:`PredictionConfidence` uses 0.75 / 0.5 thresholds.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from motodiag.advanced.models import FailurePrediction, PredictionConfidence
from motodiag.knowledge.issues_repo import search_known_issues


# --- Tunable constants ---

# Severity-weight for sort tiebreaking. Critical floats to the top.
SEVERITY_WEIGHT: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

# Heuristic onset bands derived from severity. Phase 149 replaces these
# with real per-issue values from migration 018 columns.
_ONSET_MILES_BY_SEVERITY: dict[str, int] = {
    "critical": 15_000,
    "high": 30_000,
    "medium": 50_000,
    "low": 80_000,
}

_ONSET_YEARS_BY_SEVERITY: dict[str, int] = {
    "critical": 3,
    "high": 5,
    "medium": 8,
    "low": 12,
}

# Match-tier base scores.
_MATCH_TIER_SCORE: dict[str, float] = {
    "exact_model": 1.00,
    "family": 0.75,
    "make": 0.50,
    "generic": 0.30,
}

# Confidence bucket thresholds (applied to the clamped numeric score).
_CONF_HIGH_THRESHOLD: float = 0.75
_CONF_MEDIUM_THRESHOLD: float = 0.50

# Bonuses added when the current mileage/age crosses each threshold.
_EARLY_BAND_BONUS: float = 0.10   # current >= onset * 0.8
_ONSET_BAND_BONUS: float = 0.10   # additional when current >= onset

# Year-range tightness bonus scaling.
_YEAR_RANGE_BONUS_CAP: float = 0.20
_YEAR_RANGE_BONUS_BASELINE: int = 30
_YEAR_RANGE_BONUS_DIVISOR: float = 150.0

# Max predictions returned per call.
_MAX_PREDICTIONS: int = 50

# Preventive-action extraction heuristic.
_FORUM_TIP_MARKER = "Forum tip:"
_NUMBERED_STEP_RE = re.compile(r"(?:^|\s)1\.\s+", re.MULTILINE)
_PREVENTIVE_TRUNCATE = 200

# Verified-by substring markers (case-insensitive).
_FORUM_MARKERS: tuple[str, ...] = (
    "forum consensus",
    "forum tip",
    "reddit",
    "forum-level",
)
_SERVICE_MANUAL_MARKERS: tuple[str, ...] = (
    "service manual",
    "oem procedure",
    "tsb",
)


# --- Public entry point ---


def predict_failures(
    vehicle: dict,
    horizon_days: Optional[int] = 180,
    min_severity: Optional[str] = None,
    db_path: Optional[str] = None,
) -> list[FailurePrediction]:
    """Predict upcoming failures for a vehicle.

    Parameters
    ----------
    vehicle : dict
        Must contain ``make`` (str), ``model`` (str), and ``year`` (int).
        ``mileage`` (int) is optional — when absent, scoring falls back
        to age-only.
    horizon_days : int, optional
        Drop predictions whose ``years_to_onset > horizon_days / 365``.
        Pass ``None`` to disable the horizon filter. Defaults to 180 days
        (~6 months — one standard service interval).
    min_severity : str, optional
        Drop predictions below this severity. One of ``"low"``,
        ``"medium"``, ``"high"``, ``"critical"``. ``None`` disables.
    db_path : str, optional
        Override the default database path (used by tests).

    Returns
    -------
    list[FailurePrediction]
        Up to ``_MAX_PREDICTIONS`` (50) rows sorted by severity weight,
        then urgency (miles-to-onset, negative first), then confidence
        score, with ``issue_id`` as final tiebreaker for determinism.
    """
    make = vehicle.get("make")
    model_name = vehicle.get("model")
    year = vehicle.get("year")
    current_mileage = vehicle.get("mileage")

    if not make or not model_name or year is None:
        return []

    # --- Candidate retrieval ---
    # Two-pass pattern: first the model-specific query, then a model=None
    # pass for make-wide issues. Dedupe by issue id.
    candidates: dict[int, dict] = {}
    for issue in search_known_issues(
        make=make, model=model_name, year=year, db_path=db_path,
    ):
        candidates[issue["id"]] = issue
    for issue in search_known_issues(
        make=make, model=None, year=year, db_path=db_path,
    ):
        # Don't overwrite a model-specific hit with a make-only hit —
        # the first pass is more precise.
        candidates.setdefault(issue["id"], issue)
    # Third pass for out-of-year-range make hits (match_tier="make").
    # search_known_issues's year filter drops these, so we widen by
    # dropping the year param.
    for issue in search_known_issues(
        make=make, model=None, db_path=db_path,
    ):
        candidates.setdefault(issue["id"], issue)
    # Fourth pass for totally-generic issues (make IS NULL + model IS
    # NULL). Those rows can't be picked up by a make-filtered query —
    # SQL ``make LIKE '%foo%'`` never matches NULL. Fetching all rows
    # and filtering in Python keeps the query count bounded (4) while
    # still surfacing generic reference rows against unknown makes.
    for issue in search_known_issues(db_path=db_path):
        if issue.get("make") is None and issue.get("model") is None:
            candidates.setdefault(issue["id"], issue)

    if not candidates:
        return []

    now_year = datetime.now().year
    age_years = now_year - int(year)

    predictions: list[FailurePrediction] = []
    for issue in candidates.values():
        pred = _build_prediction(
            issue=issue,
            vehicle_make=make,
            vehicle_model=model_name,
            vehicle_year=int(year),
            age_years=age_years,
            current_mileage=current_mileage,
        )
        if pred is None:
            continue
        predictions.append(pred)

    # --- Horizon filter ---
    if horizon_days is not None and horizon_days >= 0:
        horizon_years = horizon_days / 365.0
        predictions = [
            p for p in predictions
            if p.years_to_onset is None or p.years_to_onset <= horizon_years
        ]

    # --- Severity filter ---
    if min_severity:
        min_weight = SEVERITY_WEIGHT.get(min_severity.lower().strip(), 0)
        predictions = [
            p for p in predictions
            if SEVERITY_WEIGHT.get((p.severity or "").lower(), 0) >= min_weight
        ]

    # --- Sort: severity weight DESC, then miles_to_onset ASC (negative
    # = overdue floats first), then confidence DESC, then issue_id ASC
    # for deterministic ordering in tests.
    def _sort_key(p: FailurePrediction) -> tuple:
        sev_w = -SEVERITY_WEIGHT.get((p.severity or "").lower(), 0)
        # Missing miles_to_onset sinks to the bottom of its severity
        # band — we can't judge urgency without data.
        miles_sort = p.miles_to_onset if p.miles_to_onset is not None else 10**9
        conf_sort = -p.confidence_score
        return (sev_w, miles_sort, conf_sort, p.issue_id)

    predictions.sort(key=_sort_key)
    return predictions[:_MAX_PREDICTIONS]


# --- Per-issue builder ---


def _build_prediction(
    issue: dict,
    vehicle_make: str,
    vehicle_model: str,
    vehicle_year: int,
    age_years: int,
    current_mileage: Optional[int],
) -> Optional[FailurePrediction]:
    """Convert one known_issues row into a FailurePrediction.

    Returns ``None`` for unusable rows (missing severity/title). The
    match-tier ladder is evaluated first; scoring then layers
    year-range tightness, mileage, and age bonuses.
    """
    title = (issue.get("title") or "").strip()
    if not title:
        return None

    raw_severity = (issue.get("severity") or "medium").strip().lower()
    severity = raw_severity if raw_severity in SEVERITY_WEIGHT else "medium"

    issue_make = (issue.get("make") or "").strip().lower()
    issue_model = (issue.get("model") or "") or None
    year_start = issue.get("year_start")
    year_end = issue.get("year_end")
    vehicle_make_lc = (vehicle_make or "").strip().lower()
    vehicle_model_lc = (vehicle_model or "").strip().lower()

    # --- Match tier ---
    match_tier = "generic"
    if issue_model and issue_model.strip().lower() == vehicle_model_lc:
        match_tier = "exact_model"
    elif issue_model is None and issue_make == vehicle_make_lc:
        # family vs make depends on year membership.
        if _year_in_range(vehicle_year, year_start, year_end):
            match_tier = "family"
        else:
            match_tier = "make"
    # else: generic.

    score = _MATCH_TIER_SCORE.get(match_tier, 0.3)

    # --- Year-range tightness bonus ---
    if year_start is not None and year_end is not None:
        width = max(0, int(year_end) - int(year_start))
        raw = (_YEAR_RANGE_BONUS_BASELINE - width) / _YEAR_RANGE_BONUS_DIVISOR
        score += max(0.0, min(_YEAR_RANGE_BONUS_CAP, raw))

    # --- Onset bands (from severity heuristic) ---
    onset_miles = _ONSET_MILES_BY_SEVERITY.get(severity)
    onset_years = _ONSET_YEARS_BY_SEVERITY.get(severity)

    # --- Mileage bonus ---
    miles_to_onset: Optional[int] = None
    if current_mileage is not None and onset_miles is not None:
        miles_to_onset = int(onset_miles) - int(current_mileage)
        if current_mileage >= onset_miles * 0.8:
            score += _EARLY_BAND_BONUS
        if current_mileage >= onset_miles:
            score += _ONSET_BAND_BONUS

    # --- Age bonus ---
    years_to_onset: Optional[float] = None
    if onset_years is not None:
        years_to_onset = float(onset_years) - float(age_years)
        if age_years >= onset_years * 0.8:
            score += _EARLY_BAND_BONUS
        if age_years >= onset_years:
            score += _ONSET_BAND_BONUS

    # Clamp score to [0, 1].
    score = max(0.0, min(1.0, score))

    # --- Confidence enum ---
    if score >= _CONF_HIGH_THRESHOLD:
        confidence = PredictionConfidence.HIGH
    elif score >= _CONF_MEDIUM_THRESHOLD:
        confidence = PredictionConfidence.MEDIUM
    else:
        confidence = PredictionConfidence.LOW

    # --- Extracted fields ---
    preventive_action = _extract_preventive_action(issue)
    verified_by = _classify_verified_by(issue)

    return FailurePrediction(
        issue_id=int(issue["id"]),
        issue_title=title,
        severity=severity,
        make=issue.get("make"),
        model=issue.get("model"),
        year_range=(year_start, year_end),
        typical_onset_miles=onset_miles,
        typical_onset_years=onset_years,
        miles_to_onset=miles_to_onset,
        years_to_onset=years_to_onset,
        confidence=confidence,
        confidence_score=round(score, 4),
        preventive_action=preventive_action,
        parts_cost_cents=None,   # Phase 149 populates from migration 018.
        verified_by=verified_by,
        match_tier=match_tier,
    )


# --- Helpers ---


def _year_in_range(
    year: int, year_start: Optional[int], year_end: Optional[int],
) -> bool:
    """Return True when ``year`` falls inside ``[year_start, year_end]``.

    Both endpoints default to open when ``None`` — e.g. ``year_start=None``
    means "all years up to year_end". Used to disambiguate
    ``match_tier="family"`` (issue's make+year-range covers the bike)
    from ``match_tier="make"`` (issue's make matches but year is out of
    range — weaker match).
    """
    if year_start is not None and year < int(year_start):
        return False
    if year_end is not None and year > int(year_end):
        return False
    return True


def _extract_preventive_action(issue: dict) -> str:
    """Derive the actionable 'preventive action' string from an issue row.

    Heuristic order:

    1. If ``fix_procedure`` contains ``"Forum tip:"``, use the substring
       that follows (trimmed, collapsed whitespace).
    2. Otherwise, if ``fix_procedure`` starts with a numbered step
       (``"1. "``), use the step-1 content as the actionable summary.
    3. Otherwise, fall back to the first 200 chars of ``description``.
    """
    fix = issue.get("fix_procedure") or ""
    desc = issue.get("description") or ""

    # 1. Forum tip marker
    if _FORUM_TIP_MARKER in fix:
        tail = fix.split(_FORUM_TIP_MARKER, 1)[1]
        return _tidy(tail, _PREVENTIVE_TRUNCATE)

    # 2. Numbered step. Use preamble if present, else first step.
    if fix:
        match = _NUMBERED_STEP_RE.search(fix)
        if match:
            preamble = fix[: match.start()].strip()
            if preamble:
                return _tidy(preamble, _PREVENTIVE_TRUNCATE)
            # No preamble — take the step-1 body up to step 2 if any.
            rest = fix[match.end():]
            step2 = re.search(r"(?:^|\s)2\.\s+", rest, re.MULTILINE)
            step_one = rest[: step2.start()] if step2 else rest
            return _tidy(step_one, _PREVENTIVE_TRUNCATE)
        # No numbered steps — use the whole fix_procedure text.
        return _tidy(fix, _PREVENTIVE_TRUNCATE)

    # 3. Description fallback
    return _tidy(desc, _PREVENTIVE_TRUNCATE)


def _tidy(text: str, max_len: int) -> str:
    """Strip whitespace, collapse runs of spaces, truncate to ``max_len``."""
    if not text:
        return ""
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) > max_len:
        # Trim at the max_len boundary; callers decide whether to ellipsize.
        collapsed = collapsed[:max_len].rstrip()
    return collapsed


def _classify_verified_by(issue: dict) -> Optional[str]:
    """Classify the provenance of an issue row.

    Scans ``description + fix_procedure`` (lowercased) for canonical
    markers. Forum markers win over service-manual markers when both
    are present — the user-memory rule prioritizes forum-sourced
    knowledge.
    """
    haystack = (
        (issue.get("description") or "") + " " +
        (issue.get("fix_procedure") or "")
    ).lower()
    if not haystack.strip():
        return None
    for marker in _FORUM_MARKERS:
        if marker in haystack:
            return "forum"
    for marker in _SERVICE_MANUAL_MARKERS:
        if marker in haystack:
            return "service_manual"
    return None
