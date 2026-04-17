"""Similar case retrieval — finds past diagnostics matching the current case for RAG context.

Uses multi-factor similarity scoring to rank historical diagnostic records against
the current vehicle + symptoms, then formats top matches into context strings
suitable for injection into AI diagnostic prompts.

Scoring factors:
- Symptom overlap: Jaccard similarity on symptom token sets (0.0-1.0)
- Vehicle match: exact make+model = 1.0, same make = 0.5, different = 0.0
- Year proximity: closer model years score higher (decay over 10-year window)
- Overall score: weighted combination of all factors
"""

from typing import Optional

from pydantic import BaseModel, Field

from motodiag.engine.history import DiagnosticRecord, DiagnosticHistory


class SimilarityScore(BaseModel):
    """Similarity score between a historical record and the current case."""
    record: DiagnosticRecord = Field(..., description="The historical diagnostic record")
    symptom_overlap: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Jaccard similarity on symptom word sets (0.0-1.0)",
    )
    vehicle_match: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Vehicle match score: 1.0=exact, 0.5=same make, 0.0=different",
    )
    year_proximity: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Year proximity score: 1.0=same year, decays over 10-year window",
    )
    overall_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Weighted combination of all similarity factors",
    )


# Default weights for the overall score calculation
DEFAULT_WEIGHTS = {
    "symptom_overlap": 0.50,
    "vehicle_match": 0.30,
    "year_proximity": 0.20,
}


class CaseRetriever:
    """Finds past diagnostics similar to the current case for RAG-style context injection.

    Uses Jaccard similarity on symptom word sets, exact/partial vehicle matching,
    and year proximity scoring to rank historical records.
    """

    def __init__(
        self,
        history: DiagnosticHistory,
        weights: Optional[dict[str, float]] = None,
    ) -> None:
        """Initialize retriever with a diagnostic history source.

        Args:
            history: The DiagnosticHistory instance to search.
            weights: Custom weights for score components. Keys: symptom_overlap,
                     vehicle_match, year_proximity. Defaults to 0.50/0.30/0.20.
        """
        self._history = history
        self._weights = weights or dict(DEFAULT_WEIGHTS)

    @property
    def history(self) -> DiagnosticHistory:
        """The underlying diagnostic history store."""
        return self._history

    @staticmethod
    def _tokenize_symptoms(symptoms: list[str]) -> set[str]:
        """Convert symptom strings into a normalized word set.

        Strips punctuation, lowercases, removes stopwords shorter than 3 chars.

        Args:
            symptoms: List of symptom descriptions.

        Returns:
            Set of normalized tokens.
        """
        tokens: set[str] = set()
        for symptom in symptoms:
            for word in symptom.lower().split():
                # Strip common punctuation
                cleaned = word.strip(".,;:!?()[]{}\"'")
                if len(cleaned) >= 3:  # Skip very short words (a, an, is, at, etc.)
                    tokens.add(cleaned)
        return tokens

    @staticmethod
    def compute_symptom_overlap(symptoms_a: list[str], symptoms_b: list[str]) -> float:
        """Calculate Jaccard similarity between two symptom sets.

        Jaccard = |A ∩ B| / |A ∪ B|

        Args:
            symptoms_a: First symptom list.
            symptoms_b: Second symptom list.

        Returns:
            Jaccard similarity 0.0-1.0. Returns 0.0 if both sets are empty.
        """
        tokens_a = CaseRetriever._tokenize_symptoms(symptoms_a)
        tokens_b = CaseRetriever._tokenize_symptoms(symptoms_b)

        if not tokens_a and not tokens_b:
            return 0.0

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b

        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def compute_vehicle_match(
        make_a: str, model_a: str,
        make_b: str, model_b: str,
    ) -> float:
        """Calculate vehicle match score.

        - Exact make + model match: 1.0
        - Same make, different model: 0.5
        - Different make: 0.0

        Args:
            make_a: First vehicle make.
            model_a: First vehicle model.
            make_b: Second vehicle make.
            model_b: Second vehicle model.

        Returns:
            Vehicle match score 0.0-1.0.
        """
        make_match = make_a.lower().strip() == make_b.lower().strip()
        model_match = model_a.lower().strip() == model_b.lower().strip()

        if make_match and model_match:
            return 1.0
        elif make_match:
            return 0.5
        else:
            return 0.0

    @staticmethod
    def compute_year_proximity(year_a: int, year_b: int, window: int = 10) -> float:
        """Calculate year proximity score.

        Linear decay over the window: same year = 1.0, max_distance = 0.0.

        Args:
            year_a: First vehicle year.
            year_b: Second vehicle year.
            window: Maximum year difference before score reaches 0.0 (default 10).

        Returns:
            Year proximity score 0.0-1.0.
        """
        diff = abs(year_a - year_b)
        if diff >= window:
            return 0.0
        return round(1.0 - (diff / window), 2)

    def compute_similarity(
        self,
        current_make: str,
        current_model: str,
        current_year: int,
        current_symptoms: list[str],
        record: DiagnosticRecord,
    ) -> SimilarityScore:
        """Calculate full similarity score between current case and a historical record.

        Args:
            current_make: Current vehicle make.
            current_model: Current vehicle model.
            current_year: Current vehicle year.
            current_symptoms: Current reported symptoms.
            record: Historical diagnostic record to compare against.

        Returns:
            SimilarityScore with individual factor scores and weighted overall.
        """
        symptom_overlap = self.compute_symptom_overlap(current_symptoms, record.symptoms)
        vehicle_match = self.compute_vehicle_match(
            current_make, current_model, record.make, record.model,
        )
        year_proximity = self.compute_year_proximity(current_year, record.year)

        # Weighted overall score
        overall = (
            self._weights["symptom_overlap"] * symptom_overlap
            + self._weights["vehicle_match"] * vehicle_match
            + self._weights["year_proximity"] * year_proximity
        )
        overall = round(min(1.0, max(0.0, overall)), 3)

        return SimilarityScore(
            record=record,
            symptom_overlap=round(symptom_overlap, 3),
            vehicle_match=vehicle_match,
            year_proximity=year_proximity,
            overall_score=overall,
        )

    def find_similar_cases(
        self,
        make: str,
        model: str,
        year: int,
        symptoms: list[str],
        top_n: int = 5,
        min_score: float = 0.0,
    ) -> list[SimilarityScore]:
        """Find the most similar historical cases to the current diagnostic session.

        Searches all records in history, scores each, and returns the top-N
        ranked by overall_score descending.

        Args:
            make: Current vehicle make.
            model: Current vehicle model.
            year: Current vehicle year.
            symptoms: Current reported symptoms.
            top_n: Maximum number of results to return.
            min_score: Minimum overall_score to include in results.

        Returns:
            List of SimilarityScore objects ranked by overall_score, highest first.
        """
        scored: list[SimilarityScore] = []

        for record in self._history.get_recent(n=self._history.count):
            sim = self.compute_similarity(make, model, year, symptoms, record)
            if sim.overall_score >= min_score:
                scored.append(sim)

        # Sort by overall_score descending, then by timestamp for ties
        scored.sort(key=lambda s: (s.overall_score, s.record.timestamp), reverse=True)
        return scored[:top_n]

    def build_case_context(
        self,
        make: str,
        model: str,
        year: int,
        symptoms: list[str],
        top_n: int = 3,
        min_score: float = 0.1,
    ) -> str:
        """Format similar cases into a context string for AI prompt injection.

        Retrieves similar cases and formats them into a structured text block
        that can be prepended to the AI diagnostic prompt for RAG-style learning.

        Args:
            make: Current vehicle make.
            model: Current vehicle model.
            year: Current vehicle year.
            symptoms: Current reported symptoms.
            top_n: Number of similar cases to include (default 3).
            min_score: Minimum score threshold (default 0.1).

        Returns:
            Formatted context string. Empty string if no similar cases found.
        """
        similar = self.find_similar_cases(
            make=make, model=model, year=year, symptoms=symptoms,
            top_n=top_n, min_score=min_score,
        )

        if not similar:
            return ""

        lines: list[str] = []
        lines.append("=== SIMILAR PAST DIAGNOSTICS (for reference) ===")
        lines.append("")

        for i, sim in enumerate(similar, 1):
            r = sim.record
            lines.append(f"--- Case {i} (similarity: {sim.overall_score:.1%}) ---")
            lines.append(f"Vehicle: {r.year} {r.make} {r.model}")
            lines.append(f"Symptoms: {', '.join(r.symptoms)}")
            lines.append(f"Diagnosis: {r.diagnosis} (confidence: {r.confidence:.0%})")
            if r.resolution:
                lines.append(f"Resolution: {r.resolution}")
            if r.cost is not None:
                lines.append(f"Cost: ${r.cost:.2f}")
            if r.parts_used:
                lines.append(f"Parts used: {', '.join(r.parts_used)}")
            lines.append("")

        lines.append("=== END SIMILAR CASES ===")
        return "\n".join(lines)
