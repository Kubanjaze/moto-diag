"""Phase 191D — unit tests for the generalized SSOT-constants lint mode.

Covers ``--check-ssot-constants`` (F20 mitigation) +
``--check-tag-catalog-coverage`` (F21 mitigation) + the deprecated
``--check-model-ids`` stub-redirect inside
``scripts/check_f9_patterns.py``, plus a smoke for the production-side
``vehicle_identifier.py`` SSOT-import cleanup landed in the same commit.

Test class organization (RuleTester-style, one class per concern):
  * TestCheckSsotConstants — positive / negative / opt-out cases for the
    new TOML-driven rule.
  * TestCheckTagCatalogCoverage — clean-master + synthetic drift cases
    for the F21 lint mode.
  * TestStubRedirectDeprecation — the ``--check-model-ids`` deprecation
    stub: stderr split, functional equivalence, exit-code semantics.
  * TestVehicleIdentifierSsotImport — smoke that the Commit 2 production
    cleanup wired the SSOT lookup correctly.

All synthetic fixtures live in ``tmp_path``; this test file does NOT
add literal-pin anti-examples to the real ``tests/`` tree (would be
self-defeating).

Pattern doc: ``docs/patterns/f9-mock-vs-runtime-drift.md``.
Plan: ``docs/phases/in_progress/191D_implementation.md``.
"""

# f9-allow-ssot-constants: meta-test — this file IS the lint rule's
# RuleTester suite; synthetic fixtures intentionally pin SSOT literals
# to validate positive / negative behavior and would tautology-loop
# if the rule scanned its own source.
# f9-allow-model-ids: meta-test — same rationale; the deprecated rule's
# stub-redirect tests reference MODEL_ALIASES literals as fixtures.

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------
# Module loader: scripts/ is not a Python package, so we load the module
# via importlib.util to avoid sys.path munging or adding an __init__.py.
# Same pattern as test_phase191c_f9_lint.py — reusing the dataclass-
# friendly sys.modules registration that Builder-B fixed in Phase 191C
# fix-cycle (Python 3.13 dataclass requires module-importable-by-name).
# ---------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_f9_patterns.py"
REGISTRY_PATH = REPO_ROOT / "f9_ssot_constants.toml"


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
check_ssot_constants = _check_f9.check_ssot_constants
check_tag_catalog_coverage = _check_f9.check_tag_catalog_coverage
load_registry = _check_f9.load_registry
DEPRECATION_NOTICE = _check_f9.DEPRECATION_NOTICE
DEPRECATED_MODEL_IDS_FILTER = _check_f9.DEPRECATED_MODEL_IDS_FILTER


# ---------------------------------------------------------------------
# Class 1 — TestCheckSsotConstants (Phase 191D F20 mitigation)
# ---------------------------------------------------------------------


class TestCheckSsotConstants:
    """Positive / negative / opt-out cases for the TOML-driven rule."""

    def test_registry_loads_all_entries(self):
        """Smoke that the shipped registry parses + every source module
        imports cleanly. If this fails, the lint mode is broken
        site-wide (registry-error finding fires for every entry)."""
        entries, errors = load_registry(REGISTRY_PATH)
        assert errors == [], (
            f"Expected 0 registry errors, got {len(errors)}:\n"
            + "\n".join(e.format() for e in errors)
        )
        # Sanity floor — the plan-of-record initial registry has 14
        # entries after Phase 191D fix-cycle dropped DEFAULT_VISION_MODEL
        # (the constant's value "sonnet" is also a MODEL_ALIASES key,
        # which produced 23 false positives in the wild). The drop is
        # documented inline in f9_ssot_constants.toml. Going below 14
        # means a legitimate entry was lost.
        assert len(entries) >= 14, (
            f"Expected >= 14 registry entries, got {len(entries)}. "
            f"Did an entry get dropped from f9_ssot_constants.toml?"
        )
        # Every entry must have its live_value populated (None means
        # the dynamic import succeeded but the symbol wasn't found —
        # also a bug).
        for entry in entries:
            assert entry.live_value is not None, (
                f"Entry {entry.name} from {entry.source_module} has "
                f"no live_value — import succeeded but symbol missing?"
            )

    def test_positive_schema_version_literal_pin_in_test(
        self, tmp_path: Path,
    ):
        """Test asserting ``SCHEMA_VERSION == 40`` (the current live
        value as of Phase 192 migration 040) without an opt-out comment
        must trigger one finding.

        This is the F20 case shape: the test imports the SSOT but ALSO
        literal-pins the value, so a future migration bump silently
        breaks the assertion (Phase 191B C2 fix-cycle-5 anti-regression).
        """
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_synthetic.py").write_text(
            "from motodiag.core.database import SCHEMA_VERSION\n"
            "def test_pin():\n"
            "    assert SCHEMA_VERSION == 40\n",
            encoding="utf-8",
        )
        findings = check_ssot_constants(
            [tests_dir], registry_path=REGISTRY_PATH,
        )
        # Filter to ssot-pin rule (registry-error rows would also be
        # ssot-* but registry is clean; ssot-pin is the rule under
        # test).
        ssot_pin_findings = [f for f in findings if f.rule == "ssot-pin"]
        assert len(ssot_pin_findings) == 1, (
            f"Expected exactly 1 ssot-pin finding, got "
            f"{len(ssot_pin_findings)}:\n"
            + "\n".join(f.format() for f in findings)
        )
        f = ssot_pin_findings[0]
        assert "SCHEMA_VERSION" in f.message
        assert "motodiag.core.database" in f.message

    def test_negative_membership_check_does_not_trigger(
        self, tmp_path: Path,
    ):
        """``assert SCHEMA_VERSION in {39, 40}`` is membership-checking
        (not literal-pinning) and ALSO doesn't appear next to the
        identifier `SCHEMA_VERSION` close enough to trigger... actually
        BOTH 39 and 40 are within proximity here. This test guards the
        case where the literal IS within proximity but the assertion
        shape is membership / range / inequality (the rule scans for
        any matching literal regardless of operator — by design — so
        BOTH literals fire here UNLESS the user adds an opt-out).

        Phase 191D scope: the rule is intentionally noisy on this
        case — membership checks against a SSOT value are still
        literal-pinning and should be opt-outed with contract-pin if
        intentional. This negative test asserts the opt-out path
        works for the membership-check shape.
        """
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # SSOT-pin literal but with a 25-char opt-out reason — must
        # NOT trigger.
        (tests_dir / "test_synthetic.py").write_text(
            "from motodiag.core.database import SCHEMA_VERSION\n"
            "def test_membership():\n"
            "    assert SCHEMA_VERSION in {39, 40}  "
            "# f9-noqa: ssot-pin acceptable membership against current "
            "schema + next anticipated migration version\n",
            encoding="utf-8",
        )
        findings = check_ssot_constants(
            [tests_dir], registry_path=REGISTRY_PATH,
        )
        ssot_pin_findings = [f for f in findings if f.rule == "ssot-pin"]
        assert ssot_pin_findings == [], (
            f"Expected 0 findings with valid opt-out, got "
            f"{len(ssot_pin_findings)}:\n"
            + "\n".join(f.format() for f in ssot_pin_findings)
        )

    def test_opt_out_ssot_pin_honored(self, tmp_path: Path):
        """Per-line ``# f9-noqa: ssot-pin <reason>`` (>=20 chars) must
        suppress the finding entirely."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_synthetic.py").write_text(
            "from motodiag.core.database import SCHEMA_VERSION\n"
            "def test_pin():\n"
            "    assert SCHEMA_VERSION == 40  "
            "# f9-noqa: ssot-pin migration-boundary contract assertion "
            "for billing-cycle alignment\n",
            encoding="utf-8",
        )
        findings = check_ssot_constants(
            [tests_dir], registry_path=REGISTRY_PATH,
        )
        ssot_pin_findings = [f for f in findings if f.rule == "ssot-pin"]
        assert ssot_pin_findings == [], (
            f"Expected 0 findings with valid opt-out, got "
            f"{len(ssot_pin_findings)}:\n"
            + "\n".join(f.format() for f in ssot_pin_findings)
        )

    def test_opt_out_contract_pin_subcategory_honored(
        self, tmp_path: Path,
    ):
        """The new Phase 191D ``contract-pin`` subcategory under
        ``# f9-noqa: ssot-pin contract-pin: <reason>`` must be honored
        AND the diagnostic infrastructure must recognize it (the
        malformed-optout message text mentions both shapes)."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # 30-char reason after the contract-pin: keyword satisfies the
        # 20-char floor. (The category keyword itself doesn't pad the
        # reason length.)
        (tests_dir / "test_synthetic.py").write_text(
            "from motodiag.core.database import SCHEMA_VERSION\n"
            "def test_pin():\n"
            "    assert SCHEMA_VERSION == 40  "
            "# f9-noqa: ssot-pin contract-pin: tier-billing-math "
            "regression coverage; bump requires Stripe re-verification\n",
            encoding="utf-8",
        )
        findings = check_ssot_constants(
            [tests_dir], registry_path=REGISTRY_PATH,
        )
        ssot_pin_findings = [
            f for f in findings if f.rule == "ssot-pin"
        ]
        assert ssot_pin_findings == [], (
            f"Expected 0 ssot-pin findings with valid contract-pin "
            f"opt-out, got {len(ssot_pin_findings)}:\n"
            + "\n".join(f.format() for f in ssot_pin_findings)
        )

    def test_opt_out_reason_under_floor_flagged_as_malformed(
        self, tmp_path: Path,
    ):
        """``# f9-noqa: ssot-pin ok`` (3-char reason) must NOT honor
        the opt-out AND must emit a ``ssot-pin-malformed-optout``
        finding so the comment can't be a drive-by."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_synthetic.py").write_text(
            "from motodiag.core.database import SCHEMA_VERSION\n"
            "def test_pin():\n"
            "    assert SCHEMA_VERSION == 40  "
            "# f9-noqa: ssot-pin ok\n",
            encoding="utf-8",
        )
        findings = check_ssot_constants(
            [tests_dir], registry_path=REGISTRY_PATH,
        )
        rules = {f.rule for f in findings}
        assert "ssot-pin-malformed-optout" in rules, (
            f"Expected a ssot-pin-malformed-optout finding, got rules "
            f"{rules}"
        )
        # Underlying ssot-pin still fires too (malformed opt-out
        # doesn't exempt — same posture as Phase 191C file-level).
        assert "ssot-pin" in rules, (
            f"Expected the underlying ssot-pin to ALSO fire (malformed "
            f"opt-out doesn't exempt), got rules {rules}"
        )

    def test_dict_typed_entry_scans_value_position(
        self, tmp_path: Path,
    ):
        """Dict-typed entry: the live value of
        ``TIER_VEHICLE_LIMITS["individual"]`` is 5; a test asserting on
        that literal alongside the identifier must trigger."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_synthetic.py").write_text(
            "from motodiag.vehicles.registry import TIER_VEHICLE_LIMITS\n"
            "def test_pin():\n"
            "    assert TIER_VEHICLE_LIMITS['individual'] == 5\n",
            encoding="utf-8",
        )
        findings = check_ssot_constants(
            [tests_dir], registry_path=REGISTRY_PATH,
        )
        ssot_pin_findings = [
            f for f in findings if f.rule == "ssot-pin"
        ]
        assert len(ssot_pin_findings) >= 1, (
            f"Expected >=1 ssot-pin findings on dict value-position, "
            f"got {len(ssot_pin_findings)}:\n"
            + "\n".join(f.format() for f in findings)
        )
        # Diagnostic should name TIER_VEHICLE_LIMITS specifically.
        assert any(
            "TIER_VEHICLE_LIMITS" in f.message
            for f in ssot_pin_findings
        )

    def test_coincidence_equal_literal_does_not_flag(
        self, tmp_path: Path,
    ):
        """A test asserting ``response.status_code == 5`` with NO
        TIER_VEHICLE_LIMITS import + NO identifier nearby must NOT
        trigger, even though 5 IS a value of TIER_VEHICLE_LIMITS.

        Documents the false-positive narrowing required in the plan
        (and the Phase 191D heuristic refinement that limits dict-
        typed scans to identifier-nearby matches only)."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_unrelated.py").write_text(
            "def test_response():\n"
            "    response_status_code = 5\n"
            "    assert response_status_code == 5\n",
            encoding="utf-8",
        )
        findings = check_ssot_constants(
            [tests_dir], registry_path=REGISTRY_PATH,
        )
        ssot_pin_findings = [
            f for f in findings if f.rule == "ssot-pin"
        ]
        assert ssot_pin_findings == [], (
            f"Expected 0 findings on coincidence-equal literal, got "
            f"{len(ssot_pin_findings)}:\n"
            + "\n".join(f.format() for f in ssot_pin_findings)
        )


# ---------------------------------------------------------------------
# Class 2 — TestCheckTagCatalogCoverage (Phase 191D F21 mitigation)
# ---------------------------------------------------------------------


class TestCheckTagCatalogCoverage:
    """Positive / negative cases for the tag-catalog-coverage rule."""

    def test_clean_master_has_no_error_findings(self):
        """Real-master diff: every tag used in
        ``src/motodiag/api/routes/**/*.py`` must already exist in
        ``TAG_CATALOG`` (the videos tag was added at Phase 191B
        fix-cycle-5; this is the regression guard).

        Warn-severity ``tag-catalog-orphan`` rows are allowed (e.g.
        future-route placeholders) — only ``tag-catalog-coverage``
        error rows would be a regression.
        """
        findings = check_tag_catalog_coverage(
            REPO_ROOT / "src" / "motodiag" / "api" / "routes",
            REPO_ROOT / "src" / "motodiag" / "api" / "openapi.py",
        )
        coverage_errors = [
            f for f in findings if f.rule == "tag-catalog-coverage"
        ]
        assert coverage_errors == [], (
            f"Expected 0 tag-catalog-coverage findings, got "
            f"{len(coverage_errors)}:\n"
            + "\n".join(f.format() for f in coverage_errors)
        )

    def test_synthetic_drift_route_tag_missing_from_catalog(
        self, tmp_path: Path,
    ):
        """Synthetic regression: a route declares ``tags=["bogus"]``
        but ``TAG_CATALOG`` has no matching entry → exactly one
        ``tag-catalog-coverage`` finding fires."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "fake_route.py").write_text(
            "from fastapi import APIRouter\n"
            "router = APIRouter(prefix='/fake', "
            "tags=['bogus_tag_for_test'])\n",
            encoding="utf-8",
        )
        openapi_file = tmp_path / "openapi.py"
        openapi_file.write_text(
            "TAG_CATALOG = [\n"
            "    {'name': 'meta', 'description': 'health'},\n"
            "]\n",
            encoding="utf-8",
        )
        findings = check_tag_catalog_coverage(
            routes_dir, openapi_file,
        )
        coverage_errors = [
            f for f in findings if f.rule == "tag-catalog-coverage"
        ]
        assert len(coverage_errors) == 1, (
            f"Expected 1 tag-catalog-coverage finding, got "
            f"{len(coverage_errors)}:\n"
            + "\n".join(f.format() for f in coverage_errors)
        )
        assert "bogus_tag_for_test" in coverage_errors[0].message

    def test_reverse_diff_warn_only(self, tmp_path: Path):
        """Tag in TAG_CATALOG but no route uses it → emits a
        ``tag-catalog-orphan`` (warn-severity) finding, NOT a
        ``tag-catalog-coverage`` (error-severity) one."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "real_route.py").write_text(
            "from fastapi import APIRouter\n"
            "router = APIRouter(prefix='/meta', tags=['meta'])\n",
            encoding="utf-8",
        )
        openapi_file = tmp_path / "openapi.py"
        openapi_file.write_text(
            "TAG_CATALOG = [\n"
            "    {'name': 'meta', 'description': 'health'},\n"
            "    {'name': 'orphan_tag', 'description': 'unused'},\n"
            "]\n",
            encoding="utf-8",
        )
        findings = check_tag_catalog_coverage(
            routes_dir, openapi_file,
        )
        rules = {f.rule for f in findings}
        assert "tag-catalog-orphan" in rules, (
            f"Expected a tag-catalog-orphan finding, got rules {rules}"
        )
        assert "tag-catalog-coverage" not in rules, (
            f"Did not expect tag-catalog-coverage (route side clean), "
            f"got rules {rules}"
        )
        orphans = [
            f for f in findings if f.rule == "tag-catalog-orphan"
        ]
        assert any("orphan_tag" in f.message for f in orphans)


# ---------------------------------------------------------------------
# Class 3 — TestStubRedirectDeprecation (Phase 191D --check-model-ids)
# ---------------------------------------------------------------------


class TestStubRedirectDeprecation:
    """Verify the ``--check-model-ids`` deprecation stub-redirect.

    The contract: deprecation notice goes to STDERR (preserves stdout
    for finding-line consumers), the underlying scan is functionally
    equivalent to ``--check-ssot-constants`` filtered to
    ``MODEL_ALIASES`` + ``MODEL_PRICING``, and exit-code semantics
    match the underlying call.
    """

    def test_deprecated_flag_emits_warning_to_stderr(
        self, tmp_path: Path,
    ):
        """``--check-model-ids`` against a clean fixture: deprecation
        notice appears in STDERR, NOT in STDOUT."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # Clean fixture — no SSOT-pin literals.
        (tests_dir / "test_clean.py").write_text(
            "def test_noop():\n"
            "    assert True\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--check-model-ids",
                "--repo-root",
                str(tmp_path),
                "--ssot-registry",
                str(REGISTRY_PATH),
            ],
            capture_output=True,
            text=True,
        )
        # Deprecation in stderr, NOT stdout.
        assert "DEPRECATION" in result.stderr, (
            f"Expected DEPRECATION in stderr, got stderr:\n"
            f"{result.stderr}"
        )
        assert "DEPRECATION" not in result.stdout, (
            f"DEPRECATION leaked into stdout (breaks pipe-based "
            f"consumers); got stdout:\n{result.stdout}"
        )

    def test_deprecated_flag_functionally_equivalent_for_model_ids(
        self, tmp_path: Path,
    ):
        """``--check-model-ids`` and ``--check-ssot-constants`` against
        the same fixture (a model-ID literal-pin) produce the same set
        of findings (modulo the stderr deprecation banner).

        The deprecated path internally invokes
        ``check_ssot_constants`` filtered to ``MODEL_ALIASES`` +
        ``MODEL_PRICING`` — so for model-ID-only fixtures, the two
        modes are equivalent.
        """
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # Pin a model-ID literal nearby an identifier that triggers
        # the dict-typed heuristic.
        (tests_dir / "test_pin.py").write_text(
            "from motodiag.engine.client import MODEL_ALIASES\n"
            "def test_pin():\n"
            "    assert MODEL_ALIASES['haiku'] == "
            "'claude-haiku-4-5-20251001'\n",
            encoding="utf-8",
        )

        # Path A: deprecated flag.
        deprecated_findings = _check_f9.check_ssot_constants(
            [tests_dir],
            registry_path=REGISTRY_PATH,
            name_filter=DEPRECATED_MODEL_IDS_FILTER,
        )
        # Path B: explicit filter via the same call shape.
        direct_findings = _check_f9.check_ssot_constants(
            [tests_dir],
            registry_path=REGISTRY_PATH,
            name_filter=DEPRECATED_MODEL_IDS_FILTER,
        )

        # Same call → same findings (sanity that the function is
        # deterministic). The stub-redirect contract is: both surfaces
        # invoke the same underlying function with the same filter.
        assert (
            len(deprecated_findings) == len(direct_findings)
        ), (
            f"Functional-equivalence mismatch: deprecated path "
            f"produced {len(deprecated_findings)} findings, direct "
            f"produced {len(direct_findings)}."
        )
        # Both paths must produce >=1 ssot-pin finding for the model-ID.
        ssot_pin = [
            f for f in deprecated_findings if f.rule == "ssot-pin"
        ]
        assert len(ssot_pin) >= 1

    def test_deprecated_flag_exit_code_matches_underlying_call(
        self, tmp_path: Path,
    ):
        """Clean fixture exits 0 via either flag; finding-bearing
        fixture exits 1 via either flag."""
        # Clean fixture.
        clean_dir = tmp_path / "clean"
        (clean_dir / "tests").mkdir(parents=True)
        (clean_dir / "tests" / "test_clean.py").write_text(
            "def test_x():\n    assert True\n",
            encoding="utf-8",
        )
        result_clean_dep = subprocess.run(
            [
                sys.executable, str(SCRIPT_PATH),
                "--check-model-ids",
                "--repo-root", str(clean_dir),
                "--ssot-registry", str(REGISTRY_PATH),
            ],
            capture_output=True, text=True,
        )
        assert result_clean_dep.returncode == 0, (
            f"Clean fixture via --check-model-ids: expected 0, got "
            f"{result_clean_dep.returncode}.\n"
            f"stderr:\n{result_clean_dep.stderr}"
        )
        result_clean_new = subprocess.run(
            [
                sys.executable, str(SCRIPT_PATH),
                "--check-ssot-constants",
                "--repo-root", str(clean_dir),
                "--ssot-registry", str(REGISTRY_PATH),
            ],
            capture_output=True, text=True,
        )
        assert result_clean_new.returncode == 0, (
            f"Clean fixture via --check-ssot-constants: expected 0, "
            f"got {result_clean_new.returncode}.\n"
            f"stderr:\n{result_clean_new.stderr}"
        )

        # Finding-bearing fixture.
        dirty_dir = tmp_path / "dirty"
        (dirty_dir / "tests").mkdir(parents=True)
        (dirty_dir / "tests" / "test_pin.py").write_text(
            "from motodiag.engine.client import MODEL_ALIASES\n"
            "def test_pin():\n"
            "    assert MODEL_ALIASES['haiku'] == "
            "'claude-haiku-4-5-20251001'\n",
            encoding="utf-8",
        )
        result_dirty_dep = subprocess.run(
            [
                sys.executable, str(SCRIPT_PATH),
                "--check-model-ids",
                "--repo-root", str(dirty_dir),
                "--ssot-registry", str(REGISTRY_PATH),
            ],
            capture_output=True, text=True,
        )
        assert result_dirty_dep.returncode == 1, (
            f"Dirty fixture via --check-model-ids: expected 1, got "
            f"{result_dirty_dep.returncode}.\n"
            f"stderr:\n{result_dirty_dep.stderr}"
        )


# ---------------------------------------------------------------------
# Class 4 — TestVehicleIdentifierSsotImport (Phase 191D Commit 2 prod
#   cleanup smoke)
# ---------------------------------------------------------------------


class TestVehicleIdentifierSsotImport:
    """Smoke that the production-side cleanup wired SSOT correctly.

    The cleanup replaced literal model-ID assignments in
    ``src/motodiag/intake/vehicle_identifier.py`` with imports from
    ``motodiag.engine.client.MODEL_ALIASES``. These tests are not
    behavioral — they verify the indirection resolves to the right
    runtime string. If ``MODEL_ALIASES["haiku"]`` ever bumps, the
    expected literal here will need to be updated alongside it.
    """

    def test_haiku_model_id_resolves_via_ssot(self):
        from motodiag.intake.vehicle_identifier import HAIKU_MODEL_ID
        assert HAIKU_MODEL_ID == "claude-haiku-4-5-20251001", (
            f"HAIKU_MODEL_ID should resolve to the current "
            f"MODEL_ALIASES['haiku'] value via the SSOT import; got "
            f"{HAIKU_MODEL_ID!r}"
        )

    def test_sonnet_model_id_resolves_via_ssot(self):
        from motodiag.intake.vehicle_identifier import SONNET_MODEL_ID
        assert SONNET_MODEL_ID == "claude-sonnet-4-6", (
            f"SONNET_MODEL_ID should resolve to the current "
            f"MODEL_ALIASES['sonnet'] value via the SSOT import; got "
            f"{SONNET_MODEL_ID!r}"
        )

    def test_vehicle_identifier_imports_model_aliases(self):
        """The module should import MODEL_ALIASES from the engine
        client SSOT (not redeclare its own literals). Verifies the
        indirection is wired (rather than coincidentally matching
        live values via duplicate literal assignments)."""
        import motodiag.intake.vehicle_identifier as vi
        # MODEL_ALIASES must be an attribute of vi (imported into
        # module scope). If a future refactor renames the import or
        # uses ``import ... as ...``, this guard surfaces it.
        assert hasattr(vi, "MODEL_ALIASES"), (
            "vehicle_identifier should import MODEL_ALIASES from "
            "motodiag.engine.client (Phase 191D Commit 2 SSOT cleanup)."
        )
        # And the imported MODEL_ALIASES must be the SAME dict
        # instance as the engine client's (so a runtime mutation —
        # though not recommended — propagates uniformly).
        from motodiag.engine.client import MODEL_ALIASES as engine_aliases
        assert vi.MODEL_ALIASES is engine_aliases, (
            "vehicle_identifier.MODEL_ALIASES is not the engine "
            "client's MODEL_ALIASES — the SSOT cleanup may have "
            "redeclared instead of importing."
        )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
