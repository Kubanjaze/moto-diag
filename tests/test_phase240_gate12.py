"""Phase 240 — Gate 12: European brand coverage, through the real front doors.

Track K's closing gate. Roadmap row 240 was written as "Gate 11" before
Phase 205 closed under that number (desktop + mobile end-to-end, Track
J's opener), so this is Gate 12 — the same class of row correction as
"Mercuri (MV)" at Phase 235.

House style from Gates 5/6/7 and 11: every query goes through the REAL
CLI root or the HTTP API, never the repo layer; a class of executable
documentation records what the corpus honestly lacks and is MEANT to
fail the day someone fills it; and a gate guards the gates before it.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from motodiag.advanced.parts_loader import load_parts_file, load_parts_xref_file
from motodiag.api.app import create_app
from motodiag.cli.main import cli as real_cli
from motodiag.core.database import SCHEMA_VERSION, init_db
from motodiag.hardware.compat_loader import seed_all
from motodiag.knowledge.loader import load_dtc_directory, load_known_issues_file

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = REPO_ROOT / "src" / "motodiag" / "knowledge" / "seed"
K = SEED / "knowledge"
DTC = SEED / "dtc_codes"
HW = REPO_ROOT / "src" / "motodiag" / "hardware" / "compat_data"
PARTS = REPO_ROOT / "src" / "motodiag" / "advanced" / "data"

#: Track K's makes, with the display form each surface uses. Moto Guzzi
#: is here deliberately: it has no Track K row of its own and is covered
#: only by the cross-make phases 236-239, which the honest-gaps class
#: records.
MAKES = {
    "bmw": "BMW", "ducati": "Ducati", "ktm": "KTM", "triumph": "Triumph",
    "aprilia": "Aprilia", "mv-agusta": "MV Agusta", "moto-guzzi": "Moto Guzzi",
}
DTC_MAKES = {"bmw", "ducati", "ktm", "triumph", "aprilia", "mv-agusta"}
COMPAT_MAKES = {"bmw", "ducati", "ktm", "triumph", "aprilia", "mv-agusta"}
CROSS_MAKE_FILES = (
    "known_issues_european_tooling.json",
    "known_issues_european_differentials.json",
    "known_issues_european_intervals.json",
    "known_issues_european_parts.json",
)


@pytest.fixture(scope="module")
def gate_db(tmp_path_factory):
    """One fully seeded database: DTCs, every knowledge file, the adapter
    catalogue (through the CLI, as a user would) and the parts catalogue."""
    from motodiag.core.config import reset_settings
    path = str(tmp_path_factory.mktemp("gate12") / "gate12.db")
    init_db(path)
    load_dtc_directory(DTC, path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    load_parts_file(PARTS / "parts.json", path)
    load_parts_xref_file(PARTS / "parts_xref.json", path)
    seed_all(data_dir=HW, db_path=path)
    return path


@pytest.fixture(scope="module")
def api_key(gate_db):
    """A real key for a real user, the way Gate 11 does it — the /v1
    routes are key-gated and the gate must walk in the front door."""
    from motodiag.auth.api_key_repo import create_api_key
    from motodiag.core.database import get_connection
    with get_connection(gate_db) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) VALUES (?, ?, ?, 1)",
            ("gate12_owner", "gate12_owner@ex.com", "shop"),
        ).lastrowid
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
            "VALUES (?, ?, 'active', datetime('now', '+30 days'))", (uid, "shop"))
    _, key = create_api_key(uid, db_path=gate_db)
    # The parts catalogue is shop-scoped in the API, so the key's user
    # needs a shop they own — created through the CLI, as Gate 11 did.
    from motodiag.core.config import reset_settings
    from motodiag.shop import seed_first_owner
    os.environ["MOTODIAG_DB_PATH"] = gate_db
    reset_settings()
    _run(["shop", "profile", "init", "--name", "Gate 12 Cycles"])
    with get_connection(gate_db) as conn:
        shop_id = conn.execute("SELECT id FROM shops ORDER BY id DESC LIMIT 1").fetchone()[0]
    seed_first_owner(shop_id, uid, db_path=gate_db)
    return key, shop_id


@pytest.fixture(autouse=True)
def _env(gate_db, monkeypatch):
    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DB_PATH", gate_db)
    monkeypatch.setenv("COLUMNS", "240")
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    yield
    reset_settings()


def _run(args, expect_ok=True):
    """Invoke the REAL cli root, as Gate 11 insisted — a partial root
    cannot catch a command that fails to register on the real one."""
    result = CliRunner().invoke(real_cli, args, catch_exceptions=False)
    if expect_ok:
        assert result.exit_code == 0, f"{' '.join(args)} failed:\n{result.output[-1500:]}"
    return result


@pytest.fixture(scope="module")
def api(api_key):
    key, _ = api_key
    client = TestClient(create_app())
    client.headers.update({"X-API-Key": key})
    return client


@pytest.fixture(scope="module")
def shop_id(api_key):
    return api_key[1]


def _first_code(make_slug):
    rows = json.loads((DTC / f"{make_slug.replace('-', '_')}.json").read_text(encoding="utf-8"))
    return rows[0]["code"], rows[0]


def _compat_rows(make_slug):
    return [r for r in json.loads((HW / "compat_matrix.json").read_text(encoding="utf-8")) if r["make"] == make_slug]


# ===========================================================================
# 1. Every European make answers through the CLI
# ===========================================================================
class TestEveryEuropeanMakeAnswersThroughTheCli:
    @pytest.mark.parametrize("slug", sorted(MAKES))
    def test_kb_search_by_make_returns_known_issues(self, slug):
        result = _run(["kb", "search", MAKES[slug], "--limit", "5"])
        assert MAKES[slug].split()[0] in result.output, result.output[-800:]

    @pytest.mark.parametrize("slug", sorted(DTC_MAKES))
    def test_a_make_specific_code_resolves_to_the_make_row_not_the_generic(self, slug, api):
        """dtc_repo resolves make-specific before generic. The make row
        must win, and it must be the make's meaning — for Aprilia that
        is the whole point of Phase 235."""
        code, row = _first_code(slug)
        r = api.get(f"/v1/kb/dtc/{code}", params={"make": row["make"]})
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body.get("make") == row["make"], body
        assert body.get("description") == row["description"]

    @pytest.mark.parametrize("slug", sorted(COMPAT_MAKES))
    def test_compat_recommend_names_an_adapter_for_the_make(self, slug):
        rows = _compat_rows(slug)
        assert rows, f"{slug} has no compat rows"
        model = rows[0]["model_pattern"].replace("%", "").strip() or "any"
        year = rows[0]["year_min"] or 2015
        # `check` asks whether ONE named adapter fits; `recommend` asks
        # which adapters fit this bike — the question the gate is asking.
        result = _run(["hardware", "compat", "recommend", "--make", slug, "--model", model,
                       "--year", str(year), "--limit", "50", "--json"], expect_ok=False)
        assert result.exit_code == 0, result.output[-800:]
        # --json rather than the rich table: a long slug is truncated by
        # the renderer, which is a display fact and not a coverage one.
        got = json.loads(result.output)
        slugs = {r["adapter_slug"] for r in rows}
        found = {(x.get("adapter_slug") or x.get("slug") or "") for x in (got if isinstance(got, list) else got.get("items", got.get("results", [])))}
        assert slugs & found, f"{slug}: none of {sorted(slugs)[:5]} in {sorted(found)[:8]}"


# ===========================================================================
# 2. The two front doors agree
# ===========================================================================
class TestCrossSurfaceAgreement:
    @pytest.mark.parametrize("slug", sorted(MAKES))
    def test_api_issue_search_finds_the_make_the_cli_found(self, slug, api):
        r = api.get("/v1/kb/issues", params={"make": MAKES[slug], "limit": 100})
        assert r.status_code == 200, r.text[:400]
        items = r.json().get("items", r.json())
        assert items, f"API returned no issues for {slug}"
        assert all(MAKES[slug].split()[0].lower() in (i.get("make") or "").lower() for i in items)

    def test_parts_search_reaches_the_european_rows(self, api, shop_id):
        """The parts catalogue is scoped by shop in the API; the gate
        asks for a European make and expects Phase 239's rows back."""
        r = api.get(f"/v1/shop/{shop_id}/parts/search", params={"q": "oil filter", "make": "aprilia"})
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("results", []))
        assert any("aprilia" in json.dumps(i).lower() for i in items), str(body)[:300]


# ===========================================================================
# 3. What Track K honestly lacks — executable documentation
# ===========================================================================
class TestTheHonestGaps:
    """These PASS today and are MEANT to fail the day someone fills the
    gap, which is the cheapest reminder to update the gate and the
    roadmap. The pattern is Gate 11's TestDesktopCannotFinishTheJob."""

    def test_moto_guzzi_has_no_dtc_file(self):
        assert not (DTC / "moto_guzzi.json").exists()

    def test_moto_guzzi_has_no_compat_rows(self):
        assert _compat_rows("moto-guzzi") == []

    def test_moto_guzzi_has_no_make_file_of_its_own(self):
        assert not list(K.glob("known_issues_moto_guzzi*.json"))

    def test_moto_guzzi_is_covered_only_by_the_cross_make_phases(self):
        """Its issues all come from 236-239. If a make-file appears, the
        test above fails first; this one records where the coverage is."""
        hits = 0
        for name in CROSS_MAKE_FILES:
            for e in json.loads((K / name).read_text(encoding="utf-8")):
                if "Moto Guzzi" in e["make"]:
                    hits += 1
        assert hits >= 5

    def test_aprilia_660_valve_interval_is_recorded_as_unverified(self):
        raw = json.loads((K / "known_issues_european_intervals.json").read_text(encoding="utf-8"))
        e = next(x for x in raw if "Trust Aprilia" in x["title"])
        assert "unverified" in e["model"] or "unconfirmed" in e["description"]


# ===========================================================================
# 4. Track K corpus invariants
# ===========================================================================
class TestTrackKCorpusInvariants:
    def test_every_cross_make_file_exists(self):
        for name in CROSS_MAKE_FILES:
            assert (K / name).exists(), name

    #: Every reference format the Phase 231 decision names, not just the
    #: two the first draft matched. NHTSA nnVnnnnnn, "Recall nnnnnnn",
    #: DVSA R/YYYY/NNN, Transport Canada YYYY-NNN as a recall id, and a
    #: bare 7-digit campaign id in recall-shaped prose.
    CAMPAIGN_PATTERNS = (
        r"\b\d{2}V\d{6}\b",
        r"\bRecall\s+\d{6,7}\b",
        r"\bR/\d{4}/\d{3}\b",
        # A reference-SHAPED token, not the words. "Record the campaign
        # reference on the job card" is an instruction to a mechanic, not
        # a printed reference — the mention-versus-use distinction this
        # track hit fifteen times in content validators, and once more
        # here in the gate's own first draft.
        # The reference token must contain a DIGIT. Without that the
        # case-insensitive scan matched the word "numbers" in the very
        # sentence that records the decision — "No campaign reference
        # numbers appear here deliberately." Mention versus use, twice
        # in one test.
        r"\b(?:recall|campaign) (?:number|reference|id)[:\s]+(?=[-A-Z0-9/]*\d)[A-Z0-9][-A-Z0-9/]{4,}",
    )

    #: Every Track K surface, not only the knowledge files. The audit
    #: found "Bajaj-built" in compat_matrix and a withheld cost figure in
    #: parts.json — neither of which the first draft's file set reached.
    def _track_k_surfaces(self):
        files = [p for p in K.glob("known_issues_*.json")
                 if any(p.name.startswith(f"known_issues_{m}")
                        for m in ("bmw", "ducati", "ktm", "triumph", "aprilia", "mv", "european"))]
        files += list(DTC.glob("*.json"))
        files += [HW / "compat_matrix.json", HW / "adapters.json"]
        return files

    def test_no_campaign_reference_number_anywhere_in_track_k(self):
        """The Phase 231 decision — describe a campaign, route to the
        frame number — enforced across every Track K surface and every
        field, not four fields of one file family.

        Widened at Phase 240 after the closure audit showed the first
        draft would have passed over all three leaks it found: it read
        only title/description/fix_procedure/causes, so a value in the
        `model` field was invisible, and it never opened the DTC files,
        the adapter catalogue or the parts catalogue at all."""
        import re as _re
        for f in self._track_k_surfaces():
            blob = f.read_text(encoding="utf-8")
            for pat in self.CAMPAIGN_PATTERNS:
                hits = _re.findall(pat, blob, _re.I)
                assert not hits, f"{f.name}: campaign reference {hits[:3]}"

    def test_the_deliberate_absences_hold_across_every_surface(self):
        """Five decisions not to print something, each made in one phase
        and each checked here corpus-wide. Every one of these fired
        during the Track K closure audit against a file other than the
        one that made the decision — which is precisely why the check
        belongs at the gate rather than in the deciding phase's test."""
        import re as _re
        surfaces = self._track_k_surfaces() + [PARTS / "parts.json"]
        blobs = {f.name: f.read_text(encoding="utf-8") for f in surfaces}

        # (a) The Triumph pre-Euro-5 connector transition year.
        for name, blob in blobs.items():
            if "triumph" not in name and "european" not in name:
                continue
            for m in _re.finditer(r"(?:16-pin|sixteen-pin|red 6-pin|six-pin)[^\"]{0,120}", blob):
                assert not _re.search(r"20 ?2[3-5]", m.group(0)), f"{name}: transition year — {m.group(0)[:90]}"

        # (b) The 2025-onward KTM 390 platform's build location. Checked
        # STRUCTURALLY, not by proximity in the raw text: a mutation that
        # merely widened an entry's year_end to 2026 slipped past a
        # 220-character text window, because the year lives in a separate
        # JSON field from the plant name. Any entry or compat row whose
        # prose asserts a build location must be bounded by its own year
        # fields, or must record the absence.
        NEG = _re.compile(r"could not be established|not established|unestablished|"
                          r"do not carry|left open|not assumed", _re.I)
        PLANT = _re.compile(r"Bajaj|Chakan|built in India", _re.I)
        for f in self._track_k_surfaces() + [PARTS / "parts.json"]:
            try:
                rows = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                blob = json.dumps(row)
                if not PLANT.search(blob):
                    continue
                if NEG.search(blob):
                    continue  # the entry that records the absence
                end = row.get("year_end") or row.get("year_max") or 0
                assert end < 2025, (
                    f"{f.name}: asserts a build location through {end} — the 2025-onward "
                    f"390 platform's plant is not established ({str(row.get('title') or row.get('model_pattern'))[:60]})")

        # (c2) The withheld conversion cost, over the WHOLE notes field of
        # any tappet row — a 200-character window from the word "tappet"
        # missed a figure appended to the end of a long note.
        for f in [PARTS / "parts.json"]:
            for row in json.loads(f.read_text(encoding="utf-8")):
                if "tappet" not in json.dumps(row).lower():
                    continue
                assert not _re.search(r"(?:USD|EUR|GBP|NZD|\$)\s?[\d,]{3,}", row.get("notes", "")), \
                    f"{f.name}: {row['slug']} carries the withheld conversion cost"

        # (c) The Moto Guzzi 8V roller-tappet conversion cost, in prose.
        for name, blob in blobs.items():
            for m in _re.finditer(r"(?:tappet|conversion kit)[^\"]{0,400}", blob, _re.I):
                assert not _re.search(r"(?:USD|EUR|GBP|NZD|\$)\s?[\d,]{3,}", m.group(0)), \
                    f"{name}: conversion cost figure — {m.group(0)[:90]}"

        # (d) The MV Agusta F4 shim diameter, as a specification.
        for name, blob in blobs.items():
            for m in _re.finditer(r"7\.48\s?mm[^\"]{0,160}", blob):
                assert _re.search(r"owner report|not a specification|unverified", m.group(0), _re.I), \
                    f"{name}: shim diameter printed as a spec — {m.group(0)[:90]}"

        # (e) The MV Agusta crank rotation direction (Phase 233).
        mv = blobs.get("known_issues_mv_agusta_triple.json", "")
        for m in _re.finditer(r"crank[^\"]{0,140}", mv, _re.I):
            assert not _re.search(r"\b(?:clockwise|anticlockwise|counter-?clockwise)\b", m.group(0), _re.I), \
                f"MV crank direction stated — {m.group(0)[:90]}"

    def test_no_file_still_defers_something_a_later_phase_resolved(self):
        """A deferral that a later phase answered becomes a false claim.
        Phase 238 amended one in place and missed its sibling; the audit
        found it. Pinned so the next resolved deferral is not left
        stale."""
        import re as _re
        mv = json.loads((K / "known_issues_mv_agusta_triple.json").read_text(encoding="utf-8"))
        for e in mv:
            blob = " ".join([e["title"], e["description"]])
            if "F3" in blob and "valve" in blob.lower():
                assert not _re.search(r"is unconfirmed|could not be confirmed against MV's own table",
                                      blob), e["title"]

    def test_provenance_vocabulary_is_the_six_values(self):
        seen = set()
        for f in K.glob("known_issues_*.json"):
            seen |= {e.get("source", "unverified") for e in json.loads(f.read_text(encoding="utf-8"))}
        assert seen <= {"unverified", "model-generated", "forum", "service-manual", "mechanic-verified", "regulation"}, seen

    def test_the_regulation_value_is_in_use(self):
        raw = json.loads((K / "known_issues_aprilia_mv_electrical.json").read_text(encoding="utf-8"))
        assert any(e["source"] == "regulation" for e in raw)

    def test_documented_count_matches_the_live_seed(self):
        import re
        live = sum(len(json.loads(f.read_text(encoding="utf-8"))) for f in K.glob("known_issues_*.json"))
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        m = re.search(r"(\d{3,4}) curated known issues", readme)
        assert m and int(m.group(1)) == live, (m and m.group(1), live)


# ===========================================================================
# 5. Regression — a gate guards the gates before it
# ===========================================================================
class TestRegression:
    @pytest.mark.parametrize("gate_file", [
        "tests/test_phase133_gate_5.py",
        "tests/test_phase147_gate_6.py",
        "tests/test_phase159_gate_7.py",
        "tests/test_phase174_gate8.py",
        "tests/test_phase184_gate9.py",
        "tests/test_phase205_gate11.py",
    ])
    def test_earlier_gate_still_passes(self, gate_file):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", gate_file, "-q", "-p", "no:cacheprovider"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=900,
        )
        assert result.returncode == 0, f"{gate_file} regressed:\n{result.stdout[-2000:]}"

    def test_schema_version_pin(self):
        assert SCHEMA_VERSION == 52, (  # f9-noqa: ssot-pin contract-pin: Gate 12 schema-bump pin. The literal is the point — importing the constant would make this assert `x == x`. 52 is migration 052 (Phase 235B, known_issues.source gains `regulation`). Bumping requires a corresponding new migration in src/motodiag/core/migrations.py.
            "SCHEMA_VERSION moved — confirm a migration accompanies it and update this pin."
        )
