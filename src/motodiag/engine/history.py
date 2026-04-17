"""Diagnostic history + learning — stores and retrieves past diagnostic sessions for RAG-style learning.

Maintains an in-memory history of completed diagnostic sessions, enabling:
- Recording completed diagnostics with outcomes, costs, and resolution details
- Filtered retrieval by make, model, year range, and symptom keywords
- Statistical summaries (avg confidence, most common diagnoses, cost analysis)
- Similar case lookup for RAG context injection into AI diagnostic prompts
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class DiagnosticRecord(BaseModel):
    """A single completed diagnostic session record."""
    record_id: str = Field(..., description="Unique identifier for this record")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this diagnostic was performed",
    )
    make: str = Field(..., description="Motorcycle manufacturer (e.g., Harley-Davidson)")
    model: str = Field(..., description="Motorcycle model (e.g., Sportster 1200)")
    year: int = Field(..., ge=1900, le=2100, description="Model year")
    symptoms: list[str] = Field(default_factory=list, description="Reported symptoms")
    diagnosis: str = Field(..., description="Final diagnosis / root cause determined")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in diagnosis 0.0-1.0")
    resolution: Optional[str] = Field(None, description="How the issue was resolved")
    cost: Optional[float] = Field(None, ge=0.0, description="Total repair cost in USD")
    duration_minutes: Optional[int] = Field(None, ge=0, description="Diagnostic + repair duration in minutes")
    notes: Optional[str] = Field(None, description="Additional notes from the mechanic")
    parts_used: list[str] = Field(default_factory=list, description="Parts used in the repair")
    system_category: Optional[str] = Field(
        None,
        description="Primary system involved (electrical, fuel, mechanical, cooling, drivetrain, braking)",
    )


class HistoryStatistics(BaseModel):
    """Summary statistics from the diagnostic history."""
    total_records: int = Field(default=0, description="Total number of diagnostic records")
    avg_confidence: float = Field(default=0.0, description="Average diagnosis confidence")
    avg_cost: Optional[float] = Field(None, description="Average repair cost (records with cost only)")
    avg_duration_minutes: Optional[float] = Field(
        None, description="Average duration in minutes (records with duration only)"
    )
    most_common_diagnoses: list[tuple[str, int]] = Field(
        default_factory=list, description="Top diagnoses by frequency: [(diagnosis, count), ...]"
    )
    most_common_makes: list[tuple[str, int]] = Field(
        default_factory=list, description="Top makes by frequency: [(make, count), ...]"
    )
    most_common_symptoms: list[tuple[str, int]] = Field(
        default_factory=list, description="Top symptoms by frequency: [(symptom, count), ...]"
    )
    records_with_resolution: int = Field(default=0, description="Records that have a resolution recorded")
    resolution_rate: float = Field(default=0.0, description="Fraction of records with a resolution 0.0-1.0")


class DiagnosticHistory:
    """In-memory diagnostic history store for recording and retrieving past sessions.

    Provides filtered retrieval, statistical summaries, and similar-case lookup
    for RAG-style context injection into AI diagnostic prompts.
    """

    def __init__(self) -> None:
        """Initialize empty history store."""
        self._records: list[DiagnosticRecord] = []
        self._record_index: dict[str, DiagnosticRecord] = {}  # record_id → record

    @property
    def count(self) -> int:
        """Number of records in the history."""
        return len(self._records)

    def add_record(self, record: DiagnosticRecord) -> None:
        """Store a completed diagnostic session.

        Args:
            record: The diagnostic record to store.

        Raises:
            ValueError: If record_id already exists in history.
        """
        if record.record_id in self._record_index:
            raise ValueError(f"Record ID '{record.record_id}' already exists in history")
        self._records.append(record)
        self._record_index[record.record_id] = record

    def get_record(self, record_id: str) -> Optional[DiagnosticRecord]:
        """Retrieve a specific record by ID.

        Args:
            record_id: The unique record identifier.

        Returns:
            The matching record, or None if not found.
        """
        return self._record_index.get(record_id)

    def get_records(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        symptom_keywords: Optional[list[str]] = None,
        diagnosis_keywords: Optional[list[str]] = None,
        system_category: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> list[DiagnosticRecord]:
        """Retrieve records with optional filters.

        All filters are AND-combined. Keyword matching is case-insensitive and
        uses substring matching (any keyword must appear in any symptom/diagnosis).

        Args:
            make: Filter by motorcycle make (case-insensitive substring).
            model: Filter by motorcycle model (case-insensitive substring).
            year_min: Minimum model year (inclusive).
            year_max: Maximum model year (inclusive).
            symptom_keywords: At least one keyword must appear in at least one symptom.
            diagnosis_keywords: At least one keyword must appear in the diagnosis.
            system_category: Filter by system category (case-insensitive exact match).
            min_confidence: Minimum confidence threshold.
            limit: Maximum number of records to return.

        Returns:
            List of matching records, ordered by timestamp descending (newest first).
        """
        results: list[DiagnosticRecord] = []

        for record in self._records:
            # Apply each filter
            if make and make.lower() not in record.make.lower():
                continue
            if model and model.lower() not in record.model.lower():
                continue
            if year_min is not None and record.year < year_min:
                continue
            if year_max is not None and record.year > year_max:
                continue
            if min_confidence is not None and record.confidence < min_confidence:
                continue
            if system_category and (
                not record.system_category
                or record.system_category.lower() != system_category.lower()
            ):
                continue

            # Symptom keyword matching: any keyword in any symptom
            if symptom_keywords:
                symptom_text = " ".join(s.lower() for s in record.symptoms)
                if not any(kw.lower() in symptom_text for kw in symptom_keywords):
                    continue

            # Diagnosis keyword matching: any keyword in diagnosis
            if diagnosis_keywords:
                diag_lower = record.diagnosis.lower()
                if not any(kw.lower() in diag_lower for kw in diagnosis_keywords):
                    continue

            results.append(record)

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda r: r.timestamp, reverse=True)

        if limit is not None:
            results = results[:limit]

        return results

    def get_recent(self, n: int = 10) -> list[DiagnosticRecord]:
        """Retrieve the most recent N records.

        Args:
            n: Number of recent records to return (default 10).

        Returns:
            Up to N records, newest first.
        """
        sorted_records = sorted(self._records, key=lambda r: r.timestamp, reverse=True)
        return sorted_records[:n]

    def get_statistics(self, top_n: int = 5) -> HistoryStatistics:
        """Compute summary statistics across all records.

        Args:
            top_n: Number of top items to include in frequency lists.

        Returns:
            HistoryStatistics with aggregated data.
        """
        if not self._records:
            return HistoryStatistics()

        total = len(self._records)

        # Average confidence
        avg_conf = sum(r.confidence for r in self._records) / total

        # Average cost (only records with cost)
        costs = [r.cost for r in self._records if r.cost is not None]
        avg_cost = sum(costs) / len(costs) if costs else None

        # Average duration (only records with duration)
        durations = [r.duration_minutes for r in self._records if r.duration_minutes is not None]
        avg_dur = sum(durations) / len(durations) if durations else None

        # Most common diagnoses
        diag_counts: dict[str, int] = {}
        for r in self._records:
            diag_lower = r.diagnosis.lower().strip()
            diag_counts[diag_lower] = diag_counts.get(diag_lower, 0) + 1
        most_common_diag = sorted(diag_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # Most common makes
        make_counts: dict[str, int] = {}
        for r in self._records:
            make_lower = r.make.lower().strip()
            make_counts[make_lower] = make_counts.get(make_lower, 0) + 1
        most_common_makes = sorted(make_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # Most common symptoms
        symptom_counts: dict[str, int] = {}
        for r in self._records:
            for s in r.symptoms:
                s_lower = s.lower().strip()
                symptom_counts[s_lower] = symptom_counts.get(s_lower, 0) + 1
        most_common_symptoms = sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # Resolution rate
        resolved = sum(1 for r in self._records if r.resolution is not None)
        resolution_rate = resolved / total if total > 0 else 0.0

        return HistoryStatistics(
            total_records=total,
            avg_confidence=round(avg_conf, 3),
            avg_cost=round(avg_cost, 2) if avg_cost is not None else None,
            avg_duration_minutes=round(avg_dur, 1) if avg_dur is not None else None,
            most_common_diagnoses=most_common_diag,
            most_common_makes=most_common_makes,
            most_common_symptoms=most_common_symptoms,
            records_with_resolution=resolved,
            resolution_rate=round(resolution_rate, 3),
        )

    def find_similar(
        self,
        make: str,
        model: str,
        year: int,
        symptoms: list[str],
        top_n: int = 5,
    ) -> list[DiagnosticRecord]:
        """Find past records most similar to the current case for RAG context.

        Scoring heuristic:
        - Exact make+model match: +3 points
        - Same make only: +1 point
        - Year within 3 years: +1 point
        - Each matching symptom keyword: +2 points

        Args:
            make: Current vehicle make.
            model: Current vehicle model.
            year: Current vehicle year.
            symptoms: Current symptoms reported.
            top_n: Number of similar cases to return.

        Returns:
            Up to top_n records, ranked by similarity score (highest first).
        """
        if not self._records:
            return []

        scored: list[tuple[float, DiagnosticRecord]] = []
        current_symptom_words = set()
        for s in symptoms:
            for word in s.lower().split():
                current_symptom_words.add(word)

        for record in self._records:
            score = 0.0

            # Vehicle matching
            make_match = make.lower() == record.make.lower()
            model_match = model.lower() == record.model.lower()
            if make_match and model_match:
                score += 3.0
            elif make_match:
                score += 1.0

            # Year proximity
            year_diff = abs(year - record.year)
            if year_diff <= 3:
                score += 1.0
            elif year_diff <= 6:
                score += 0.5

            # Symptom overlap — count words in common
            record_symptom_words = set()
            for s in record.symptoms:
                for word in s.lower().split():
                    record_symptom_words.add(word)

            overlap = current_symptom_words & record_symptom_words
            score += len(overlap) * 2.0

            if score > 0:
                scored.append((score, record))

        # Sort by score descending, then by timestamp descending for ties
        scored.sort(key=lambda x: (x[0], x[1].timestamp), reverse=True)
        return [record for _, record in scored[:top_n]]

    def clear(self) -> None:
        """Remove all records from history."""
        self._records.clear()
        self._record_index.clear()

    def remove_record(self, record_id: str) -> bool:
        """Remove a specific record by ID.

        Args:
            record_id: The record to remove.

        Returns:
            True if the record was found and removed, False otherwise.
        """
        record = self._record_index.pop(record_id, None)
        if record is None:
            return False
        self._records.remove(record)
        return True

    def export_records(self) -> list[dict]:
        """Export all records as a list of dicts (for serialization).

        Returns:
            List of record dictionaries.
        """
        return [r.model_dump(mode="json") for r in self._records]

    def import_records(self, data: list[dict]) -> int:
        """Import records from a list of dicts, skipping duplicates.

        Args:
            data: List of record dictionaries.

        Returns:
            Number of records successfully imported.
        """
        imported = 0
        for item in data:
            try:
                record = DiagnosticRecord(**item)
                if record.record_id not in self._record_index:
                    self._records.append(record)
                    self._record_index[record.record_id] = record
                    imported += 1
            except Exception:
                continue  # Skip invalid records silently
        return imported
