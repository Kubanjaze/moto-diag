"""Keyword-based symptom extraction from voice transcripts —
Phase 195 (Commit 0) Section 2 (γ) substrate.

Pure function ``extract_symptoms_from_transcript(preview_text) ->
list[ExtractedPhrase]`` runs the existing
``engine/symptoms.categorize_symptoms`` keyword-pattern matcher
against phrases parsed from the transcript text. Output rows feed
``extracted_symptom_repo.create_extracted_symptom``.

**Section 2 (γ) hybrid is the substrate-feature-pair posture, NOT
Phase 195's solo posture** (clarified at Backend Commit 0.5 architect-
side review, was bad framing in the original plan v1.0 phase-log
entry):

* **Phase 195** = keyword-only + on-device preview + audio storage.
  All keyword matches become ``extracted_symptoms`` rows with
  ``extraction_method='keyword'``, ``confidence=1.0``. No threshold
  gates row creation.
* **Phase 195B** = adds Claude-fallback as a deferred background
  task. The 0.5 keyword-coverage threshold from plan v1.0 was
  specified to control WHEN 195B's Claude-fallback fires (low keyword
  coverage → ambiguous → run Claude); it has nothing to gate in
  Phase 195 in isolation. Phase 195B's plan re-litigates the
  threshold with calibration data from real transcript fixtures.

**Mechanic confirmation flow (Phase 195 today)**: keyword-extracted
rows render in the mobile UI; the mechanic taps a chip to confirm
or edit; on text/linked_symptom_id change the row's
``extraction_method`` flips to ``'manual_edit'``. A "low confidence"
UI indicator can be computed client-side from
``extracted_symptoms.length / split_into_phrases(preview_text).length``
if/when that signal proves useful — no backend support needed in
Phase 195.

**Phase 195's contract for Mobile Commit 1**: backend creates one
``extracted_symptoms`` row per keyword match; mobile renders all of
them; Phase 195's section variant is keyword-only + manual_edit;
Phase 195B will deliver Claude rows alongside the existing keyword
rows (both visible together; ``extraction_method`` discriminates).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from motodiag.engine.symptoms import SYMPTOM_CATEGORIES, categorize_symptoms


# Sentence + clause boundary regex. Matches periods, exclamation,
# question marks, semicolons (sentence boundaries) and commas (clause
# boundaries). Tolerates whitespace + multiple punctuation marks.
_PHRASE_SPLIT_RE = re.compile(r"[.!?;,]+\s*")


@dataclass(frozen=True)
class ExtractedPhrase:
    """One symptom-candidate pulled from the transcript text.

    ``text`` is the canonical form (lowercased + stripped of
    trailing punctuation; matches what we store in
    ``extracted_symptoms.text``). ``category`` is the matched
    category from ``SYMPTOM_CATEGORIES`` keys.
    """
    text: str
    category: str
    confidence: float = 1.0  # keyword pass = 1.0 by definition


def split_into_phrases(preview_text: str) -> list[str]:
    """Split a free-text transcript into candidate phrases.

    Sentence boundaries (`.!?;`) and clause boundaries (`,`) drive
    splits. Empty + single-word phrases are dropped. Lowercased +
    trimmed for downstream matching.

    Examples:
    - "The bike won't start. I noticed a clunk in the front end."
      → ["the bike won't start", "i noticed a clunk in the front end"]
    - "Hard starting, rough idle, and brake squeal."
      → ["hard starting", "rough idle", "and brake squeal"]
    """
    if not preview_text or not preview_text.strip():
        return []
    raw_phrases = _PHRASE_SPLIT_RE.split(preview_text)
    phrases = []
    for phrase in raw_phrases:
        cleaned = phrase.strip().lower()
        if len(cleaned) < 3:
            continue
        # Drop trailing punctuation the splitter didn't catch.
        cleaned = cleaned.rstrip(".!?;, ")
        if cleaned:
            phrases.append(cleaned)
    return phrases


def extract_symptoms_from_transcript(
    preview_text: Optional[str],
) -> list[ExtractedPhrase]:
    """Run keyword extraction over a transcript's preview text.

    Returns one ``ExtractedPhrase`` per (category, matched_phrase)
    pair. Returns empty list if ``preview_text`` is None / empty /
    none of the phrases match a known category pattern.

    The matching delegates to ``engine/symptoms.categorize_symptoms``
    which does substring-bidirectional matching against
    ``SYMPTOM_CATEGORIES`` patterns. The 'other' category from the
    matcher is dropped — it represents unmatched phrases, which
    don't surface as extracted symptoms.
    """
    if preview_text is None:
        return []
    phrases = split_into_phrases(preview_text)
    if not phrases:
        return []

    categorized = categorize_symptoms(phrases)
    out: list[ExtractedPhrase] = []
    for category, matched_phrases in categorized.items():
        if category == "other":
            continue
        for phrase in matched_phrases:
            out.append(
                ExtractedPhrase(
                    text=phrase, category=category, confidence=1.0,
                ),
            )
    return out


def categories() -> list[str]:
    """Return the canonical category names from the keyword dict.

    Useful for UI category-picker rendering + test fixtures.
    """
    return list(SYMPTOM_CATEGORIES.keys())


# ---------------------------------------------------------------------------
# Phase 195B — Claude-fallback threshold (plan v1.0 §3)
# ---------------------------------------------------------------------------
#
# CALIBRATION (derived Phase 195B Backend Commit 1, documented here +
# in the Commit 1 phase-log per the F47 audit-trail obligation):
#
# The threshold gates whether the Claude-rich extraction pass runs
# after the keyword pass. "Coverage" = fraction of candidate phrases
# in the transcript that the keyword matcher assigned to a real
# (non-'other') category.
#
# Hybrid calibration corpus: Step 10's 5 device transcripts (all
# clean — all phrases matched, coverage 1.0; used ALONE they push the
# threshold to "never fire Claude") + 18 synthesized edge-case
# fixtures covering keyword-extraction failure modes (informal
# phrasing — "won't kick over"; jargon outside SYMPTOM_CATEGORIES;
# run-on multi-symptom sentences). Running the keyword pass over the
# synthetic set: transcripts a human reads as "has symptoms the
# keyword dict missed" cluster at coverage <= 0.5; transcripts the
# keyword pass handled well cluster at coverage >= 0.6.
#
# Threshold = 0.5 — moderate, NOT aggressive. Step 10's finding that
# on-device keyword extraction is resilient to peripheral STT noise
# (correct fuel-category rows in all 5 conditions) means Claude does
# not need to fire defensively; 0.5 lets keyword handle the clear
# cases + reserves Claude for genuinely ambiguous transcripts. A
# zero-row keyword result on a non-empty transcript ALWAYS fires
# Claude (coverage 0.0 is below any positive threshold; made explicit
# below for clarity).
#
# F47 tickets the post-launch re-derivation against >=50 real
# production transcripts — the synthetic-fixture realism is the
# acknowledged exposure (plan v1.0 Risk #2). Overridable here as a
# single constant when F47's revisit lands.
CLAUDE_FALLBACK_COVERAGE_THRESHOLD = 0.5


def keyword_coverage(
    phrases: list[str],
    extracted: list[ExtractedPhrase],
) -> float:
    """Fraction of candidate phrases the keyword pass categorized.

    ``phrases`` is the :func:`split_into_phrases` output;
    ``extracted`` is the :func:`extract_symptoms_from_transcript`
    output. Coverage = distinct phrases that produced >=1 extracted
    symptom / total candidate phrases. Returns 0.0 for an empty
    phrase list (no transcript content → no coverage; the caller's
    ``should_run_claude_fallback`` treats empty transcripts as
    "nothing to extract", NOT "run Claude").
    """
    if not phrases:
        return 0.0
    matched = {e.text for e in extracted}
    # An ExtractedPhrase.text is the canonical (lowercased/stripped)
    # phrase — the same form split_into_phrases emits, so set
    # membership lines up.
    covered = sum(1 for p in phrases if p in matched)
    return covered / len(phrases)


def should_run_claude_fallback(
    preview_text: Optional[str],
    extracted: list[ExtractedPhrase],
    threshold: float = CLAUDE_FALLBACK_COVERAGE_THRESHOLD,
) -> bool:
    """Decide whether to run the Claude-rich extraction pass.

    Phase 195B plan v1.0 §3 gate. Returns True when the keyword pass
    left enough uncovered that a Claude pass is worth its cost:

    * empty / whitespace transcript → False (nothing to extract).
    * non-empty transcript, keyword produced ZERO rows → True
      (keyword found nothing; the transcript clearly has content).
    * keyword coverage < ``threshold`` → True.
    * else → False (keyword sufficient).
    """
    if preview_text is None or not preview_text.strip():
        return False
    phrases = split_into_phrases(preview_text)
    if not phrases:
        return False
    if not extracted:
        return True
    return keyword_coverage(phrases, extracted) < threshold
