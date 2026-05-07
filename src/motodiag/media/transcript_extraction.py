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
