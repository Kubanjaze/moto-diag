"""Phase 255 — the transmission axis: a machine attribute, a row declaration, a filter that excludes.

**This file is the test Phase 254 was missing.**

254 passed 85 of its own tests, 22 of 22 mutations, a 986-test blast radius
and a 7,750-test regression, all green, and still shipped twelve rows that
reached a Gold Wing, a CBR1000RR, a Grom, an R1 and an XS650 — machines with
no CVT. Every one of those tests asked whether the rows were *right*. None
asked which machines would *receive* them. By the delivery standard that is
a validation failure, not a verification one, and the class of test that
catches it is the one below: assertions about machines, stated as negatives.

The negatives are the point. `test_the_machines_254_over_reached_get_none`
fails if a single scoped row reaches a machine that cannot have it, and it
names those machines individually rather than counting them, so deleting a
machine from the list is a visible edit rather than a quieter number.

Two rules this file also pins, because both are load-bearing and neither is
enforced by the schema:

* **No shipped row declares `manual`.** Until manual-transmission coverage
  of the corpus's models is sourced, a `{manual}` row would be withheld from
  every unlisted CBR and Harley — worse than today. Set logic is exercised
  with synthetic test-only rows instead.
* **No keyword matching anywhere.** Rows declare their sets by hand in the
  seed file; machines are classified from a sourced table. `Likewise` must
  not match `Like` and `Jetstream` must not match `Jet`.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.core.models import VehicleTransmission
from motodiag.knowledge.applicability import (
    AXES,
    ApplicabilityError,
    RowApplicability,
    TransmissionValue,
    dump_applicability,
    parse_applicability,
    row_applies,
)
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.knowledge.prompt_rows import compose_prompt_rows
from motodiag.knowledge.retrieval import rows_for_machine
from motodiag.knowledge.transmission import (
    ALL_TRANSMISSIONS,
    AMBIGUOUS_MODELS,
    POWERTRAIN_DEFAULT_EXCLUDED,
    TRANSMISSION_LOOKUP,
    Resolution,
    resolve_transmission,
)
from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
CVT_SEED = K / "known_issues_cvt.json"


def _cvt_rows() -> list[dict]:
    return json.loads(CVT_SEED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p255") / "p255.db")
    init_db(path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    reset_settings()
    return path


def _scoped_ids(db_path: str) -> set[int]:
    """Ids of every row that declares anything on the transmission axis."""
    with sqlite3.connect(db_path) as conn:
        return {
            r[0] for r in conn.execute(
                "SELECT id FROM known_issues WHERE applicability IS NOT NULL"
            )
        }


def _filtered(rows, resolution):
    """Apply the applicability filter to `rows` for an already-resolved machine.

    Phase 256 moved the filter out of `compose_prompt_rows` and into
    `retrieval.rows_for_machine`, so there is one way to apply it rather
    than two. These tests exercise the rule, not a door, so they call the
    predicate directly and skip the recording side.
    """
    from motodiag.knowledge.applicability import row_applies

    return [r for r in rows if row_applies(r, "transmission", resolution.candidates)]


def _reaching(db_path: str, make: str, model: str, *, powertrain: str = "ice") -> set[int]:
    """Row ids that survive the filter for this machine. No cap, so the
    measurement is about applicability and not about the twelve-row budget."""
    _, raw = known_issues_for_vehicle(make, model, db_path=db_path, limit=400)
    kept = rows_for_machine(raw, make=make, model=model, powertrain=powertrain,
                            purpose="prompt", db_path=db_path, record=False).rows
    return {r["id"] for r in kept}


def _before(db_path: str, make: str, model: str) -> set[int]:
    """What reached the machine before this phase — no transmission argument."""
    _, raw = known_issues_for_vehicle(make, model, db_path=db_path, limit=400)
    return {r["id"] for r in compose_prompt_rows(raw, limit=400)}


# ---------------------------------------------------------------------------
# 1. The machine-level regression guard — the test 254 was missing
# ---------------------------------------------------------------------------

#: Machines Phase 254 measurably over-reached, plus the five that are
#: actually in the operator's `vehicles` table. Named individually so that
#: dropping one is an edit somebody reviews.
OVER_REACHED = [
    ("Honda", "GL1800 Gold Wing", "six-speed or DCT tourer"),
    ("Honda", "CBR1000RR", "six-speed sportbike"),
    ("Honda", "Grom", "five-speed minibike"),
    ("Yamaha", "YZF-R1", "six-speed sportbike"),
    ("Yamaha", "XS650", "five-speed twin"),
    ("Honda", "CB500", "live vehicle"),
    ("Honda", "CBR954RR Fireblade", "live vehicle"),
    ("Honda", "cbrf4i", "live vehicle"),
    ("Yamaha", "MT07", "live vehicle"),
    ("SYM", "Symba", "Cub clone, centrifugal clutch and four gears"),
    ("SYM", "Wolf 150", "manual motorcycle from a scooter maker"),
]

#: Machines that retrieve the CVT layer today and MUST still retrieve it.
#: The diff that matters is against machines, not corpus model names: a
#: model with no rows of its own still reaches the layer through the
#: make-wide tier, which is the 254 defect itself.
MUST_KEEP = [
    ("Honda", "PCX 150"), ("Honda", "PCX150"), ("Honda", "Honda PCX150"),
    ("Honda", "PCX125"), ("Honda", "SH125i"), ("Honda", "SH150i"),
    ("Yamaha", "Zuma 125"), ("Yamaha", "Yamaha Zuma 125"), ("Yamaha", "YW125Y"),
    ("Yamaha", "XMAX"), ("Yamaha", "Yamaha XMAX"), ("Yamaha", "XMAX 300"),
    ("Kymco", "Agility 50"), ("Kymco", "Agility 125"), ("Kymco", "Kymco Agility"),
    ("Kymco", "Super 8"), ("Kymco", "Like 150i"), ("Kymco", "People S 250"),
    ("Genuine", "Buddy 125"), ("Genuine", "Genuine Buddy"),
    ("Genuine", "Buddy Kick"), ("Genuine", "Roughhouse 50"),
    ("Genuine", "Urbano 125"),
    ("Vespa", "Primavera"), ("Vespa", "LX 150"), ("Vespa", "LX 50"),
    ("Vespa", "GTS 300"),
    ("Piaggio", "Fly 125"), ("Piaggio", "Beverly 125"), ("Piaggio", "MP3 400"),
    ("SYM", "Symply 125"), ("SYM", "Mio 50"), ("SYM", "Fiddle III"),
]


class TestTheMachineLevelRegression:
    @pytest.mark.parametrize("make,model,why", OVER_REACHED,
                             ids=[f"{m}-{d}" for m, d, _ in OVER_REACHED])
    def test_the_machines_254_over_reached_get_none(self, db, make, model, why):
        """A machine with no CVT receives no row that declares `cvt`.

        The negative assertion. It is not "fewer rows" and not "a lower
        count" — it is zero, named machine by named machine.
        """
        reaching = _reaching(db, make, model) & _scoped_ids(db)
        assert reaching == set(), (
            f"{make} {model} ({why}) still receives scoped rows {sorted(reaching)}"
        )

    @pytest.mark.parametrize("make,model", [(m, d) for m, d, _ in OVER_REACHED],
                             ids=[f"{m}-{d}" for m, d, _ in OVER_REACHED])
    def test_the_over_reach_was_real_before_the_fix(self, db, make, model):
        """The defect is reproduced before it is asserted away.

        Without this, the test above would also pass on a corpus that had
        never had the rows at all, and would keep passing if the filter
        silently dropped everything.
        """
        assert _before(db, make, model) & _scoped_ids(db), (
            f"{make} {model} retrieved no scoped rows even BEFORE the filter — "
            "the guard above is not measuring anything"
        )

    @pytest.mark.parametrize("make,model", MUST_KEEP,
                             ids=[f"{m}-{d}" for m, d in MUST_KEEP])
    def test_sourced_cvt_machines_lose_nothing(self, db, make, model):
        """Every scooter that retrieves the CVT layer today still does."""
        before = _before(db, make, model) & _scoped_ids(db)
        after = _reaching(db, make, model) & _scoped_ids(db)
        assert before, f"{make} {model} retrieved no scoped rows before the filter"
        assert before <= after, (
            f"{make} {model} lost {sorted(before - after)} on deploy"
        )

    def test_the_kawasaki_control_is_unmoved(self, db):
        """Kawasaki isolated the cause in Step 0 and must stay at zero.

        It is not in the 254 rows' make list, so it never had them. If this
        ever returns rows, the cause was never the make column.
        """
        assert _before(db, "Kawasaki", "Ninja 400") & _scoped_ids(db) == set()
        assert _reaching(db, "Kawasaki", "Ninja 400") & _scoped_ids(db) == set()

    def test_the_unscoped_row_still_reaches_everyone_it_did(self, db):
        """Row 4605 is deliberately unscoped and must not be filtered.

        It is about three unrelated components all being called a drive
        belt, which is a fact about vocabulary and not about CVTs.
        """
        unscoped = {
            r["title"] for r in _cvt_rows() if "applicability" not in r
        }
        assert len(unscoped) == 1
        for make, model, _why in OVER_REACHED:
            _, raw = known_issues_for_vehicle(make, model, db_path=db, limit=400)
            titles_before = {r["title"] for r in raw}
            if not (unscoped & titles_before):
                continue
            kept = rows_for_machine(raw, make=make, model=model,
                                    purpose="prompt", db_path=db,
                                    record=False).rows
            assert unscoped <= {r["title"] for r in kept}, (
                f"{make} {model} lost the unscoped vocabulary row"
            )


# ---------------------------------------------------------------------------
# 2. The sequencing rule — 255 ships mechanism plus `cvt` scoping only
# ---------------------------------------------------------------------------
class TestSequencing:
    def test_no_shipped_row_declares_manual(self):
        """Until manual coverage is sourced, `{manual}` withholds too much.

        A clutch-cable row declared `{manual}` would be withheld from every
        CBR and Harley not in the lookup — a worse outcome than today's, not
        a better one. The rule is enforced across every seed file, not just
        254's, so a later phase cannot slip one in without deleting this.
        """
        offenders = []
        for path in sorted(K.glob("known_issues_*.json")):
            for row in json.loads(path.read_text(encoding="utf-8")):
                declared = (row.get("applicability") or {}).get("transmission") or []
                if "manual" in declared:
                    offenders.append((path.name, row.get("title", "")[:60]))
        assert offenders == [], offenders

    def test_only_cvt_is_declared_anywhere(self):
        declared = set()
        for path in sorted(K.glob("known_issues_*.json")):
            for row in json.loads(path.read_text(encoding="utf-8")):
                declared |= set((row.get("applicability") or {}).get("transmission") or [])
        assert declared <= {"cvt"}, declared

    def test_the_254_file_declares_eleven_of_twelve(self):
        rows = _cvt_rows()
        assert len(rows) == 12
        declared = [r for r in rows if "applicability" in r]
        assert len(declared) == 11
        assert all(r["applicability"] == {"transmission": ["cvt"]} for r in declared)


# ---------------------------------------------------------------------------
# 3. The applicability contract — the only guard a JSON column has
# ---------------------------------------------------------------------------
class TestTheContract:
    def test_the_literal_tracks_the_enum(self):
        """SSOT: the Literal and the enum must not drift apart.

        `Literal` needs static members, so the values are written out in
        `applicability.py` rather than derived. That is a shadowed constant
        (F9 subtype 4) and this is the test that keeps it honest.
        """
        from typing import get_args

        assert set(get_args(TransmissionValue)) == {
            v.value for v in VehicleTransmission
        }

    def test_an_unknown_axis_key_is_rejected(self):
        with pytest.raises(ApplicabilityError):
            parse_applicability({"transmision": ["cvt"]})

    def test_an_unknown_value_is_rejected(self):
        with pytest.raises(ApplicabilityError):
            parse_applicability({"transmission": ["twist_and_go"]})

    def test_an_empty_list_is_rejected(self):
        """Not 'applies to nothing', not 'applies to everything'. An error.

        An empty list is almost always an authoring slip, and a slip that
        could silently mean either of two opposite things must fail.
        """
        with pytest.raises(ApplicabilityError):
            parse_applicability({"transmission": []})

    def test_invalid_json_is_rejected(self):
        with pytest.raises(ApplicabilityError):
            parse_applicability("{transmission: cvt}")

    def test_absent_means_unscoped_not_empty(self):
        assert parse_applicability(None) is None
        assert parse_applicability("") is None
        assert parse_applicability({}) is None
        assert row_applies({}, "transmission", ["manual"]) is True

    def test_an_unknown_axis_cannot_be_queried(self):
        with pytest.raises(ApplicabilityError):
            row_applies({}, "cooling", ["liquid"])

    def test_the_write_path_validates_rather_than_trusts(self, tmp_path):
        """A typo must not reach the database as a silently unscoped row."""
        from motodiag.knowledge.issues_repo import add_known_issue

        path = str(tmp_path / "contract.db")
        init_db(path)
        with pytest.raises(ApplicabilityError):
            add_known_issue(
                title="t", description="d", db_path=path,
                applicability={"transmission": ["belt_drive"]},
            )

    def test_a_corrupt_row_is_excluded_not_fatal(self, db, caplog):
        """**Phase 256 changed this deliberately. Read the change, not the diff.**

        Phase 255 made an unreadable `applicability` RAISE at read time, on
        the reasoning that the only alternative was loading it as unscoped —
        which would put a mistyped row back in front of every machine. The
        cost shipped: one bad row stopped diagnosis for every machine, not
        just the one the row would have reached. That was filed as F122.

        The third option follows from this axis's own principle, *missing
        beats misleading*, and Phase 256 takes it: the chokepoint
        **excludes** the row, logs it by id, and counts it. Never unscoped,
        so a typo cannot reintroduce the Phase 254 defect. Never fatal, so
        one bad row cannot take down the product.

        **Loud rejection stays at write time** — the test below this one
        still asserts that `add_known_issue` raises. The asymmetry is the
        point: at write time nothing is lost by refusing; at read time
        refusing costs the technician an answer they could have had.
        """
        import logging
        import shutil
        from motodiag.knowledge.retrieval import rows_for_machine

        corrupt = str(Path(db).parent / "corrupt.db")
        shutil.copy(db, corrupt)
        with sqlite3.connect(corrupt) as conn:
            target = conn.execute(
                "SELECT id FROM known_issues WHERE applicability IS NOT NULL "
                "ORDER BY id LIMIT 1"
            ).fetchone()[0]
            conn.execute("UPDATE known_issues SET applicability = ? WHERE id = ?",
                         ('{"transmision": ["cvt"]}', target))

        _, raw = known_issues_for_vehicle("Honda", "PCX 150", db_path=corrupt, limit=400)
        assert target in {r["id"] for r in raw}, "the corrupt row was not retrieved"

        with caplog.at_level(logging.ERROR):
            result = rows_for_machine(raw, make="Honda", model="PCX 150",
                                      purpose="prompt", db_path=corrupt)

        assert target not in {r["id"] for r in result.rows}, "corrupt row was served"
        assert result.corrupt == 1
        assert str(target) in caplog.text, "the log must name the offending row id"

    def test_dump_round_trips(self):
        assert dump_applicability({"transmission": ["cvt"]}) == '{"transmission": ["cvt"]}'
        assert dump_applicability(None) is None

    def test_the_axis_tuple_matches_the_model(self):
        assert set(AXES) == set(RowApplicability.model_fields)


# ---------------------------------------------------------------------------
# 4. The inclusion rule — declared set must cover every candidate
# ---------------------------------------------------------------------------
#: Synthetic rows. Set logic is tested on these and never on shipped
#: content, which is what lets 255 ship `cvt` scoping only while still
#: proving the rule holds for every value.
SYNTHETIC = {
    "cvt_only": {"applicability": {"transmission": ["cvt"]}},
    "manual_only": {"applicability": {"transmission": ["manual"]}},
    "dct_only": {"applicability": {"transmission": ["dct"]}},
    "manual_and_dct": {"applicability": {"transmission": ["manual", "dct"]}},
    "all_six": {"applicability": {"transmission": sorted(ALL_TRANSMISSIONS)}},
    "unscoped": {},
}


class TestTheInclusionRule:
    def test_a_row_passes_when_it_covers_the_single_candidate(self):
        assert row_applies(SYNTHETIC["cvt_only"], "transmission", ["cvt"])

    def test_a_row_is_withheld_when_it_does_not(self):
        assert not row_applies(SYNTHETIC["cvt_only"], "transmission", ["manual"])

    def test_unknown_withholds_every_scoped_row(self):
        """All six candidates: only a row declaring all six survives."""
        for name in ("cvt_only", "manual_only", "dct_only", "manual_and_dct"):
            assert not row_applies(SYNTHETIC[name], "transmission", ALL_TRANSMISSIONS), name
        assert row_applies(SYNTHETIC["all_six"], "transmission", ALL_TRANSMISSIONS)
        assert row_applies(SYNTHETIC["unscoped"], "transmission", ALL_TRANSMISSIONS)

    def test_declaring_all_six_is_the_same_as_unscoped(self):
        for candidates in ([v] for v in ALL_TRANSMISSIONS):
            assert row_applies(SYNTHETIC["all_six"], "transmission", candidates)

    def test_ambiguous_passes_only_rows_valid_for_both(self):
        """The Africa Twin fixture, on synthetic rows."""
        both = resolve_transmission("Honda", "Africa Twin").candidates
        assert both == {"manual", "dct"}
        assert row_applies(SYNTHETIC["manual_and_dct"], "transmission", both)
        assert not row_applies(SYNTHETIC["manual_only"], "transmission", both)
        assert not row_applies(SYNTHETIC["dct_only"], "transmission", both)

    def test_an_empty_candidate_set_withholds(self):
        """Never read as 'matches everything'."""
        assert not row_applies(SYNTHETIC["cvt_only"], "transmission", [])
        assert not row_applies(SYNTHETIC["cvt_only"], "transmission", None)


# ---------------------------------------------------------------------------
# 5. The resolver — precedence, provenance, and matching
# ---------------------------------------------------------------------------
class TestPrecedence:
    def test_explicit_beats_the_lookup(self):
        r = resolve_transmission("Honda", "PCX 150", explicit="manual")
        assert r.value == "manual" and r.provenance == "explicit"

    def test_the_lookup_beats_the_powertrain_default(self):
        r = resolve_transmission("SYM", "Symba", powertrain="electric")
        assert r.value == "semi_auto_centrifugal"
        assert r.provenance == "model-sourced"

    def test_the_powertrain_default_applies_when_nothing_else_does(self):
        r = resolve_transmission("Zero", "SR/F", powertrain="electric")
        assert r.value == "direct_drive" and r.provenance == "powertrain-default"

    def test_the_electric_default_is_a_default_and_not_a_rule(self):
        """Three machines prove it. Each resolves unknown, not direct_drive.

        The Brammo Empulse has a six-speed gearbox, Electric Motion trials
        machines have a rider clutch and one ratio that fits none of the six
        values cleanly, and the Ninja 7 Hybrid is an automated manual.
        """
        for make, model in (("Brammo", "Empulse"), ("Electric Motion", "Escape"),
                            ("Kawasaki", "Ninja 7 Hybrid")):
            r = resolve_transmission(make, model, powertrain="electric")
            assert r.provenance == "unknown", (make, model, r.provenance)
            assert r.candidates == ALL_TRANSMISSIONS

    def test_an_unrecognised_explicit_value_falls_through(self):
        """A bad column value must not resolve to itself."""
        r = resolve_transmission("Honda", "PCX 150", explicit="twist and go")
        assert r.provenance == "model-sourced" and r.value == "cvt"

    def test_unknown_is_all_six(self):
        r = resolve_transmission("Honda", "CBR1000RR")
        assert r.candidates == ALL_TRANSMISSIONS
        assert r.provenance == "unknown"
        assert r.value is None and r.certain is False


class TestMatching:
    @pytest.mark.parametrize("make,model,expected", [
        ("Honda", "PCX150", "cvt"),
        ("Honda", "PCX 150", "cvt"),
        ("Honda", "PCX-150", "cvt"),
        ("Honda", "pcx  150", "cvt"),
        ("Honda", "Honda PCX150", "cvt"),
        ("Honda", "HONDA PCX 150", "cvt"),
        ("Yamaha", "Zuma 125", "cvt"),
        ("Yamaha", "Yamaha Zuma 125", "cvt"),
        ("Yamaha", "YW125Y", "cvt"),
        ("Genuine", "Genuine Buddy", "cvt"),
        ("Kymco", "Kymco Agility 125", "cvt"),
        ("SYM", "SYM Symba", "semi_auto_centrifugal"),
    ])
    def test_every_form_in_the_junction_resolves(self, make, model, expected):
        assert resolve_transmission(make, model).value == expected

    @pytest.mark.parametrize("make,model", [
        ("Kymco", "Likewise"),      # must not match the Kymco "Like"
        ("SYM", "Jetstream"),       # must not match the SYM "Jet 4"
        ("Genuine", "Buddyguard"),  # must not match "Buddy"
        ("Vespa", "LX 500"),        # must not match "LX 50"
        ("Honda", "PCX 1500"),      # must not match "PCX 150"
        ("Piaggio", "Flyweight"),   # must not match "Fly"
    ])
    def test_no_substring_matching(self, make, model):
        """Real model names are ordinary words — Like, Fly, Jet, Wolf, Buddy.

        Substring matching would make every one of them a hazard, so the
        comparison is whole-token against an explicit alias list.
        """
        assert resolve_transmission(make, model).provenance == "unknown"

    @pytest.mark.parametrize("make,model,split_form", [
        ("Bintelli", "Sprint49", "sprint 49"),
        ("Vespa", "Primavera150", "primavera 150"),
    ])
    def test_no_alpha_numeric_splitting(self, make, model, split_form):
        """`PCX150` resolves because it is a listed alias, not because it
        was split into `PCX` and `150`.

        These two cases are the discriminating ones: each concatenation is
        absent from the alias list while its split form is present, so a
        resolver that split letters from digits would answer differently.
        Asserting on `PCX150` alone cannot tell the two implementations
        apart — it resolves either way.
        """
        assert split_form in {
            a for e in TRANSMISSION_LOOKUP if e.make == make for a in e.aliases
        }, "the split form must be a real alias or this proves nothing"
        assert resolve_transmission(make, model).provenance == "unknown"

    def test_listed_concatenations_still_resolve(self):
        """The other half: a concatenation that IS listed must work."""
        assert resolve_transmission("Honda", "PCX150").provenance == "model-sourced"
        assert resolve_transmission("Honda", "SH125i").provenance == "model-sourced"

    @pytest.mark.parametrize("model", [
        "XC155", "XC155F", "xc 155f", "SMAX", "S-Max", "Yamaha SMAX",
        "Yamaha XC155F",
    ])
    def test_the_smax_resolves_under_either_name(self, model):
        """One machine, two names, and the marketing name is nearly invisible.

        Phase 255 shipped saying this equivalence was unsourced, after
        Yamaha's model pages returned JavaScript shells and their model API
        returned HTTP 500. It is in NHTSA's flat recall file, held on disk
        since Phase 254: campaign 16V892000 reads "certain model year 2015
        XC155F SMAX scooters" — the only occurrence of "SMAX" in 245,336
        rows. Searching for the marketing name and finding nothing was
        never evidence of anything.
        """
        assert resolve_transmission("Yamaha", model).value == "cvt"

    def test_matching_is_make_scoped(self):
        """'Sprint' is a Bintelli scooter AND a Vespa, from different books.

        This test used to assert that the Vespa Sprint resolved to unknown,
        because Phase 255 dropped its aliases as unsourced. They were
        sourced all along — the Primavera manual's own cover reads "Vespa
        Primavera S - Sprint S 125-150" — so the old assertion was pinning
        a gap rather than a property, and it broke the moment the gap
        closed.

        The property it was reaching for survives, and is now checked
        directly: one spelling, two makes, two different entries and two
        different documents. Both answer `cvt`, so provenance cannot tell
        them apart — only the entry can.
        """
        bintelli = resolve_transmission("Bintelli", "Sprint")
        vespa = resolve_transmission("Vespa", "Sprint")
        assert bintelli.value == vespa.value == "cvt"
        assert bintelli.entry is not None and vespa.entry is not None
        assert bintelli.entry.canonical != vespa.entry.canonical
        assert bintelli.entry.source != vespa.entry.source

    def test_a_model_does_not_resolve_under_another_marque(self):
        """The negative half: a make that does not build it gets nothing."""
        assert resolve_transmission("Genuine", "Buddy 125").value == "cvt"
        for other in ("Honda", "Yamaha", "Vespa", "SYM"):
            assert resolve_transmission(other, "Buddy 125").provenance == "unknown", other

    def test_the_make_prefix_is_stripped_not_ignored(self):
        """Stripping is positional: a leading make token is removed, and a
        make token anywhere else is not."""
        assert resolve_transmission("Honda", "Honda PCX 150").value == "cvt"
        assert resolve_transmission("Honda", "PCX 150 Honda").provenance == "unknown"

    def test_an_empty_model_resolves_unknown(self):
        assert resolve_transmission("Honda", "").provenance == "unknown"
        assert resolve_transmission("Honda", "Honda").provenance == "unknown"


class TestTheLookupItself:
    def test_every_entry_cites_a_document(self):
        """No row without a document; no entry without one either."""
        for e in TRANSMISSION_LOOKUP:
            assert len(e.source) > 40, e.canonical
            assert e.aliases, e.canonical

    def test_no_alias_is_duplicated_within_a_make(self):
        """Two entries claiming one spelling would make the answer depend on
        table order."""
        seen: dict[tuple[str, str], str] = {}
        for e in TRANSMISSION_LOOKUP:
            for alias in e.aliases:
                key = (e.make.lower(), alias.lower())
                assert key not in seen, (key, seen.get(key), e.canonical)
                seen[key] = e.canonical

    def test_there_is_no_make_default(self):
        """Not even for a marque that builds nothing but scooters.

        Piaggio's hand-shift Vespa PX and the Genuine Stella are the
        standing counter-examples: a make-default has to be right for every
        machine the marque ever sold.
        """
        for make in {e.make for e in TRANSMISSION_LOOKUP}:
            r = resolve_transmission(make, "a model nobody has ever sold")
            assert r.provenance == "unknown", make

    def test_the_lookup_holds_no_value_outside_the_enum(self):
        values = {e.transmission for e in TRANSMISSION_LOOKUP}
        assert values <= set(VehicleTransmission)

    def test_the_ambiguous_table_never_holds_a_single_value(self):
        """An entry with one candidate belongs in the lookup, not here."""
        for _make, _aliases, candidates in AMBIGUOUS_MODELS:
            assert len(candidates) > 1
            assert candidates <= ALL_TRANSMISSIONS

    def test_the_excluded_table_is_reachable(self):
        """Each exclusion must actually be hit by its own make and alias."""
        for make, aliases in POWERTRAIN_DEFAULT_EXCLUDED:
            for alias in aliases:
                r = resolve_transmission(make, alias, powertrain="electric")
                assert r.provenance == "unknown", (make, alias)


# ---------------------------------------------------------------------------
# 6. The filter excludes; 250B still reorders
# ---------------------------------------------------------------------------
class TestTheFilter:
    def test_it_excludes_rather_than_reorders(self):
        rows = [
            dict(id=1, title="variator", match_tier="make_wide", severity="medium",
                 **SYNTHETIC["cvt_only"]),
            dict(id=2, title="generic", match_tier="make_wide", severity="medium"),
        ]
        out = _filtered(rows, Resolution(frozenset({"manual"}), "model-sourced"))
        assert [r["id"] for r in out] == [2], "the row was reordered, not removed"

    def test_no_transmission_argument_changes_nothing(self):
        """Every existing caller is unaffected — 244S's behaviour by default."""
        rows = [
            dict(id=1, title="variator", match_tier="make_wide", severity="medium",
                 **SYNTHETIC["cvt_only"]),
            dict(id=2, title="generic", match_tier="make_wide", severity="medium"),
        ]
        assert {r["id"] for r in compose_prompt_rows(rows, limit=12)} == {1, 2}

    def test_filtering_happens_before_the_reserves(self, db):
        """An inapplicable row must not win a reserved slot.

        The relevance and safety reserves both pull from the pool. If the
        filter ran after composition, a critical scoped row would be swapped
        in over an applicable one and the machine would be told something
        false about itself in the most prominent slot there is.
        """
        rows = [
            dict(id=i, title=f"filler {i}", match_tier="make_wide",
                 severity="medium") for i in range(20)
        ] + [dict(id=99, title="variator rollers", match_tier="make_wide",
                  severity="critical", **SYNTHETIC["cvt_only"])]
        out = compose_prompt_rows(
            _filtered(rows, Resolution(frozenset({"manual"}), "model-sourced")),
            limit=12, symptoms=["variator rollers worn"],
        )
        assert 99 not in {r["id"] for r in out}

    def test_250B_still_reorders_and_still_excludes_nothing(self):
        """Phase 255 diverges from 250B deliberately and leaves it alone."""
        rows = [
            dict(id=1, title="ice row", make="Honda", match_tier="make_wide",
                 severity="medium"),
            dict(id=2, title="electric row", make="Zero", match_tier="make_wide",
                 severity="medium"),
        ]
        out = compose_prompt_rows(rows, limit=12, powertrain="electric")
        assert {r["id"] for r in out} == {1, 2}


class TestTheOtherDoors:
    """`compose_prompt_rows` is not the only path rows take to a model.

    Found by asking, late, which callers retrieve corpus rows for a specific
    machine — the question Phase 254 never asked about its own rows. There
    are three:

    * `_load_known_issues` — `motodiag diagnose` and `motodiag code`. Filtered.
    * the video `/ask` endpoint — hands rows straight to a vision model with
      no composition at all. **Was leaking**; filtered here.
    * `predict_failures` — its own `search_known_issues` retrieval. **Still
      leaking**, measured and filed as F123 rather than changed late in this
      phase, because it is a scored 50-prediction pipeline and deserves its
      own plan.
    """

    def test_the_ask_endpoint_filters(self, db):
        """The `/ask` path, at the limit the endpoint actually uses.

        Measured before the fix: an MT07 and an XS650 each received rows
        4614 (a CVT recall) and 4606 (variator roller wear limits). The
        Hondas missed them at limit=25 only because their own rows filled
        the 25 first — ranking luck, not correctness, which is why the
        assertion is on the machines that demonstrably leaked.
        """
        from motodiag.knowledge.retrieval import rows_for_machine

        scoped = _scoped_ids(db)
        for make, model in (("Yamaha", "MT07"), ("Yamaha", "XS650")):
            _, issues = known_issues_for_vehicle(
                make, model, db_path=db, limit=25,
            )
            assert {r["id"] for r in issues} & scoped, (
                f"{make} {model} no longer leaks at limit=25 — this test is "
                "not measuring anything"
            )
            kept = rows_for_machine(issues, make=make, model=model,
                                    purpose="prompt", db_path=db,
                                    record=False).rows
            assert {r["id"] for r in kept} & scoped == set()

    def test_the_ask_endpoint_keeps_a_scooters_rows(self, db):
        from motodiag.knowledge.retrieval import rows_for_machine

        _, issues = known_issues_for_vehicle(
            "Yamaha", "Zuma 125", db_path=db, limit=25,
        )
        before = {r["id"] for r in issues} & _scoped_ids(db)
        kept = rows_for_machine(issues, make="Yamaha", model="Zuma 125",
                                purpose="prompt", db_path=db, record=False).rows
        assert before and before <= {r["id"] for r in kept}

    def test_the_ask_endpoint_is_actually_wired_to_the_filter(self):
        """The logic above passes whether or not the endpoint calls it.

        This is the integration half, and it is the half Phase 254's suite
        did not have. Same shape as Phase 244N's recorder guard, which
        exists in this file's neighbour for the same reason.
        """
        from tests.support.source_guards import code_of
        from motodiag.api.routes import videos as videos_mod

        src = code_of(videos_mod)
        assert "rows_for_machine(" in src, (
            "the /ask endpoint must filter retrieved rows through the "
            "Phase 256 chokepoint"
        )


# ---------------------------------------------------------------------------
# 7. The counter — the cost of the policy, measured
# ---------------------------------------------------------------------------
class TestTheCounter:
    """Phase 256 moved this from process memory to a table.

    Phase 255 counted withheld rows in a module-level dict behind
    `record_withheld` / `withheld_snapshot` / `reset_withheld`. All three
    are retired. They could not have worked: every CLI command is a fresh
    process, so the aggregate was always zero by the time anyone could read
    it, and Phase 209B's orphan guard flagged the two accessors with the
    note "retire these or wire that route". Phase 256 wired the route and
    the entries came out of the allowlist.
    """

    def test_a_known_machine_is_not_recorded_as_a_gap(self, db):
        """Only `unknown` and `ambiguous` belong in the to-do list.

        A machine whose transmission is sourced withholds only rows that
        genuinely do not apply to it — the filter working, not a hole in
        the lookup. Recording it would bury the real gaps.
        """
        import shutil
        from motodiag.knowledge.retrieval import rows_for_machine, withheld_report

        path = str(Path(db).parent / "known.db")
        shutil.copy(db, path)
        _, raw = known_issues_for_vehicle("SYM", "Wolf 150", db_path=path, limit=400)
        result = rows_for_machine(raw, make="SYM", model="Wolf 150",
                                  purpose="prompt", db_path=path)
        assert result.resolution.provenance == "model-sourced"
        assert result.withheld > 0, "the Wolf is a manual; scoped rows must go"
        assert [r for r in withheld_report(path) if r["model"] == "Wolf 150"] == []

    def test_repeated_retrievals_accumulate(self, db):
        import shutil
        from motodiag.knowledge.retrieval import rows_for_machine, withheld_report

        path = str(Path(db).parent / "accum.db")
        shutil.copy(db, path)
        _, raw = known_issues_for_vehicle("Honda", "Grom", db_path=path, limit=400)
        for _ in range(3):
            rows_for_machine(raw, make="Honda", model="Grom",
                             purpose="prompt", db_path=path)
        row = [r for r in withheld_report(path) if r["model"] == "Grom"][0]
        assert row["retrievals"] == 3

    def test_the_chokepoint_persists_what_it_withheld(self, db):
        """The count lives in a table, readable by `motodiag kb withheld`."""
        import shutil
        from motodiag.knowledge.retrieval import rows_for_machine, withheld_report

        path = str(Path(db).parent / "record.db")
        shutil.copy(db, path)
        _, raw = known_issues_for_vehicle("Honda", "GL1800 Gold Wing",
                                          db_path=path, limit=400)
        result = rows_for_machine(raw, make="Honda", model="GL1800 Gold Wing",
                                  purpose="prompt", db_path=path)
        assert result.withheld > 0
        rows = [r for r in withheld_report(path)
                if r["model"] == "GL1800 Gold Wing"]
        assert rows, "nothing was persisted"
        assert rows[0]["rows_withheld"] == result.withheld
        assert rows[0]["provenance"] == "ambiguous"
        assert rows[0]["purpose"] == "prompt"

class TestTheSchema:
    def test_schema_version_is_at_least_63(self):
        from motodiag.core.database import SCHEMA_VERSION

        assert SCHEMA_VERSION >= 63  # f9-noqa: ssot-pin contract-pin: Phase 255's own floor pin. Migration 063 adds `vehicles.transmission` and `known_issues.applicability`; the literal names the migration this phase adds, and importing the constant would make this assert x >= x. Deliberately `>=` and not `==`: this asserts that 063 is in the head and the constant never moved back below it, which is the only claim this phase has about the number. The two pins that DO want the exact head are test_phase244I_model_vocabulary.py and test_phase191b_serve_migrations.py, and both were bumped 62 -> 63 in the same commit; Phase 244R's was relaxed from `== 62` to `>= 62` for the reason recorded there. A future migration must bump those two and leave this one alone.

    def test_the_columns_exist(self, db):
        with sqlite3.connect(db) as conn:
            vehicles = {r[1] for r in conn.execute("PRAGMA table_info(vehicles)")}
            issues = {r[1] for r in conn.execute("PRAGMA table_info(known_issues)")}
        assert "transmission" in vehicles
        assert "applicability" in issues

    def test_the_check_constraint_rejects_a_typo(self, db, tmp_path):
        path = str(tmp_path / "check.db")
        init_db(path)
        with sqlite3.connect(path) as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO vehicles (make, model, year, transmission) "
                    "VALUES ('X', 'Y', 2020, 'twist_and_go')"
                )

    def test_transmission_is_nullable_and_has_no_default(self, tmp_path):
        """Unlike `powertrain`, which defaults to 'ice'.

        A machine whose transmission nobody recorded has an unknown
        transmission. Writing 'manual' would be a fabrication that
        retrieval would then act on.
        """
        path = str(tmp_path / "null.db")
        init_db(path)
        with sqlite3.connect(path) as conn:
            conn.execute(
                "INSERT INTO vehicles (make, model, year) VALUES ('X', 'Y', 2020)"
            )
            value = conn.execute(
                "SELECT transmission FROM vehicles WHERE make = 'X'"
            ).fetchone()[0]
        assert value is None

    def test_rollback_and_reapply(self, tmp_path):
        from motodiag.core.migrations import (
            apply_pending_migrations, get_current_version, rollback_to_version,
        )

        path = str(tmp_path / "roll.db")
        init_db(path)
        assert get_current_version(path) >= 63
        rollback_to_version(62, db_path=path)
        with sqlite3.connect(path) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(known_issues)")}
        assert "applicability" not in cols
        apply_pending_migrations(db_path=path)
        with sqlite3.connect(path) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(known_issues)")}
        assert "applicability" in cols

    def test_the_backfill_reaches_the_already_seeded_rows(self, tmp_path):
        """A loader fix only reaches a database someone re-seeds.

        The operator's database already holds the twelve Phase 254 rows,
        written before there was a column to declare them in. This walks
        that exact path: rows present, column absent, migration applied.

        Building the fixture database and reading it back would NOT test
        this — the loader writes `applicability` on the way in, so the
        column is already populated and the migration's `post_apply` hook
        never has to do anything.
        """
        from motodiag.core.migrations import (
            apply_pending_migrations, rollback_to_version,
        )

        path = str(tmp_path / "backfill.db")
        init_db(path)
        load_known_issues_file(CVT_SEED, path)
        assert len(_scoped_ids(path)) == 11, "the loader path is broken"

        # Back to the state the operator's database is actually in: the
        # rows are there and the column is not.
        rollback_to_version(62, db_path=path)
        with sqlite3.connect(path) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(known_issues)")}
            assert "applicability" not in cols
            assert conn.execute(
                "SELECT COUNT(*) FROM known_issues"
            ).fetchone()[0] == 12, "rollback lost rows"

        apply_pending_migrations(db_path=path)
        assert len(_scoped_ids(path)) == 11, (
            "the migration did not declare the rows that were already there"
        )

    def test_the_backfill_leaves_the_unscoped_row_alone(self, tmp_path):
        """Row 4605 declares nothing and the migration must not invent one."""
        from motodiag.core.migrations import (
            apply_pending_migrations, rollback_to_version,
        )

        path = str(tmp_path / "backfill2.db")
        init_db(path)
        load_known_issues_file(CVT_SEED, path)
        rollback_to_version(62, db_path=path)
        apply_pending_migrations(db_path=path)
        with sqlite3.connect(path) as conn:
            blank = conn.execute(
                "SELECT COUNT(*) FROM known_issues WHERE applicability IS NULL"
            ).fetchone()[0]
        assert blank == 1
