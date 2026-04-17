"""Phase 128 — Knowledge Base Browser CLI tests.

Covers:
- `TestRepoTextSearch`: the new ``search_known_issues_text`` function —
  title / description / symptoms-JSON matching, case-insensitivity, empty
  query short-circuit, and limit clause.
- `TestCliList`: default listing, --make, --severity, --limit, empty-filter
  message path through ``motodiag kb list``.
- `TestCliShow`: happy detail render, missing-id error, sparse-field
  graceful rendering through ``motodiag kb show``.
- `TestCliSearch`: title/description/symptom matches and empty-result
  messaging through ``motodiag kb search``.
- `TestCliBySymptom`: happy path, empty-result, exercise of
  ``find_issues_by_symptom`` wiring.
- `TestCliByCode`: happy path, empty-result, and DTC force-uppercase
  behavior.
- `TestRegistration`: ``kb`` command group present, expected subcommand
  set complete.

All tests are DB-only. Zero AI calls, zero live tokens — Phase 08 repo
is pure SQL and the CLI layer is a thin click wrapper around those
functions.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db
from motodiag.knowledge.issues_repo import (
    add_known_issue,
    search_known_issues_text,
)


# --- Fixtures ---


@pytest.fixture
def db(tmp_path):
    """Bare DB fixture for repo-layer tests (no env patching)."""
    path = str(tmp_path / "phase128.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings at a temp DB so CliRunner sees it via the default path.

    Mirrors the Phase 125/127 pattern: env var + reset_settings around the
    test so get_settings() returns a Settings pointing at the temp DB.
    """
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase128_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    # Widen terminal so Rich tables don't word-wrap long titles across lines
    monkeypatch.setenv("COLUMNS", "200")
    reset_settings()
    yield path
    reset_settings()


def _seed_issues(db_path: str) -> dict[str, int]:
    """Seed a deterministic, filter-diverse set of 5 known issues.

    Returns a dict mapping slug -> issue_id so tests can assert exact IDs.

    Seeding covers:
      - Stator failure (Harley, high severity, P0562 DTC, multi-symptom)
      - Regulator/rectifier burnout (Honda, high, P0563, different symptom)
      - Worn clutch plates (Honda, medium, no DTC, clutch symptom)
      - Leaky fork seals (Yamaha, low, no DTC, suspension symptom)
      - Sparse entry (Kawasaki, medium, no parts/hours — covers empty-field
        rendering in `kb show`)
    """
    ids: dict[str, int] = {}
    ids["stator"] = add_known_issue(
        title="Stator failure",
        description=(
            "Stator windings break down from heat causing charging failure."
        ),
        make="Harley-Davidson",
        model="Sportster 1200",
        year_start=1999,
        year_end=2017,
        severity="high",
        symptoms=["battery not charging", "headlight dim or flickering"],
        dtc_codes=["P0562"],
        causes=["Stator winding insulation breakdown"],
        fix_procedure="Test stator AC output, replace if low.",
        parts_needed=["Stator assembly", "Stator gasket"],
        estimated_hours=3.5,
        db_path=db_path,
    )
    ids["regulator"] = add_known_issue(
        title="Regulator/rectifier burnout on highway",
        description=(
            "Shunt-style regulator overheats at sustained high RPM; boils "
            "the battery and browns out electrics."
        ),
        make="Honda",
        model="CBR929RR",
        year_start=2000,
        year_end=2001,
        severity="high",
        symptoms=[
            "battery boiling", "erratic charging", "won't start when hot",
        ],
        dtc_codes=["P0563"],
        causes=["Undersized heat sink", "Corroded ground"],
        fix_procedure="Upgrade to MOSFET unit from a later model.",
        parts_needed=["MOSFET regulator/rectifier", "Dielectric grease"],
        estimated_hours=1.5,
        db_path=db_path,
    )
    ids["clutch"] = add_known_issue(
        title="Worn clutch plates slipping under load",
        description=(
            "Fiber plates lose friction material after 30k miles; slipping "
            "in upper gears under throttle."
        ),
        make="Honda",
        model="CBR600RR",
        year_start=2003,
        year_end=2006,
        severity="medium",
        symptoms=["clutch slipping", "high RPM without acceleration"],
        dtc_codes=[],
        causes=["Plate wear", "Weak clutch springs"],
        fix_procedure="Replace fiber plates and springs as a set.",
        parts_needed=["Clutch plate kit", "Clutch springs"],
        estimated_hours=2.0,
        db_path=db_path,
    )
    ids["fork"] = add_known_issue(
        title="Leaky fork seals at low mileage",
        description=(
            "OEM seals weep at the dust wiper after the first winter's "
            "salt exposure."
        ),
        make="Yamaha",
        model="R6",
        year_start=2006,
        year_end=2010,
        severity="low",
        symptoms=["oil on fork lowers", "suspension sag"],
        dtc_codes=[],
        causes=["Pitting on fork tubes", "Debris cutting the seal lip"],
        fix_procedure="Replace fork seals, polish tubes.",
        parts_needed=["Fork seals", "Fork oil"],
        estimated_hours=2.5,
        db_path=db_path,
    )
    # Sparse entry — no parts, no estimated hours, empty symptoms/causes
    ids["sparse"] = add_known_issue(
        title="Occasional idle hang",
        description="Engine holds elevated idle briefly after hard braking.",
        make="Kawasaki",
        model="ZX-6R",
        year_start=2005,
        severity="medium",
        symptoms=[],
        dtc_codes=[],
        causes=[],
        fix_procedure=None,
        parts_needed=[],
        estimated_hours=None,
        db_path=db_path,
    )
    return ids


# =============================================================================
# TestRepoTextSearch — new search_known_issues_text function
# =============================================================================


class TestRepoTextSearch:
    def test_matches_title(self, db):
        ids = _seed_issues(db)
        results = search_known_issues_text("Stator", db_path=db)
        result_ids = [r["id"] for r in results]
        assert ids["stator"] in result_ids
        # Others don't have "stator" in title/description/symptoms
        assert ids["clutch"] not in result_ids
        assert ids["fork"] not in result_ids

    def test_matches_description(self, db):
        ids = _seed_issues(db)
        # "shunt" appears only in the regulator description
        results = search_known_issues_text("shunt", db_path=db)
        result_ids = [r["id"] for r in results]
        assert ids["regulator"] in result_ids
        assert ids["stator"] not in result_ids

    def test_matches_symptom_in_json(self, db):
        ids = _seed_issues(db)
        # "clutch slipping" lives only in the clutch entry's symptoms array
        results = search_known_issues_text("clutch slipping", db_path=db)
        result_ids = [r["id"] for r in results]
        assert ids["clutch"] in result_ids
        assert ids["stator"] not in result_ids
        assert ids["regulator"] not in result_ids

    def test_case_insensitive(self, db):
        ids = _seed_issues(db)
        # Lower-case query must still match the capitalized "Stator" title
        results_lower = search_known_issues_text("stator", db_path=db)
        results_upper = search_known_issues_text("STATOR", db_path=db)
        results_mixed = search_known_issues_text("StAtOr", db_path=db)
        lower_ids = [r["id"] for r in results_lower]
        upper_ids = [r["id"] for r in results_upper]
        mixed_ids = [r["id"] for r in results_mixed]
        assert ids["stator"] in lower_ids
        assert ids["stator"] in upper_ids
        assert ids["stator"] in mixed_ids
        # All three queries return the same row set (order / contents)
        assert lower_ids == upper_ids == mixed_ids

    def test_empty_query_returns_empty(self, db):
        _seed_issues(db)
        assert search_known_issues_text("", db_path=db) == []
        assert search_known_issues_text("   ", db_path=db) == []
        # Even with a limit, empty query short-circuits
        assert search_known_issues_text("", limit=10, db_path=db) == []

    def test_limit_respected(self, db):
        _seed_issues(db)
        # Broad-matching query — the word "the" appears in multiple
        # descriptions. Check that limit=2 trims the result set.
        all_results = search_known_issues_text("the", db_path=db)
        assert len(all_results) >= 2, (
            "Test assumes >=2 matches for 'the' across descriptions."
        )
        limited = search_known_issues_text("the", limit=2, db_path=db)
        assert len(limited) == 2


# =============================================================================
# TestCliList — `motodiag kb list`
# =============================================================================


class TestCliList:
    def test_default_list_renders(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "list"])
        assert r.exit_code == 0, r.output
        # Table header and at least one seeded title surface
        assert "Known Issues" in r.output
        assert "Stator" in r.output

    def test_make_filter(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "list", "--make", "Honda"])
        assert r.exit_code == 0, r.output
        # Honda entries visible
        assert "Honda" in r.output
        assert "CBR929RR" in r.output or "CBR600RR" in r.output
        # Harley and Yamaha rows excluded
        assert "Sportster" not in r.output
        assert "Yamaha" not in r.output

    def test_severity_filter(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "list", "--severity", "low"])
        assert r.exit_code == 0, r.output
        # Only the low-severity fork-seal entry should match
        assert "fork" in r.output.lower() or "Fork" in r.output
        assert "Stator" not in r.output
        assert "Regulator" not in r.output

    def test_limit_caps_rows(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "list", "--limit", "2"])
        assert r.exit_code == 0, r.output
        # Count how many seeded titles appear. With --limit 2, at most 2
        # rows should surface regardless of which filter ordering applies.
        title_hits = sum(
            t in r.output
            for t in [
                "Stator failure",
                "Regulator/rectifier",
                "Worn clutch",
                "Leaky fork",
                "Occasional idle",
            ]
        )
        assert title_hits <= 2, (
            f"Expected <=2 rows with --limit 2, got {title_hits}. "
            f"Output: {r.output}"
        )

    def test_empty_filter_message(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        # Filter for a make that isn't in the seed set
        r = runner.invoke(cli, ["kb", "list", "--make", "Ducati"])
        assert r.exit_code == 0, r.output
        assert "no issues match" in r.output.lower()


# =============================================================================
# TestCliShow — `motodiag kb show <id>`
# =============================================================================


class TestCliShow:
    def test_show_happy_path(self, cli_db):
        ids = _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "show", str(ids["stator"])])
        assert r.exit_code == 0, r.output
        # Title, description excerpt, fix procedure, and parts list render
        assert "Stator failure" in r.output
        assert "charging failure" in r.output
        assert "Test stator AC output" in r.output
        assert "Stator assembly" in r.output
        # Estimated labor callout present
        assert "3.5" in r.output

    def test_show_missing_id_errors(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "show", "99999"])
        assert r.exit_code != 0
        assert "not found" in r.output.lower()

    def test_show_sparse_entry_renders_gracefully(self, cli_db):
        ids = _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "show", str(ids["sparse"])])
        assert r.exit_code == 0, r.output
        # Still prints the title/description
        assert "Occasional idle hang" in r.output
        # Empty sections render the "none recorded" / "not recorded" markers
        # rather than crashing or printing "None"
        lower = r.output.lower()
        assert "none recorded" in lower or "not recorded" in lower
        # "None" literal is never printed unescaped
        assert "None\n" not in r.output


# =============================================================================
# TestCliSearch — `motodiag kb search <query>`
# =============================================================================


class TestCliSearch:
    def test_search_matches_title(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "search", "stator"])
        assert r.exit_code == 0, r.output
        assert "Stator failure" in r.output

    def test_search_matches_description(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        # "shunt" only appears in the regulator description
        r = runner.invoke(cli, ["kb", "search", "shunt"])
        assert r.exit_code == 0, r.output
        assert "Regulator/rectifier" in r.output
        assert "Stator failure" not in r.output

    def test_search_matches_symptom_in_json(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        # "clutch slipping" is only in the clutch entry's symptoms JSON
        r = runner.invoke(cli, ["kb", "search", "clutch slipping"])
        assert r.exit_code == 0, r.output
        assert "Worn clutch plates" in r.output
        assert "Stator" not in r.output

    def test_search_empty_result_message(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "search", "zzzzzz_nonexistent"])
        assert r.exit_code == 0, r.output
        assert "no issues mention" in r.output.lower()


# =============================================================================
# TestCliBySymptom — `motodiag kb by-symptom <symptom>`
# =============================================================================


class TestCliBySymptom:
    def test_by_symptom_happy_path(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "by-symptom", "battery not charging"])
        assert r.exit_code == 0, r.output
        assert "Stator failure" in r.output
        # Clutch and fork entries don't list that symptom
        assert "Worn clutch" not in r.output
        assert "Leaky fork" not in r.output

    def test_by_symptom_empty_result(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(
            cli, ["kb", "by-symptom", "engine fell out of the frame"],
        )
        assert r.exit_code == 0, r.output
        assert "no issues list the symptom" in r.output.lower()

    def test_by_symptom_routes_through_repo(self, cli_db):
        """Sanity check: repo-level find_issues_by_symptom is the data source.

        We match on a unique symptom and confirm the returned row set matches
        what the repo function returns directly — proves the CLI wires to the
        documented repo function and doesn't silently substitute a stub.
        """
        _seed_issues(cli_db)
        from motodiag.cli.main import cli
        from motodiag.knowledge.issues_repo import find_issues_by_symptom

        repo_rows = find_issues_by_symptom("suspension sag", db_path=cli_db)
        assert len(repo_rows) == 1
        assert repo_rows[0]["title"] == "Leaky fork seals at low mileage"

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "by-symptom", "suspension sag"])
        assert r.exit_code == 0, r.output
        assert "Leaky fork seals" in r.output


# =============================================================================
# TestCliByCode — `motodiag kb by-code <dtc>`
# =============================================================================


class TestCliByCode:
    def test_by_code_happy_path(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "by-code", "P0562"])
        assert r.exit_code == 0, r.output
        assert "Stator failure" in r.output
        # P0563 is on a different issue; must not bleed through on P0562
        assert "Regulator/rectifier" not in r.output

    def test_by_code_empty_result(self, cli_db):
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "by-code", "P9999"])
        assert r.exit_code == 0, r.output
        assert "no issues reference dtc" in r.output.lower()

    def test_by_code_uppercases_input(self, cli_db):
        """Lowercase DTC input should be force-uppercased before lookup.

        The knowledge-base loader stores codes uppercase; mechanics in the
        field often type lowercase. The CLI normalizes so either form works.
        """
        _seed_issues(cli_db)
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["kb", "by-code", "p0562"])
        assert r.exit_code == 0, r.output
        # Title output of the seeded P0562 issue must appear
        assert "Stator failure" in r.output
        # The uppercased code surfaces in the table title
        assert "P0562" in r.output


# =============================================================================
# TestRegistration — `kb` group wired into the CLI
# =============================================================================


class TestRegistration:
    def test_kb_group_registered(self):
        """`kb` appears as a subgroup on the top-level CLI."""
        from motodiag.cli.main import cli
        import click as _click

        assert "kb" in cli.commands, (
            f"kb group missing from cli; got {sorted(cli.commands)}"
        )
        kb_group = cli.commands["kb"]
        assert isinstance(kb_group, _click.Group), (
            f"cli.commands['kb'] is not a click.Group; got {type(kb_group)}"
        )

    def test_kb_has_five_subcommands(self):
        """All five planned kb subcommands are registered."""
        from motodiag.cli.main import cli

        kb_group = cli.commands["kb"]
        expected = {"list", "show", "search", "by-symptom", "by-code"}
        actual = set(kb_group.commands.keys())
        missing = expected - actual
        assert not missing, (
            f"Missing kb subcommands: {sorted(missing)}. "
            f"Present: {sorted(actual)}"
        )
