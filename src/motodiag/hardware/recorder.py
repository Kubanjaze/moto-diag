"""Sensor recording persistence (Phase 142).

:class:`RecordingManager` is the CRUD + file-split engine behind the
``motodiag hardware log`` subgroup. It turns Phase 141's ephemeral
:class:`~motodiag.hardware.sensors.SensorStreamer` output into durable
recordings a mechanic can replay, diff, and export weeks later.

Design highlights
-----------------

- **SQLite + JSONL split.** Under a 1000-row threshold, every reading
  lands in ``sensor_samples``. Above the threshold the recording spills
  to a ``~/.motodiag/recordings/<uuid>.jsonl`` sidecar, and
  ``sensor_samples`` retains every 100th reading as a sparse summary
  for fast ad-hoc queries. :meth:`load_recording` transparently merges
  the two sources so consumers never need to know where a given sample
  came from.
- **Flush every 1 s or 100 samples, whichever first.** Bounded crash
  loss (≤ 1 s of data) without pathological write amplification at
  high poll rates.
- **Single adaptation point for Phase 141's SensorReading.** The
  ``_reading_to_sample_row`` helper is the one place the code assumes
  field names like ``pid_hex`` / ``value`` / ``captured_at`` — any
  upstream rename is a one-line fix.
- **pid_hex normalized to Phase 141's ``"0x0C"`` format.** Stored with
  the ``0x`` prefix and uppercase hex byte so string equality works
  across the boundary between SQLite rows, JSONL sidecars, and live
  :class:`~motodiag.hardware.sensors.SensorReading` objects.
- **Linear-interp diff alignment** via :meth:`diff_recordings`. Two
  recordings of different lengths get resampled (stdlib ``bisect``) so
  per-PID stats (min / max / avg) are apples-to-apples. Flags a PID
  when ``|pct_change| > 10 %``.
"""

from __future__ import annotations

import bisect
import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from motodiag.core.database import get_connection, get_db_path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Total SQLite-row threshold at which we spill to JSONL. Below this,
#: every reading stays in ``sensor_samples``; at/above, new readings
#: stream into the JSONL sidecar with a 1-in-100 sparse summary copy.
SPILL_THRESHOLD: int = 1000

#: Emit every Nth reading to ``sensor_samples`` once the recording has
#: spilled to JSONL. The sparse summary keeps ad-hoc SQL queries cheap
#: (e.g. "average RPM in the first 30 s") without having to stream the
#: whole JSONL sidecar.
SPARSE_EVERY: int = 100

#: Flush the in-memory buffer every this many readings, even if the
#: time-based trigger has not fired yet. Bounded write amplification
#: at high poll rates.
FLUSH_EVERY_N: int = 100

#: Flush the in-memory buffer every this many seconds, even if the
#: count-based trigger has not fired yet. Bounded crash-loss window.
FLUSH_EVERY_S: float = 1.0

#: Flag threshold for :class:`PIDDiff`. Empirically catches "genuinely
#: hot" / "genuinely low" signals without tripping on noise-drift.
DIFF_FLAG_PCT: float = 10.0


# ---------------------------------------------------------------------------
# Diff report dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PIDDiff:
    """One row of a :class:`DiffReport` — stat delta for a single PID.

    ``stat_1`` / ``stat_2`` are the chosen metric (``min`` / ``max`` /
    ``avg``) for the two aligned recordings. ``pct_change`` is
    ``(stat_2 - stat_1) / stat_1 * 100`` with a ``0.0`` guard when
    ``stat_1 == 0`` (avoids ``ZeroDivisionError``). ``flagged`` fires
    when ``|pct_change| > DIFF_FLAG_PCT`` so the CLI can paint a 🔥 icon.
    """

    pid_hex: str
    name: str
    unit: str
    stat_1: Optional[float]
    stat_2: Optional[float]
    delta: Optional[float]
    pct_change: float
    flagged: bool


@dataclass(frozen=True)
class DiffReport:
    """Full output of :meth:`RecordingManager.diff_recordings`.

    ``matched`` covers PIDs present in both recordings (stats aligned).
    ``only_in_1`` / ``only_in_2`` list the PID-hex strings that appear
    in exactly one of the two recordings — surfaced so the mechanic can
    see coverage gaps (one session recorded RPM but the other didn't).
    """

    recording_1_id: int
    recording_2_id: int
    metric: str
    matched: list[PIDDiff]
    only_in_1: list[str]
    only_in_2: list[str]


# ---------------------------------------------------------------------------
# SensorReading adaptation — single point of contact with Phase 141
# ---------------------------------------------------------------------------


def _reading_to_sample_row(reading: Any) -> dict[str, Any]:
    """Adapt a Phase 141 :class:`SensorReading` to a sensor_samples row.

    This helper is intentionally duck-typed — it reads attributes and
    falls through to ``dict`` indexing — so the test suite can pass
    either a real ``SensorReading`` Pydantic model or a local
    synthetic dataclass. The fields consulted are:

    - ``captured_at`` — :class:`datetime`, rendered as ISO 8601 UTC.
    - ``pid_hex`` — normalized to ``"0x0C"`` (uppercase, ``0x`` prefix)
      regardless of whether the caller hands us ``"0C"``, ``"0x0c"``,
      or the canonical form.
    - ``value`` — nullable float; left as-is (SQLite stores NULL fine).
    - ``raw`` — nullable int.
    - ``unit`` — optional string.

    Centralising the read here means a future upstream rename (e.g.
    Phase 147's hypothetical ``timestamp_utc``) becomes a one-line fix
    rather than a grep-and-replace through the recorder module.
    """
    # Attribute access first (real SensorReading), then dict fallback
    # (tests' synthetic dataclass-like dicts).
    def get(name: str, default: Any = None) -> Any:
        if isinstance(reading, dict):
            return reading.get(name, default)
        return getattr(reading, name, default)

    captured_at = get("captured_at")
    if isinstance(captured_at, datetime):
        captured_at_iso = captured_at.isoformat()
    else:
        captured_at_iso = str(captured_at) if captured_at is not None else (
            datetime.now(timezone.utc).isoformat()
        )

    raw_pid_hex = get("pid_hex")
    if raw_pid_hex is None:
        # Fall back to synthesizing from ``pid`` if someone passes a
        # SensorReading-adjacent shape that only carries the int.
        pid_int = get("pid")
        pid_hex = f"0x{int(pid_int):02X}" if pid_int is not None else "0x00"
    else:
        pid_hex = str(raw_pid_hex).strip()
        if pid_hex.lower().startswith("0x"):
            # Canonicalize to uppercase tail while keeping the 0x prefix.
            pid_hex = "0x" + pid_hex[2:].upper()
        else:
            pid_hex = "0x" + pid_hex.upper()

    return {
        "captured_at": captured_at_iso,
        "pid_hex": pid_hex,
        "value": get("value"),
        "raw": get("raw"),
        "unit": get("unit") or "",
    }


# ---------------------------------------------------------------------------
# RecordingManager
# ---------------------------------------------------------------------------


class RecordingManager:
    """Durable sensor-recording store with SQLite + JSONL split.

    Parameters
    ----------
    db_path:
        Optional override for the SQLite database path. Defaults to
        :func:`motodiag.core.database.get_db_path` at call time, so
        tests that monkey-patch settings see their tmp DB.
    recordings_dir:
        Directory for JSONL sidecars. Defaults to
        ``~/.motodiag/recordings``. Created lazily on first spill.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        recordings_dir: Optional[Path] = None,
    ) -> None:
        self._db_path = db_path
        self._recordings_dir = (
            recordings_dir
            if recordings_dir is not None
            else Path.home() / ".motodiag" / "recordings"
        )
        # Buffers keyed by recording_id so concurrent recordings through
        # the same manager don't contaminate each other.
        self._buffer: dict[int, list[dict[str, Any]]] = {}
        self._last_flush: dict[int, float] = {}
        self._file_ref: dict[int, Optional[str]] = {}
        self._total_rows_in_sqlite: dict[int, int] = {}
        self._total_rows_overall: dict[int, int] = {}
        self._lock = threading.Lock()

    # --- internal helpers ---------------------------------------------------

    def _resolve_db_path(self) -> str:
        return self._db_path or get_db_path()

    def _ensure_dir(self) -> None:
        self._recordings_dir.mkdir(parents=True, exist_ok=True)

    def _jsonl_path(self, file_ref: str) -> Path:
        return self._recordings_dir / file_ref

    # --- start / stop ------------------------------------------------------

    def start_recording(
        self,
        vehicle_id: Optional[int],
        label: Optional[str],
        pids: list[str],
        protocol_name: str,
        notes: Optional[str] = None,
    ) -> int:
        """Insert a new recording row and return its primary key.

        ``pids`` is stored as a compact comma-separated uppercase string
        without the ``0x`` prefix (``"0C,05,42"``) — matches the
        implementation spec's ``pids_csv`` column.
        """
        pids_csv = ",".join(self._normalize_pid_for_csv(p) for p in pids)
        started_at = datetime.now(timezone.utc).isoformat()

        with get_connection(self._resolve_db_path()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO sensor_recordings
                    (vehicle_id, session_label, started_at, protocol_name,
                     pids_csv, notes, sample_count, file_ref)
                VALUES (?, ?, ?, ?, ?, ?, 0, NULL)
                """,
                (
                    vehicle_id,
                    label,
                    started_at,
                    protocol_name,
                    pids_csv,
                    notes,
                ),
            )
            recording_id = int(cursor.lastrowid)

        with self._lock:
            self._buffer[recording_id] = []
            self._last_flush[recording_id] = time.monotonic()
            self._file_ref[recording_id] = None
            self._total_rows_in_sqlite[recording_id] = 0
            self._total_rows_overall[recording_id] = 0

        return recording_id

    @staticmethod
    def _normalize_pid_for_csv(pid: str) -> str:
        """Strip ``0x`` prefix + uppercase for the ``pids_csv`` column."""
        s = str(pid).strip()
        if s.lower().startswith("0x"):
            s = s[2:]
        return s.upper()

    def append_samples(
        self,
        recording_id: int,
        readings: Iterable[Any],
    ) -> None:
        """Buffer readings and flush per policy (1 s OR 100 samples)."""
        rows = [_reading_to_sample_row(r) for r in readings]
        if not rows:
            return

        with self._lock:
            if recording_id not in self._buffer:
                raise ValueError(
                    f"Recording {recording_id} was not started via "
                    "this RecordingManager instance"
                )
            self._buffer[recording_id].extend(rows)

            now = time.monotonic()
            should_flush = (
                len(self._buffer[recording_id]) >= FLUSH_EVERY_N
                or (now - self._last_flush[recording_id]) >= FLUSH_EVERY_S
            )
            if should_flush:
                self._flush_locked(recording_id)

    def _flush_locked(self, recording_id: int) -> None:
        """Drain the buffer to SQLite + (optionally) JSONL.

        Called with ``self._lock`` held. Updates ``sample_count`` on the
        recording row so ``list_recordings`` / ``show`` stay accurate
        without a separate aggregate query.
        """
        pending = self._buffer.get(recording_id, [])
        if not pending:
            self._last_flush[recording_id] = time.monotonic()
            return

        file_ref = self._file_ref.get(recording_id)
        sqlite_rows_so_far = self._total_rows_in_sqlite.get(recording_id, 0)
        total_overall = self._total_rows_overall.get(recording_id, 0)

        sqlite_rows_to_insert: list[dict[str, Any]] = []
        jsonl_rows_to_append: list[dict[str, Any]] = []

        if file_ref is None and (sqlite_rows_so_far + len(pending)) < SPILL_THRESHOLD:
            # Wholly under the threshold — stream every row into SQLite.
            sqlite_rows_to_insert = list(pending)
        else:
            # We are at / crossing the threshold. Any row that would
            # push us to SPILL_THRESHOLD or above spills to JSONL; on
            # the very first spill we allocate a UUID sidecar file and
            # persist its name to ``file_ref``.
            if file_ref is None:
                file_ref = f"{uuid.uuid4().hex}.jsonl"
                self._ensure_dir()
                self._file_ref[recording_id] = file_ref
                # Persist file_ref immediately so a crash mid-append is
                # still prunable via the sidecar path.
                with get_connection(self._resolve_db_path()) as conn:
                    conn.execute(
                        "UPDATE sensor_recordings SET file_ref = ? WHERE id = ?",
                        (file_ref, recording_id),
                    )

            for idx, row in enumerate(pending):
                combined_index = sqlite_rows_so_far + idx + 1
                # Rows that are still in the SQLite-only regime go to
                # sensor_samples normally. Once we're past the threshold
                # we spill to JSONL and keep only 1-in-SPARSE_EVERY rows
                # in SQLite as a sparse summary.
                if combined_index <= SPILL_THRESHOLD:
                    sqlite_rows_to_insert.append(row)
                else:
                    jsonl_rows_to_append.append(row)
                    # Count position within the spilled tail so we
                    # emit a sparse-summary row every SPARSE_EVERY-th
                    # reading post-threshold.
                    tail_index = combined_index - SPILL_THRESHOLD
                    if tail_index % SPARSE_EVERY == 0:
                        sqlite_rows_to_insert.append(row)

        # --- SQLite flush ---
        if sqlite_rows_to_insert:
            with get_connection(self._resolve_db_path()) as conn:
                conn.executemany(
                    """
                    INSERT INTO sensor_samples
                        (recording_id, captured_at, pid_hex, value, raw, unit)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            recording_id,
                            row["captured_at"],
                            row["pid_hex"],
                            row["value"],
                            row["raw"],
                            row["unit"],
                        )
                        for row in sqlite_rows_to_insert
                    ],
                )
            self._total_rows_in_sqlite[recording_id] = (
                sqlite_rows_so_far + len(sqlite_rows_to_insert)
            )

        # --- JSONL flush ---
        if jsonl_rows_to_append and file_ref is not None:
            path = self._jsonl_path(file_ref)
            # Open fresh per flush — no long-lived handle, which keeps
            # Windows file locking happy when a concurrent reader
            # (e.g. ``log show`` in another shell) opens the sidecar.
            with open(path, "a", encoding="utf-8") as fh:
                for row in jsonl_rows_to_append:
                    fh.write(json.dumps(row) + "\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except (OSError, AttributeError):  # pragma: no cover
                    # Best-effort fsync — tmp filesystems on Windows CI
                    # occasionally refuse; we've already flushed to the
                    # OS page cache so the crash budget still holds.
                    pass

        total_overall += len(pending)
        self._total_rows_overall[recording_id] = total_overall

        # Bump sample_count on the recording row so list/show stay fresh.
        with get_connection(self._resolve_db_path()) as conn:
            conn.execute(
                "UPDATE sensor_recordings SET sample_count = ? WHERE id = ?",
                (total_overall, recording_id),
            )

        self._buffer[recording_id] = []
        self._last_flush[recording_id] = time.monotonic()

    def stop_recording(
        self,
        recording_id: int,
        hz_stats: Optional[tuple[float, float]] = None,
    ) -> None:
        """Final flush + set ``stopped_at`` (optionally ``min_hz``/``max_hz``)."""
        with self._lock:
            if recording_id in self._buffer:
                self._flush_locked(recording_id)

        stopped_at = datetime.now(timezone.utc).isoformat()
        min_hz, max_hz = (None, None)
        if hz_stats is not None:
            min_hz, max_hz = float(hz_stats[0]), float(hz_stats[1])

        with get_connection(self._resolve_db_path()) as conn:
            conn.execute(
                """
                UPDATE sensor_recordings
                   SET stopped_at = ?, min_hz = ?, max_hz = ?
                 WHERE id = ?
                """,
                (stopped_at, min_hz, max_hz, recording_id),
            )

        # Drop per-recording state once we've finalized.
        with self._lock:
            self._buffer.pop(recording_id, None)
            self._last_flush.pop(recording_id, None)

    # --- load / list --------------------------------------------------------

    def load_recording(
        self,
        recording_id: int,
    ) -> tuple[dict[str, Any], Iterator[dict[str, Any]]]:
        """Return ``(metadata_dict, samples_iterator)``.

        The iterator yields samples in ascending ``captured_at`` order
        across both SQLite and JSONL sources. When the recording spilled
        to JSONL, the sparse-summary rows in ``sensor_samples`` are
        filtered out of the SQLite stream so consumers don't see
        duplicates — the JSONL sidecar is authoritative for the spilled
        tail.
        """
        meta = self._fetch_metadata(recording_id)
        if meta is None:
            raise KeyError(f"Recording {recording_id} not found")

        file_ref = meta.get("file_ref")
        iterator = self._merge_samples(recording_id, file_ref)
        return meta, iterator

    def _fetch_metadata(self, recording_id: int) -> Optional[dict[str, Any]]:
        with get_connection(self._resolve_db_path()) as conn:
            cursor = conn.execute(
                "SELECT * FROM sensor_recordings WHERE id = ?",
                (recording_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def _merge_samples(
        self,
        recording_id: int,
        file_ref: Optional[str],
    ) -> Iterator[dict[str, Any]]:
        """Yield samples time-ordered from SQLite + JSONL sources.

        When ``file_ref`` is set, the SQLite stream excludes the
        sparse-summary rows that correspond to spilled tail samples
        (those rows also exist in the JSONL sidecar, which is
        authoritative). The filter logic: load all SQLite rows first,
        load all JSONL rows, drop SQLite rows whose ``(captured_at,
        pid_hex, raw)`` tuple appears in the JSONL set, then merge by
        ``captured_at``.
        """
        with get_connection(self._resolve_db_path()) as conn:
            cursor = conn.execute(
                """
                SELECT captured_at, pid_hex, value, raw, unit
                  FROM sensor_samples
                 WHERE recording_id = ?
                 ORDER BY captured_at ASC
                """,
                (recording_id,),
            )
            sqlite_rows = [dict(r) for r in cursor.fetchall()]

        if not file_ref:
            for row in sqlite_rows:
                yield row
            return

        jsonl_path = self._jsonl_path(file_ref)
        jsonl_rows: list[dict[str, Any]] = []
        if jsonl_path.exists():
            with open(jsonl_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        jsonl_rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip a corrupt line rather than abort playback.
                        continue

        # Build a set of JSONL-row signatures so we can subtract the
        # sparse-summary duplicates from the SQLite stream.
        jsonl_sigs = {
            (r.get("captured_at"), r.get("pid_hex"), r.get("raw"))
            for r in jsonl_rows
        }
        filtered_sqlite = [
            r for r in sqlite_rows
            if (r.get("captured_at"), r.get("pid_hex"), r.get("raw"))
            not in jsonl_sigs
        ]

        merged = filtered_sqlite + jsonl_rows
        merged.sort(key=lambda r: r.get("captured_at") or "")
        for row in merged:
            yield row

    def list_recordings(
        self,
        vehicle_id: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List recordings with optional filters.

        ``since`` / ``until`` are ISO 8601 strings compared against
        ``started_at`` lexicographically (which is correct for UTC ISO
        8601). Results are ordered most-recent-first.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if vehicle_id is not None:
            clauses.append("vehicle_id = ?")
            params.append(vehicle_id)
        if since is not None:
            clauses.append("started_at >= ?")
            params.append(since)
        if until is not None:
            clauses.append("started_at <= ?")
            params.append(until)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"SELECT * FROM sensor_recordings {where} "
            "ORDER BY started_at DESC LIMIT ?"
        )
        params.append(int(limit))

        with get_connection(self._resolve_db_path()) as conn:
            cursor = conn.execute(sql, tuple(params))
            return [dict(r) for r in cursor.fetchall()]

    # --- prune --------------------------------------------------------------

    def prune(self, older_than_days: Optional[int] = None) -> tuple[int, int]:
        """Delete recordings older than ``older_than_days``.

        Returns ``(rowcount, bytes_freed)`` — ``rowcount`` is the number
        of ``sensor_recordings`` rows deleted (cascades to
        ``sensor_samples`` via the FK), and ``bytes_freed`` is the total
        size of the JSONL sidecars unlinked. Missing sidecar files are
        tolerated silently (mechanic may have deleted the JSONL
        manually or a crash may have left a dangling ``file_ref``).

        ``older_than_days=None`` or ``0`` deletes *all* recordings —
        useful for test-suite teardown or an emergency wipe, but the
        CLI wraps this in a ``--yes`` prompt.
        """
        with get_connection(self._resolve_db_path()) as conn:
            if older_than_days is None or older_than_days <= 0:
                cursor = conn.execute(
                    "SELECT id, file_ref FROM sensor_recordings"
                )
            else:
                cursor = conn.execute(
                    "SELECT id, file_ref FROM sensor_recordings "
                    "WHERE julianday('now') - julianday(started_at) > ?",
                    (int(older_than_days),),
                )
            to_delete = [dict(r) for r in cursor.fetchall()]

        if not to_delete:
            return 0, 0

        bytes_freed = 0
        for row in to_delete:
            file_ref = row.get("file_ref")
            if file_ref:
                path = self._jsonl_path(file_ref)
                try:
                    bytes_freed += path.stat().st_size
                except OSError:
                    pass
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    # Windows: the file may be held open by an unclosed
                    # iterator. Swallow — the DB row still gets deleted
                    # and a subsequent prune will reclaim the bytes.
                    pass

        ids = [row["id"] for row in to_delete]
        placeholders = ",".join("?" * len(ids))
        with get_connection(self._resolve_db_path()) as conn:
            conn.execute(
                f"DELETE FROM sensor_recordings WHERE id IN ({placeholders})",
                tuple(ids),
            )

        return len(ids), bytes_freed

    # --- diff ---------------------------------------------------------------

    def diff_recordings(
        self,
        id1: int,
        id2: int,
        metric: str = "avg",
    ) -> DiffReport:
        """Linear-interp aligned diff between two recordings.

        The algorithm:

        1. Load both recordings via :meth:`load_recording` so spilled
           JSONL samples are transparent.
        2. Bucket readings by ``pid_hex`` on each side.
        3. For each common PID, resample the longer series down to the
           shorter series' length using linear interpolation (stdlib
           ``bisect`` + manual interp — no numpy dep).
        4. Compute ``min`` / ``max`` / ``avg`` on the aligned series.
        5. Emit a :class:`PIDDiff` per common PID; flag when
           ``|pct_change| > DIFF_FLAG_PCT``.

        ``metric`` selects which of the per-PID stats populates
        ``stat_1`` / ``stat_2`` / ``delta`` / ``pct_change`` — min, max,
        and avg are all computed regardless of the flag for future
        diff-report consumers.
        """
        if metric not in ("min", "max", "avg"):
            raise ValueError(
                f"metric must be one of min/max/avg (got {metric!r})"
            )

        meta1, iter1 = self.load_recording(id1)
        meta2, iter2 = self.load_recording(id2)

        by_pid_1 = self._bucket_by_pid(iter1)
        by_pid_2 = self._bucket_by_pid(iter2)

        common = sorted(set(by_pid_1.keys()) & set(by_pid_2.keys()))
        only_in_1 = sorted(set(by_pid_1.keys()) - set(by_pid_2.keys()))
        only_in_2 = sorted(set(by_pid_2.keys()) - set(by_pid_1.keys()))

        matched: list[PIDDiff] = []
        for pid_hex in common:
            series_1 = by_pid_1[pid_hex]
            series_2 = by_pid_2[pid_hex]
            values_1 = [v for _, v, _ in series_1 if v is not None]
            values_2 = [v for _, v, _ in series_2 if v is not None]

            if not values_1 or not values_2:
                # Missing values on one side — surface as a PIDDiff with
                # None stats so the CLI renders the row as em-dash.
                matched.append(
                    PIDDiff(
                        pid_hex=pid_hex,
                        name=self._pid_display_name(pid_hex),
                        unit=self._first_unit(series_1) or self._first_unit(series_2) or "",
                        stat_1=None,
                        stat_2=None,
                        delta=None,
                        pct_change=0.0,
                        flagged=False,
                    )
                )
                continue

            # Linear-interp resample both sides down to the shorter length.
            target_len = min(len(values_1), len(values_2))
            aligned_1 = _linear_resample(values_1, target_len)
            aligned_2 = _linear_resample(values_2, target_len)

            stat_1 = _compute_metric(aligned_1, metric)
            stat_2 = _compute_metric(aligned_2, metric)
            delta = stat_2 - stat_1
            if stat_1 == 0:
                pct_change = 0.0
            else:
                pct_change = (delta / stat_1) * 100.0
            flagged = abs(pct_change) > DIFF_FLAG_PCT

            matched.append(
                PIDDiff(
                    pid_hex=pid_hex,
                    name=self._pid_display_name(pid_hex),
                    unit=self._first_unit(series_1) or self._first_unit(series_2) or "",
                    stat_1=stat_1,
                    stat_2=stat_2,
                    delta=delta,
                    pct_change=pct_change,
                    flagged=flagged,
                )
            )

        return DiffReport(
            recording_1_id=id1,
            recording_2_id=id2,
            metric=metric,
            matched=matched,
            only_in_1=only_in_1,
            only_in_2=only_in_2,
        )

    @staticmethod
    def _bucket_by_pid(
        samples: Iterable[dict[str, Any]],
    ) -> dict[str, list[tuple[str, Optional[float], str]]]:
        buckets: dict[str, list[tuple[str, Optional[float], str]]] = {}
        for row in samples:
            pid_hex = row.get("pid_hex") or ""
            captured_at = row.get("captured_at") or ""
            value = row.get("value")
            unit = row.get("unit") or ""
            buckets.setdefault(pid_hex, []).append(
                (captured_at, value, unit)
            )
        return buckets

    @staticmethod
    def _first_unit(series: list[tuple[str, Optional[float], str]]) -> str:
        for _, _, unit in series:
            if unit:
                return unit
        return ""

    @staticmethod
    def _pid_display_name(pid_hex: str) -> str:
        """Best-effort catalog lookup — falls back to the PID hex itself.

        Kept lazy because the sensor catalog is a Phase 141 import and
        pulling it at module-import time would couple recorder loading
        to a sensors module we want to keep decoupled for tests.
        """
        try:
            from motodiag.hardware.sensors import SENSOR_CATALOG
            pid_int = int(pid_hex, 16) if pid_hex.lower().startswith("0x") \
                else int(pid_hex, 16)
            spec = SENSOR_CATALOG.get(pid_int)
            if spec is not None:
                return spec.name
        except Exception:
            pass
        return pid_hex


# ---------------------------------------------------------------------------
# Linear-interp resample (stdlib only)
# ---------------------------------------------------------------------------


def _linear_resample(values: list[float], target_len: int) -> list[float]:
    """Resample ``values`` to ``target_len`` via linear interpolation.

    Uses parametric t ∈ [0, 1] for both source and target, so the
    endpoints are preserved and intermediate samples are computed by
    ``bisect``-locating the bracketing source indices and linearly
    interpolating. No numpy dependency.
    """
    n = len(values)
    if target_len <= 0:
        return []
    if target_len == 1 or n == 1:
        return [float(values[0])]
    if n == target_len:
        return [float(v) for v in values]

    # Source timeline is equally-spaced t_src[i] = i / (n - 1).
    src_ts = [i / (n - 1) for i in range(n)]
    out: list[float] = []
    for k in range(target_len):
        t = k / (target_len - 1)
        idx = bisect.bisect_left(src_ts, t)
        if idx == 0:
            out.append(float(values[0]))
            continue
        if idx >= n:
            out.append(float(values[-1]))
            continue
        # Linear interp between src_ts[idx - 1] and src_ts[idx].
        t0 = src_ts[idx - 1]
        t1 = src_ts[idx]
        v0 = float(values[idx - 1])
        v1 = float(values[idx])
        if t1 == t0:
            out.append(v0)
        else:
            frac = (t - t0) / (t1 - t0)
            out.append(v0 + (v1 - v0) * frac)
    return out


def _compute_metric(values: list[float], metric: str) -> float:
    """Compute min / max / avg on a non-empty float list."""
    if not values:
        return 0.0
    if metric == "min":
        return float(min(values))
    if metric == "max":
        return float(max(values))
    # avg
    return float(sum(values) / len(values))


__all__ = [
    "RecordingManager",
    "PIDDiff",
    "DiffReport",
    "SPILL_THRESHOLD",
    "SPARSE_EVERY",
    "FLUSH_EVERY_N",
    "FLUSH_EVERY_S",
    "DIFF_FLAG_PCT",
]
