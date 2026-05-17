"""Phase 195C — unit tests for the Pydantic-Literal-vs-DB-CHECK lint rule.

Covers ``--check-pydantic-literal-vs-check-constraint`` (F37 Track 2 —
the contract-surface-drift lint) inside ``scripts/check_f9_patterns.py``.

The rule enforces: a Pydantic response-model field that maps to a DB
column carrying a ``CHECK (<col> IN ('a', 'b', ...))`` constraint must
be typed ``Literal[...]`` (or a ``Literal`` alias) whose value-set
matches the constraint exactly — so the OpenAPI surface emits a strict
enum and mobile codegen produces a typed union, not a freeform
``string``. CHECK value-sets are keyed by ``(table, column)`` so that
three real tables carrying a same-named ``role`` column with three
*different* value-sets do not cross-wire.

Test class organization (RuleTester-style, one class per concern):
  * TestCleanLiteralMatchingCheck — Literal field matching CHECK -> 0
    findings.
  * TestStrTypedFieldPositive — str-typed field name-matching a CHECK
    -> one pydantic-literal-vs-check error.
  * TestValueSetMismatch — Literal value-set != CHECK set -> one
    pydantic-literal-vs-check error.
  * TestStrEnumWarn — str/Enum field -> WARN (not error).
  * TestOptOuts — file-level + per-line opt-outs (valid suppresses;
    malformed -> *-malformed-optout + underlying still reported).
  * TestThreeRoleColumnDisambiguation — THE CLOSURE GATE: three tables
    each with a same-named ``role`` column carrying a different CHECK
    value-set; the rule validates each model against ITS OWN table.
  * TestNegativeFixturePositiveResolution — v1.0.2 closure gate: a
    field name-coinciding with a CHECK column but whose model resolves
    to no CHECK-bearing table yields ZERO findings (no false positive,
    no `ambiguous` finding — that type was removed in v1.0.2).
  * TestCheckParsing — direct coverage of the (table, column) CHECK
    parser (numeric-CHECK skip, rollback_sql ignored, later-migration
    override).

All synthetic fixtures live in ``tmp_path``; this test file does NOT
add CHECK-drift anti-examples to the real ``src/`` tree (would be
self-defeating).

Pattern doc: ``docs/patterns/f9-mock-vs-runtime-drift.md``.
Plan: ``docs/phases/in_progress/195C_implementation.md``.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------
# Module loader: scripts/ is not a Python package, so we load the module
# via importlib.util to avoid sys.path munging or adding an __init__.py.
# Same pattern as test_phase191d_ssot_constants_lint.py.
# ---------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_f9_patterns.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "check_f9_patterns", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"Could not load {SCRIPT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_f9_patterns"] = mod
    spec.loader.exec_module(mod)
    return mod


_check_f9 = _load_script_module()
F9Finding = _check_f9.F9Finding
check_pydantic_literal_vs_check_constraint = (
    _check_f9.check_pydantic_literal_vs_check_constraint
)
_parse_check_constraints = _check_f9._parse_check_constraints


# ---------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------


def _write(path: Path, body: str) -> Path:
    """Write dedented ``body`` to ``path`` (parents created)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return path


def _migrations_module(*upgrade_sql_blocks: str) -> str:
    """Render a synthetic migrations.py with one Migration() per block.

    Each block becomes a ``Migration(version=N, upgrade_sql='''...''',
    rollback_sql='''...''')`` call. The rollback_sql is deliberately a
    schema-without-CHECK recreate so tests can prove rollback_sql is
    ignored by the parser.
    """
    lines = [
        "class Migration:",
        "    def __init__(self, version, upgrade_sql, rollback_sql=''):",
        "        self.version = version",
        "        self.upgrade_sql = upgrade_sql",
        "        self.rollback_sql = rollback_sql",
        "",
        "MIGRATIONS = [",
    ]
    for idx, sql in enumerate(upgrade_sql_blocks, start=1):
        lines.append(f"    Migration(")
        lines.append(f"        version={idx},")
        lines.append(f'        upgrade_sql="""{sql}""",')
        lines.append(
            f'        rollback_sql="""DROP TABLE IF EXISTS _x;""",'
        )
        lines.append(f"    ),")
    lines.append("]")
    return "\n".join(lines) + "\n"


def _run(
    tmp_path: Path,
    *,
    migrations_sql: tuple[str, ...],
    routes: dict[str, str] | None = None,
    models: str | None = None,
) -> list:
    """Build a synthetic repo layout in tmp_path and run the rule.

    Args:
        migrations_sql: tuple of upgrade_sql strings (one Migration each).
        routes: optional {filename: source} for routes/ modules.
        models: optional source for core/models.py.

    Returns:
        The list of F9Finding objects.
    """
    routes_dir = tmp_path / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)
    migrations_path = tmp_path / "migrations.py"
    _write(migrations_path, _migrations_module(*migrations_sql))

    models_path = tmp_path / "models.py"
    if models is not None:
        _write(models_path, models)

    if routes:
        for name, src in routes.items():
            _write(routes_dir / name, src)

    return check_pydantic_literal_vs_check_constraint(
        routes_dir, models_path, migrations_path,
    )


# ---------------------------------------------------------------------
# Class 1 — TestCleanLiteralMatchingCheck
# ---------------------------------------------------------------------


class TestCleanLiteralMatchingCheck:
    """A Literal field whose value-set matches the CHECK -> 0 findings."""

    def test_inline_literal_matching_check_is_clean(
        self, tmp_path: Path,
    ):
        sql = (
            "CREATE TABLE work_order_photos (\n"
            "  id INTEGER PRIMARY KEY,\n"
            "  role TEXT NOT NULL CHECK (role IN "
            "('before', 'after', 'general', 'undecided'))\n"
            ");"
        )
        route = """
        from pydantic import BaseModel
        from typing import Literal

        class WorkOrderPhotoResponse(BaseModel):
            id: int
            role: Literal["before", "after", "general", "undecided"]
        """
        findings = _run(
            tmp_path,
            migrations_sql=(sql,),
            routes={"photos.py": route},
        )
        assert findings == [], (
            "Expected 0 findings for a value-set-matching Literal:\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_literal_alias_matching_check_is_clean(
        self, tmp_path: Path,
    ):
        """A module-level ``X = Literal[...]`` alias is resolved and
        validated the same as an inline Literal."""
        sql = (
            "CREATE TABLE voice_transcripts (\n"
            "  id INTEGER PRIMARY KEY,\n"
            "  extraction_state TEXT NOT NULL DEFAULT 'pending'\n"
            "  CHECK (extraction_state IN "
            "('pending', 'extracting', 'extracted', 'extraction_failed'))\n"
            ");"
        )
        route = """
        from pydantic import BaseModel
        from typing import Literal

        ExtractionState = Literal[
            "pending", "extracting", "extracted", "extraction_failed"
        ]

        class VoiceTranscriptResponse(BaseModel):
            id: int
            extraction_state: ExtractionState
        """
        findings = _run(
            tmp_path,
            migrations_sql=(sql,),
            routes={"transcripts.py": route},
        )
        assert findings == [], (
            "Expected 0 findings for a matching Literal alias:\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_optional_literal_matching_check_is_clean(
        self, tmp_path: Path,
    ):
        """``Optional[Literal[...]]`` is unwrapped and validated."""
        sql = (
            "CREATE TABLE work_order_photos (\n"
            "  role TEXT CHECK (role IN ('before', 'after'))\n"
            ");"
        )
        route = """
        from pydantic import BaseModel
        from typing import Literal, Optional

        class WorkOrderPhotoResponse(BaseModel):
            role: Optional[Literal["before", "after"]] = None
        """
        findings = _run(
            tmp_path,
            migrations_sql=(sql,),
            routes={"photos.py": route},
        )
        assert findings == [], (
            "Expected 0 findings for Optional[Literal] matching CHECK:\n"
            + "\n".join(f.format() for f in findings)
        )


# ---------------------------------------------------------------------
# Class 2 — TestStrTypedFieldPositive
# ---------------------------------------------------------------------


class TestStrTypedFieldPositive:
    """A str-typed field name-matching a CHECK column -> 1 error.

    This is the F37-instance-#3 regression shape (the transcripts.py
    ``str`` regression).
    """

    def test_str_typed_field_fires_one_finding(self, tmp_path: Path):
        sql = (
            "CREATE TABLE voice_transcripts (\n"
            "  extraction_state TEXT NOT NULL "
            "CHECK (extraction_state IN "
            "('pending', 'extracting', 'extracted'))\n"
            ");"
        )
        route = """
        from pydantic import BaseModel

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: str
        """
        findings = _run(
            tmp_path,
            migrations_sql=(sql,),
            routes={"transcripts.py": route},
        )
        errors = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(errors) == 1, (
            f"Expected exactly 1 pydantic-literal-vs-check finding for "
            f"a str-typed field, got {len(errors)}:\n"
            + "\n".join(f.format() for f in findings)
        )
        f = errors[0]
        assert "extraction_state" in f.message
        assert "Literal" in f.message
        # The message must teach the fix (name the table + values).
        assert "voice_transcripts" in f.message

    def test_optional_str_typed_field_fires(self, tmp_path: Path):
        """``Optional[str]`` is unwrapped to ``str`` and still fires."""
        sql = (
            "CREATE TABLE voice_transcripts (\n"
            "  extraction_state TEXT "
            "CHECK (extraction_state IN ('pending', 'extracted'))\n"
            ");"
        )
        route = """
        from pydantic import BaseModel
        from typing import Optional

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: Optional[str] = None
        """
        findings = _run(
            tmp_path,
            migrations_sql=(sql,),
            routes={"transcripts.py": route},
        )
        errors = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(errors) == 1, (
            f"Expected 1 finding for Optional[str] field, got "
            f"{len(errors)}:\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_models_py_is_also_scanned(self, tmp_path: Path):
        """The rule scans core/models.py, not only routes/."""
        sql = (
            "CREATE TABLE voice_transcripts (\n"
            "  extraction_state TEXT "
            "CHECK (extraction_state IN ('pending', 'extracted'))\n"
            ");"
        )
        models = """
        from pydantic import BaseModel

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: str
        """
        findings = _run(
            tmp_path, migrations_sql=(sql,), models=models,
        )
        errors = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(errors) == 1, (
            f"Expected 1 finding from core/models.py scan, got "
            f"{len(errors)}:\n"
            + "\n".join(f.format() for f in findings)
        )


# ---------------------------------------------------------------------
# Class 3 — TestValueSetMismatch
# ---------------------------------------------------------------------


class TestValueSetMismatch:
    """A Literal whose value-set differs from the CHECK -> 1 error."""

    def test_literal_missing_a_check_value_fires(
        self, tmp_path: Path,
    ):
        """Literal advertises fewer values than the CHECK allows."""
        sql = (
            "CREATE TABLE voice_transcripts (\n"
            "  extraction_state TEXT "
            "CHECK (extraction_state IN "
            "('pending', 'extracting', 'extracted'))\n"
            ");"
        )
        route = """
        from pydantic import BaseModel
        from typing import Literal

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: Literal["pending", "extracted"]
        """
        findings = _run(
            tmp_path,
            migrations_sql=(sql,),
            routes={"transcripts.py": route},
        )
        errors = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(errors) == 1, (
            f"Expected 1 finding for a value-set-mismatched Literal, "
            f"got {len(errors)}:\n"
            + "\n".join(f.format() for f in findings)
        )
        assert "drift" in errors[0].message.lower()

    def test_literal_advertising_extra_value_fires(
        self, tmp_path: Path,
    ):
        """Literal advertises a value the CHECK forbids."""
        sql = (
            "CREATE TABLE voice_transcripts (\n"
            "  extraction_state TEXT "
            "CHECK (extraction_state IN ('pending', 'extracted'))\n"
            ");"
        )
        route = """
        from pydantic import BaseModel
        from typing import Literal

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: Literal["pending", "extracted", "bonus"]
        """
        findings = _run(
            tmp_path,
            migrations_sql=(sql,),
            routes={"transcripts.py": route},
        )
        errors = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(errors) == 1, (
            f"Expected 1 finding for an extra-value Literal, got "
            f"{len(errors)}:\n"
            + "\n".join(f.format() for f in findings)
        )


# ---------------------------------------------------------------------
# Class 4 — TestStrEnumWarn
# ---------------------------------------------------------------------


class TestStrEnumWarn:
    """A str/Enum field -> WARN, never an error."""

    def test_str_enum_field_produces_warn_not_error(
        self, tmp_path: Path,
    ):
        sql = (
            "CREATE TABLE videos (\n"
            "  upload_state TEXT "
            "CHECK (upload_state IN ('uploaded', 'pending', 'failed'))\n"
            ");"
        )
        models = """
        from enum import Enum
        from pydantic import BaseModel

        class VideoUploadState(str, Enum):
            uploaded = "uploaded"
            pending = "pending"
            failed = "failed"

        class VideoResponse(BaseModel):
            upload_state: VideoUploadState
        """
        findings = _run(
            tmp_path, migrations_sql=(sql,), models=models,
        )
        warns = [
            f for f in findings
            if f.rule == "pydantic-literal-vs-check-warn"
        ]
        errors = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(warns) == 1, (
            f"Expected 1 WARN for a str/Enum field, got "
            f"{len(warns)}:\n"
            + "\n".join(f.format() for f in findings)
        )
        assert errors == [], (
            f"str/Enum must NOT produce an error finding, got:\n"
            + "\n".join(f.format() for f in errors)
        )
        assert "WARN" in warns[0].message

    def test_transitive_basemodel_subclass_is_scanned(
        self, tmp_path: Path,
    ):
        """``VideoResponse(VideoBase)`` where ``VideoBase(BaseModel)`` —
        the transitive subclass must still be scanned."""
        sql = (
            "CREATE TABLE voice_transcripts (\n"
            "  extraction_state TEXT "
            "CHECK (extraction_state IN ('pending', 'extracted'))\n"
            ");"
        )
        models = """
        from pydantic import BaseModel

        class VideoBase(BaseModel):
            id: int

        class VoiceTranscriptResponse(VideoBase):
            extraction_state: str
        """
        findings = _run(
            tmp_path, migrations_sql=(sql,), models=models,
        )
        errors = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(errors) == 1, (
            f"Expected the transitive BaseModel subclass to be "
            f"scanned, got {len(errors)} findings:\n"
            + "\n".join(f.format() for f in findings)
        )


# ---------------------------------------------------------------------
# Class 5 — TestOptOuts
# ---------------------------------------------------------------------


class TestOptOuts:
    """File-level + per-line opt-outs (valid suppress; malformed flag)."""

    _SQL = (
        "CREATE TABLE voice_transcripts (\n"
        "  extraction_state TEXT "
        "CHECK (extraction_state IN ('pending', 'extracted'))\n"
        ");"
    )

    def test_file_level_optout_suppresses(self, tmp_path: Path):
        route = """
        # f9-allow-pydantic-literal-vs-check: legacy module pending
        # migration to typed Literal aliases in a later phase
        from pydantic import BaseModel

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: str
        """
        findings = _run(
            tmp_path,
            migrations_sql=(self._SQL,),
            routes={"transcripts.py": route},
        )
        assert findings == [], (
            "Valid file-level opt-out must suppress all findings:\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_file_level_malformed_optout_flagged_and_underlying_reported(
        self, tmp_path: Path,
    ):
        """A too-short file-level reason -> *-malformed-optout AND the
        underlying str-typed finding still fires."""
        route = """
        # f9-allow-pydantic-literal-vs-check: short
        from pydantic import BaseModel

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: str
        """
        findings = _run(
            tmp_path,
            migrations_sql=(self._SQL,),
            routes={"transcripts.py": route},
        )
        rules = {f.rule for f in findings}
        assert "pydantic-literal-vs-check-malformed-optout" in rules, (
            f"Expected a malformed-optout finding, got rules {rules}"
        )
        assert "pydantic-literal-vs-check" in rules, (
            f"Malformed opt-out must NOT exempt — the underlying "
            f"finding should still fire. Got rules {rules}"
        )

    def test_per_line_optout_suppresses(self, tmp_path: Path):
        route = """
        from pydantic import BaseModel

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: str  # f9-noqa: pydantic-literal-vs-check legacy column kept str pending migration 050
        """
        findings = _run(
            tmp_path,
            migrations_sql=(self._SQL,),
            routes={"transcripts.py": route},
        )
        assert findings == [], (
            "Valid per-line opt-out must suppress the finding:\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_per_line_malformed_optout_flagged_and_underlying_reported(
        self, tmp_path: Path,
    ):
        route = """
        from pydantic import BaseModel

        class VoiceTranscriptResponse(BaseModel):
            extraction_state: str  # f9-noqa: pydantic-literal-vs-check ok
        """
        findings = _run(
            tmp_path,
            migrations_sql=(self._SQL,),
            routes={"transcripts.py": route},
        )
        rules = {f.rule for f in findings}
        assert "pydantic-literal-vs-check-malformed-optout" in rules, (
            f"Expected a per-line malformed-optout finding, got rules "
            f"{rules}"
        )
        assert "pydantic-literal-vs-check" in rules, (
            f"Malformed per-line opt-out must NOT exempt — underlying "
            f"finding should still fire. Got rules {rules}"
        )


# ---------------------------------------------------------------------
# Class 6 — TestThreeRoleColumnDisambiguation  (THE CLOSURE GATE)
# ---------------------------------------------------------------------


class TestThreeRoleColumnDisambiguation:
    """Phase-closure gate: three tables each with a same-named ``role``
    column carrying a *different* CHECK value-set.

    Modelled on the three real ones:
      * fleet_bikes      {rental, demo, race, customer}
      * shop_members     {owner, tech, service_writer, apprentice}
      * work_order_photos{before, after, general, undecided}

    The rule must validate each model's ``role`` against ITS OWN
    table's CHECK set and must NOT cross-report.
    """

    _MIGRATIONS = (
        "CREATE TABLE fleet_bikes (\n"
        "  role TEXT CHECK (role IN "
        "('rental', 'demo', 'race', 'customer'))\n"
        ");",
        "CREATE TABLE shop_members (\n"
        "  role TEXT CHECK (role IN "
        "('owner', 'tech', 'service_writer', 'apprentice'))\n"
        ");",
        "CREATE TABLE work_order_photos (\n"
        "  role TEXT CHECK (role IN "
        "('before', 'after', 'general', 'undecided'))\n"
        ");",
    )

    def test_each_model_validates_against_its_own_table(
        self, tmp_path: Path,
    ):
        """Three correct models (one per table), each with a
        ``# f9-table:`` marker and a Literal matching ITS table's set
        -> 0 findings. Proves no cross-report against another table's
        ``role`` set."""
        route = """
        from pydantic import BaseModel
        from typing import Literal

        # f9-table: fleet_bikes
        class FleetBikeResponse(BaseModel):
            role: Literal["rental", "demo", "race", "customer"]

        # f9-table: shop_members
        class ShopMemberResponse(BaseModel):
            role: Literal["owner", "tech", "service_writer", "apprentice"]

        # f9-table: work_order_photos
        class WorkOrderPhotoResponse(BaseModel):
            role: Literal["before", "after", "general", "undecided"]
        """
        findings = _run(
            tmp_path,
            migrations_sql=self._MIGRATIONS,
            routes={"mixed.py": route},
        )
        assert findings == [], (
            "Each model's role must validate against its own table's "
            "CHECK set with zero cross-report:\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_correct_on_A_drifted_on_B_yields_exactly_one_finding_on_B(
        self, tmp_path: Path,
    ):
        """A correct field on table A and a drifted field on table B
        in one run -> exactly one finding, on B. This is the explicit
        no-cross-report assertion the closure gate requires."""
        route = """
        from pydantic import BaseModel
        from typing import Literal

        # f9-table: fleet_bikes
        class FleetBikeResponse(BaseModel):
            role: Literal["rental", "demo", "race", "customer"]

        # f9-table: shop_members
        class ShopMemberResponse(BaseModel):
            role: Literal["owner", "tech", "service_writer"]
        """
        findings = _run(
            tmp_path,
            migrations_sql=self._MIGRATIONS,
            routes={"mixed.py": route},
        )
        errors = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(errors) == 1, (
            f"Expected exactly one finding (on the drifted "
            f"shop_members model), got {len(errors)}:\n"
            + "\n".join(f.format() for f in findings)
        )
        # The single finding must name ShopMemberResponse / shop_members,
        # NOT FleetBikeResponse — proving table-scoped, no cross-wire.
        msg = errors[0].message
        assert "ShopMemberResponse" in msg, (
            f"Finding should be on ShopMemberResponse, got: {msg}"
        )
        assert "shop_members" in msg
        assert "FleetBikeResponse" not in msg, (
            f"Finding must NOT cross-report the correct FleetBike "
            f"model: {msg}"
        )

    def test_class_name_convention_resolves_table_without_marker(
        self, tmp_path: Path,
    ):
        """Absent a ``# f9-table:`` marker, the class-name convention
        (strip Response, snake_case, pluralize) resolves the table when
        the result is one of the colliding tables."""
        route = """
        from pydantic import BaseModel
        from typing import Literal

        class WorkOrderPhotoResponse(BaseModel):
            role: Literal["before", "after", "general", "undecided"]
        """
        findings = _run(
            tmp_path,
            migrations_sql=self._MIGRATIONS,
            routes={"photos.py": route},
        )
        # WorkOrderPhotoResponse -> work_order_photos (convention);
        # the Literal matches that table's set -> 0 findings.
        assert findings == [], (
            "Class-name convention should resolve "
            "WorkOrderPhotoResponse -> work_order_photos and validate "
            "cleanly:\n"
            + "\n".join(f.format() for f in findings)
        )


# ---------------------------------------------------------------------
# Class 7 — TestAmbiguousCollision
# ---------------------------------------------------------------------


class TestNegativeFixturePositiveResolution:
    """v1.0.2 PHASE-CLOSURE GATE — positive-resolution-required matching.

    A field whose name coincides with a DB CHECK column must NOT be
    flagged unless the field's model positively resolves to a table
    that actually carries that CHECK. This is the ``HealthStatus.status``
    case the v1.0.1 retroactive sweep surfaced — the rule over-fired on
    name-coincidence against unrelated tables. v1.0.2 removed the
    ``pydantic-literal-vs-check-ambiguous`` finding entirely: an
    unresolved / non-CHECK-bearing model is silently skipped, never
    false-flagged. These tests are a closure gate, not optional
    coverage."""

    _MIGRATIONS = (
        "CREATE TABLE work_orders (\n"
        "  status TEXT CHECK (status IN ('open', 'closed', 'cancelled'))\n"
        ");",
        "CREATE TABLE issues (\n"
        "  status TEXT CHECK (status IN ('open', 'resolved'))\n"
        ");",
    )

    def test_healthstatus_shaped_model_yields_zero_findings(
        self, tmp_path: Path,
    ):
        """THE load-bearing negative case. A health-check response
        model ``HealthStatus`` has a ``status`` field. ``status`` IS a
        CHECK column on real tables (work_orders, issues), but
        ``HealthStatus`` maps to NO DB table. Expect ZERO findings —
        under v1.0.1's name-match this over-fired; v1.0.2 must not."""
        route = """
        from pydantic import BaseModel
        from typing import Optional

        class HealthStatus(BaseModel):
            status: str
            detail: Optional[str] = None
        """
        findings = _run(
            tmp_path,
            migrations_sql=self._MIGRATIONS,
            routes={"meta.py": route},
        )
        assert findings == [], (
            "A model that resolves to no CHECK-bearing table must "
            "produce ZERO findings — a field name coinciding with a "
            "DB CHECK column is NOT sufficient to flag it (v1.0.2 "
            "positive-resolution-required matching):\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_unresolved_colliding_column_yields_zero_findings(
        self, tmp_path: Path,
    ):
        """A colliding-column model with no ``# f9-table:`` marker
        whose class-name convention names no CHECK-bearing table ->
        ZERO findings. v1.0.2 removed the ``ambiguous`` finding; the
        rule never guesses and never false-flags."""
        migrations = (
            "CREATE TABLE fleet_bikes (\n"
            "  role TEXT CHECK (role IN ('rental', 'demo'))\n"
            ");",
            "CREATE TABLE shop_members (\n"
            "  role TEXT CHECK (role IN ('owner', 'tech'))\n"
            ");",
        )
        route = """
        from pydantic import BaseModel
        from typing import Literal

        class ThingDTO(BaseModel):
            role: Literal["rental", "demo"]
        """
        findings = _run(
            tmp_path,
            migrations_sql=migrations,
            routes={"thing.py": route},
        )
        assert findings == [], (
            "An unresolved colliding-column model must produce ZERO "
            "findings under v1.0.2 (no ambiguous finding, no guess):\n"
            + "\n".join(f.format() for f in findings)
        )

    def test_marker_resolves_and_then_rule_does_flag(
        self, tmp_path: Path,
    ):
        """Counter-check: WITH an authoritative ``# f9-table:`` marker
        the same shape DOES resolve and the rule fires — proving the
        negative cases above are positive-resolution-gated, not the
        rule going globally silent."""
        migrations = (
            "CREATE TABLE work_orders (\n"
            "  status TEXT CHECK (status IN ('open', 'closed'))\n"
            ");",
        )
        route = """
        from pydantic import BaseModel

        # f9-table: work_orders
        class HealthStatus(BaseModel):
            status: str
        """
        findings = _run(
            tmp_path,
            migrations_sql=migrations,
            routes={"meta.py": route},
        )
        flagged = [
            f for f in findings if f.rule == "pydantic-literal-vs-check"
        ]
        assert len(flagged) == 1, (
            "With an authoritative # f9-table marker the model "
            "resolves and the str field IS flagged — confirming the "
            "negative cases are resolution-gated, not the rule "
            "silently disabled:\n"
            + "\n".join(f.format() for f in findings)
        )


# ---------------------------------------------------------------------
# Class 8 — TestCheckParsing  (direct (table, column) parser coverage)
# ---------------------------------------------------------------------


class TestCheckParsing:
    """Direct coverage of the (table, column) CHECK-constraint parser."""

    def test_numeric_check_is_skipped(self, tmp_path: Path):
        """``CHECK (col IN (0, 1))`` has no quoted strings -> skipped
        (not a Pydantic-Literal-of-str surface)."""
        sql = (
            "CREATE TABLE flags (\n"
            "  enabled INTEGER CHECK (enabled IN (0, 1))\n"
            ");"
        )
        mig = tmp_path / "migrations.py"
        _write(mig, _migrations_module(sql))
        check_map = _parse_check_constraints(mig)
        assert ("flags", "enabled") not in check_map, (
            f"Numeric CHECK should be skipped, got: {check_map}"
        )

    def test_string_check_keyed_by_table_and_column(
        self, tmp_path: Path,
    ):
        sql = (
            "CREATE TABLE shop_members (\n"
            "  role TEXT CHECK (role IN ('owner', 'tech'))\n"
            ");"
        )
        mig = tmp_path / "migrations.py"
        _write(mig, _migrations_module(sql))
        check_map = _parse_check_constraints(mig)
        assert check_map.get(("shop_members", "role")) == frozenset(
            {"owner", "tech"}
        ), f"Expected (shop_members, role) keyed set, got: {check_map}"

    def test_later_migration_overrides_earlier(self, tmp_path: Path):
        """When the same (table, column) appears in two migrations, the
        later one (higher lineno) wins."""
        early = (
            "CREATE TABLE shop_members (\n"
            "  role TEXT CHECK (role IN ('owner', 'tech'))\n"
            ");"
        )
        late = (
            "ALTER TABLE shop_members ADD COLUMN role2 TEXT;\n"
            "CREATE TABLE shop_members (\n"
            "  role TEXT CHECK (role IN "
            "('owner', 'tech', 'service_writer'))\n"
            ");"
        )
        mig = tmp_path / "migrations.py"
        _write(mig, _migrations_module(early, late))
        check_map = _parse_check_constraints(mig)
        assert check_map[("shop_members", "role")] == frozenset(
            {"owner", "tech", "service_writer"}
        ), (
            f"Later migration should override; got: "
            f"{check_map[('shop_members', 'role')]}"
        )

    def test_rollback_sql_is_ignored(self, tmp_path: Path):
        """The parser scans only upgrade_sql; a CHECK present only in
        rollback_sql must NOT appear in the map. ``_migrations_module``
        writes a CHECK-free rollback, so a CHECK key here can only come
        from upgrade_sql — assert the no-upgrade-CHECK case yields an
        empty map."""
        sql = "CREATE TABLE plain (id INTEGER PRIMARY KEY);"
        mig = tmp_path / "migrations.py"
        # Hand-build a migration whose rollback_sql carries a CHECK.
        body = (
            "class Migration:\n"
            "    def __init__(self, version, upgrade_sql, "
            "rollback_sql=''):\n"
            "        self.version = version\n"
            "        self.upgrade_sql = upgrade_sql\n"
            "        self.rollback_sql = rollback_sql\n"
            "\n"
            "MIGRATIONS = [\n"
            "    Migration(\n"
            "        version=1,\n"
            f'        upgrade_sql="""{sql}""",\n'
            '        rollback_sql="""CREATE TABLE rb '
            "(role TEXT CHECK (role IN ('a', 'b')));\"\"\",\n"
            "    ),\n"
            "]\n"
        )
        _write(mig, body)
        check_map = _parse_check_constraints(mig)
        assert ("rb", "role") not in check_map, (
            f"rollback_sql CHECK must be ignored, got: {check_map}"
        )

    def test_multiline_check_shape_parsed(self, tmp_path: Path):
        """A multi-line ``CHECK (...)`` (column-def on one line, CHECK
        on the next) is parsed thanks to the DOTALL regex."""
        sql = (
            "CREATE TABLE voice_transcripts (\n"
            "  extraction_state TEXT NOT NULL DEFAULT 'pending'\n"
            "    CHECK (extraction_state IN (\n"
            "      'pending',\n"
            "      'extracting',\n"
            "      'extracted'\n"
            "    ))\n"
            ");"
        )
        mig = tmp_path / "migrations.py"
        _write(mig, _migrations_module(sql))
        check_map = _parse_check_constraints(mig)
        assert check_map.get(
            ("voice_transcripts", "extraction_state")
        ) == frozenset({"pending", "extracting", "extracted"}), (
            f"Multi-line CHECK should parse, got: {check_map}"
        )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
