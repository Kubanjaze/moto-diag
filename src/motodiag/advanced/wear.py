"""Phase 149 — wear pattern analysis.

Given a vehicle + observed symptoms, rank which curated wear patterns
best match. Companion to Phase 148's mileage/age failure prediction:
Phase 148 answers "what is likely to fail based on age/miles alone",
Phase 149 answers "this bike is making these noises / showing these
signs — which worn components best explain them".

The data layer is a file-seeded JSON catalog of ~30 curated wear
patterns (`wear_patterns.json`), each with mechanic-vocabulary
symptoms, a 3-4 step inspection checklist, and a forum/service-manual
citation. Phase 155+ layers user-authored patterns on top.

Design rules (same as Phase 148):
  * Zero AI calls, zero network, zero migration, zero token budget.
  * Frozen Pydantic v2 models — downstream consumers are serializers +
    Rich renderer + test assertions, none of which should mutate.
  * Sort contract: confidence DESC → matched_count DESC → pattern_id ASC.
    Deterministic for tests; mechanic-useful ranking in the terminal.

Public API:
  * :class:`WearPattern` — one catalog entry (loaded from JSON).
  * :class:`WearMatch` — one ranked output.
  * :func:`analyze_wear` — top-level entry point.
"""

from __future__ import annotations

import fnmatch
import functools
import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class WearPattern(BaseModel):
    """A single curated wear pattern entry from ``wear_patterns.json``.

    Tuple fields (``symptoms``, ``inspection_steps``) are required for
    hashability + frozen semantics — a Pydantic v2 frozen model that
    contains a list raises on ``hash()``, which blocks caching and set
    membership in the analyzer.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    component: str
    make: Optional[str]
    model_pattern: str
    year_min: Optional[int]
    year_max: Optional[int]
    symptoms: tuple[str, ...]
    inspection_steps: tuple[str, ...]
    confidence_hint: float = Field(ge=0.0, le=1.0)
    verified_by: str


class WearMatch(BaseModel):
    """A single ranked output of :func:`analyze_wear`.

    ``bike_match_tier`` is the provenance label for the mechanic's trust
    decision (same idea as Phase 148's ``match_tier``):

    * ``exact``  — make + model-pattern + year all match.
    * ``family`` — make + model-pattern match; year out of range.
    * ``make``   — make matches only.
    * ``generic`` — pattern has ``make=None``, applies universally.
    """

    model_config = ConfigDict(frozen=True)

    pattern_id: str
    component: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    symptoms_matched: tuple[str, ...]
    symptoms_unmatched: tuple[str, ...]
    bike_match_tier: str
    inspection_steps: tuple[str, ...]
    verified_by: str


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


_DEFAULT_PATTERNS_PATH = Path(__file__).parent / "wear_patterns.json"


@functools.lru_cache(maxsize=8)
def _load_wear_patterns(path: str) -> tuple[WearPattern, ...]:
    """Load + parse + cache the wear-pattern catalog.

    Cached on path so repeat calls in the same process (CLI + tests)
    are free. Cache is keyed by string, not Path, so ``lru_cache`` can
    hash the argument. Returns a tuple for frozen semantics.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Wear pattern catalog not found at {p}")
    with p.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    patterns: list[WearPattern] = []
    for entry in raw:
        # Coerce lists -> tuples so the frozen Pydantic model accepts them.
        entry = dict(entry)
        entry["symptoms"] = tuple(entry.get("symptoms", []))
        entry["inspection_steps"] = tuple(entry.get("inspection_steps", []))
        patterns.append(WearPattern(**entry))
    return tuple(patterns)


# ---------------------------------------------------------------------------
# Tokenization + matching
# ---------------------------------------------------------------------------


def _tokenize_symptoms(raw: list[str] | str | None) -> list[str]:
    """Split + normalize user-supplied symptoms.

    Accepts a list of strings, a single CSV/semicolon-delimited string,
    or ``None``. Normalization: split on ``,`` or ``;``, lowercase,
    strip, dedupe preserving first-occurrence order (mechanics read
    left-to-right; preserving order is a quality-of-life touch for
    ``--json`` consumers).
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        pieces = [raw]
    else:
        pieces = list(raw)

    tokens: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        # Single flat split handles both delimiters.
        for chunk in piece.replace(";", ",").split(","):
            t = chunk.strip().lower()
            if t and t not in seen:
                seen.add(t)
                tokens.append(t)
    return tokens


def _bike_match_tier(
    pattern: WearPattern, vehicle: dict,
) -> Optional[tuple[str, float]]:
    """Return ``(tier, bonus)`` or ``None`` if pattern must be dropped.

    Ladder:
      * pattern.make is None           → ``("generic", 0.3)``
      * make mismatch (make set)       → ``None`` (DROP — Kawasaki never
        scores a Sportster).
      * make + model + year all match  → ``("exact", 1.0)``
      * make + model match, year miss  → ``("family", 0.7)``
      * make only                      → ``("make", 0.4)``
    """
    pat_make = (pattern.make or "").strip().lower()
    veh_make = str(vehicle.get("make") or "").strip().lower()
    veh_model = str(vehicle.get("model") or "").strip().lower()
    veh_year = vehicle.get("year")

    if not pat_make:
        return ("generic", 0.3)

    if not veh_make or pat_make != veh_make:
        return None  # DROP — explicit make mismatch.

    # fnmatch-based model pattern: SQL-style % -> shell-style *.
    glob_pattern = pattern.model_pattern.lower().replace("%", "*")
    model_match = fnmatch.fnmatchcase(veh_model, glob_pattern)

    # Year range check — endpoints None means open.
    year_in_range = True
    try:
        y = int(veh_year) if veh_year is not None else None
    except (TypeError, ValueError):
        y = None
    if y is None:
        year_in_range = False
    else:
        if pattern.year_min is not None and y < pattern.year_min:
            year_in_range = False
        if pattern.year_max is not None and y > pattern.year_max:
            year_in_range = False

    if model_match and year_in_range:
        return ("exact", 1.0)
    if model_match:
        return ("family", 0.7)
    return ("make", 0.4)


def _overlap_ratio(
    user_symptoms: list[str], pattern_symptoms: tuple[str, ...],
) -> tuple[list[str], list[str], float]:
    """Return ``(matched, unmatched, ratio)`` with substring-either-direction.

    A user token matches a pattern symptom iff one is a substring of
    the other (case-insensitive — all tokens arrive lowercased). This
    handles mechanic vocabulary drift: ``"tick of death"`` (pattern) vs.
    ``"ticking"`` (user input) still matches.
    """
    if not pattern_symptoms:
        return [], [], 0.0
    matched: list[str] = []
    unmatched: list[str] = []
    for sym in pattern_symptoms:
        sym_lc = sym.lower()
        hit = any(u in sym_lc or sym_lc in u for u in user_symptoms)
        if hit:
            matched.append(sym)
        else:
            unmatched.append(sym)
    ratio = len(matched) / len(pattern_symptoms)
    return matched, unmatched, ratio


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_wear(
    vehicle: dict,
    symptoms: list[str] | str,
    min_confidence: float = 0.5,
    db_path: str | None = None,  # reserved for Phase 155+ user patterns
    patterns_path: str | None = None,
) -> list[WearMatch]:
    """Rank curated wear patterns against a vehicle + observed symptoms.

    :param vehicle: dict with at least ``make`` / ``model`` / ``year``
        keys. May come from the ``vehicles`` table (``--bike`` mode) or
        be synthesized from direct CLI args.
    :param symptoms: comma/semicolon-delimited string OR list of
        strings. Empty / None → returns ``[]``.
    :param min_confidence: drop matches whose final score is below
        this floor. ``0.0`` keeps everything non-zero; ``1.0`` only
        returns perfect matches.
    :param db_path: reserved for Phase 155+ user-authored pattern
        overlays. Ignored in Phase 149.
    :param patterns_path: override the catalog path (tests use this to
        inject a smaller fixture without touching the shipped catalog).

    :returns: list of :class:`WearMatch`, sorted confidence DESC →
        matched_count DESC → pattern_id ASC.
    """
    user_tokens = _tokenize_symptoms(symptoms)
    if not user_tokens:
        return []

    path = patterns_path or str(_DEFAULT_PATTERNS_PATH)
    patterns = _load_wear_patterns(path)

    results: list[WearMatch] = []
    for pat in patterns:
        tier_info = _bike_match_tier(pat, vehicle)
        if tier_info is None:
            continue  # Make mismatch — Kawasaki must never score a Harley.
        tier, bonus = tier_info

        matched, unmatched, ratio = _overlap_ratio(user_tokens, pat.symptoms)
        if ratio == 0.0:
            continue  # No overlap at all — skip.

        # Weighted score: 70% symptom overlap, 30% bike-match bonus.
        raw = ratio * 0.7 + bonus * 0.3
        # Floor by ratio * confidence_hint so forum-gold patterns stay
        # competitive even on partial coverage.
        floor = ratio * pat.confidence_hint
        score = max(raw, floor)
        # Clamp into [0, 1] — required by Pydantic's Field(ge=0, le=1).
        score = min(1.0, max(0.0, score))

        if score < min_confidence:
            continue

        results.append(
            WearMatch(
                pattern_id=pat.id,
                component=pat.component,
                confidence_score=score,
                symptoms_matched=tuple(matched),
                symptoms_unmatched=tuple(unmatched),
                bike_match_tier=tier,
                inspection_steps=pat.inspection_steps,
                verified_by=pat.verified_by,
            )
        )

    # Sort: confidence DESC, then matched-count DESC, then pattern_id ASC.
    results.sort(
        key=lambda m: (
            -m.confidence_score,
            -len(m.symptoms_matched),
            m.pattern_id,
        )
    )
    return results
