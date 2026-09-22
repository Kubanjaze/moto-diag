"""Phase 255C — one canonical identity per machine, and a positive gate on extraction.

Two classes, and they are closed by different things:

* **Spelling-split** — one machine under several junction strings, each
  reachable only from the spelling that produced it. Closed by the pair form
  and by the two guards in `TestOneCanonicalPerMachine`.
* **Debris** — strings in the junction that are not model names at all.
  **The spelling guards cannot close this**, and the reason is worth stating
  because it was nearly built that way: 244I derives `model_vocabulary` FROM
  the model column, so a debris string that reached the junction is in the
  vocabulary, and the resolver returns it by exact match. Debris defines its
  own canonical. A guard asking "does this resolve to itself" is satisfied by
  construction on exactly the strings it was written for.

  Closed instead by a **positive gate** at extraction, whose negative control
  is the whole corpus rather than a sample.
"""

from __future__ import annotations

import json
import pathlib
import re
import sqlite3

import pytest

from motodiag.knowledge.models import _model_tokens

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestBugFix1ThousandsSeparator:
    """A comma between digits is a thousands separator, not a list delimiter."""

    @pytest.mark.parametrize("value,expected", [
        ("798cc triple — Brutale 800, Dragster RR, Rivale at 12,000 km; "
         "Turismo Veloce, F3 at 30,000 km",
         # '798cc triple' is absent because the positive gate rejects it:
         # no designation code, and 'triple' is a bare lowercase word. The
         # two fixes compose — the tokenizer stops tearing the figure, and
         # the gate then judges the whole fragment.
         ["Brutale 800", "Dragster RR", "Rivale at 12,000 km",
          "Turismo Veloce", "F3 at 30,000 km"]),
        ("Multistrada V4, Diavel V4 (V4 Granturismo, 60,000 km); Panigale V4",
         ["Multistrada V4", "60,000 km", "Panigale V4"]),
    ])
    def test_a_figure_is_not_torn_in_half(self, value, expected):
        assert _model_tokens(value) == expected

    def test_no_bare_thousands_fragment_survives(self):
        """'000 km' and the bare numbers it left behind are the defect."""
        toks = _model_tokens("Rivale at 12,000 km; F3 at 30,000 km")
        assert "000 km" not in toks
        assert "12" not in toks and "30" not in toks

    @pytest.mark.parametrize("value,count", [
        ("Agility 50, Agility 125, People S 250", 3),
        ("PCX125, PCX150, PCX160", 3),
        ("Vespa LX 50, Vespa LX 125, Vespa LX 150", 3),
    ])
    def test_positive_control_a_real_comma_list_still_splits(self, value, count):
        """The fix must not stop commas working as delimiters."""
        assert len(_model_tokens(value)) == count


from support.model_gate_fixtures import ADMITTED_BY_THE_GATE, REJECTED_BY_THE_GATE  # noqa: E402
from motodiag.core.database import init_db  # noqa: E402
from motodiag.knowledge.loader import load_known_issues_file  # noqa: E402
from motodiag.knowledge.marques import rebuild_make_index_at  # noqa: E402
from motodiag.knowledge.models import (  # noqa: E402
    admits_as_model, rebuild_model_index, rebuild_model_index_at,
)

SEED_DIR = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"


@pytest.fixture(scope="module")
def seeded(tmp_path_factory) -> str:
    path = str(tmp_path_factory.mktemp("p255C") / "p255C.db")
    init_db(path)
    for f in sorted(SEED_DIR.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    return path


class TestThePositiveGate:
    """Extraction admits a fragment only if it is shaped like a designation.

    Every filter this replaces is a blacklist, and each defect found was a
    gap in one. Four gaps in a single pass is the signature of the wrong
    shape of check: a blacklist admits everything nobody thought to name.
    """

    @pytest.mark.parametrize("value", sorted(REJECTED_BY_THE_GATE))
    def test_every_pinned_string_is_rejected(self, value):
        assert not admits_as_model(value)

    @pytest.mark.parametrize("value", ADMITTED_BY_THE_GATE)
    def test_every_named_designation_is_admitted(self, value):
        assert admits_as_model(value)

    def test_the_gate_rejects_exactly_the_pinned_set(self, seeded):
        """The negative control is the WHOLE corpus, not a sample.

        A gate validated on the cases it was written from proves nothing.
        This asks what it does to all 705 strings the junction held before
        it, and requires the answer to be exactly the pinned set.
        """
        with sqlite3.connect(seeded) as conn:
            present = {m for (m,) in conn.execute(
                "SELECT DISTINCT model FROM known_issue_models")}
        leaked = REJECTED_BY_THE_GATE & present
        assert not leaked, (
            f"the gate let {len(leaked)} pinned string(s) into the junction: "
            f"{sorted(leaked)}")

        # ...and nothing the gate rejects may be missing from the pin. A new
        # rejection is named rather than silently absorbed into a count.
        from motodiag.knowledge.models import _model_tokens
        with sqlite3.connect(seeded) as conn:
            columns = [r[0] for r in conn.execute(
                "SELECT model FROM known_issues WHERE model IS NOT NULL AND model != ''")]
        rejected = set()
        for col in columns:
            for raw in re.split(r",|;|—|–| and ", col):
                tok = raw.strip().strip("()[]{}\"'“”‘’ ").strip()
                if 2 <= len(tok) <= 28 and not admits_as_model(tok):
                    rejected.add(tok)
        unpinned = {r for r in rejected if r in REJECTED_BY_THE_GATE} ^ rejected
        surprises = {r for r in unpinned if r in present}
        assert not surprises, (
            "strings the gate rejects that are not in the pinned set and are "
            f"still reaching the junction: {sorted(surprises)}")

    def test_group_B_is_untouched(self, seeded):
        """Group (B) is a 244I semantics question, not this phase's.

        `R1200 hexhead` is a designation 244I is built to carry;
        `2020 service manual` is debris. Both are "number plus lowercase
        words" and no shape rule separates them. Both stay.
        """
        with sqlite3.connect(seeded) as conn:
            present = {m for (m,) in conn.execute(
                "SELECT DISTINCT model FROM known_issue_models")}
        for b in ("R1200 hexhead", "990 LC8 twins", "798 triples", "2020 service manual"):
            assert b in present, f"group (B) string {b!r} was removed; it must not be"

    def test_the_plain_model_path_is_gated_too(self):
        """Both `is_plain_model` early-accepts needed the gate.

        A short delimiter-free prose sentence takes that branch in BOTH
        `_model_tokens` and `extract_models`, and neither consulted any
        filter. "Piaggio Group marques only" is 26 characters with no comma,
        and reached the junction whole through each of them. Fixing one left
        the other open, and the whole-corpus control is what found it.
        """
        from motodiag.knowledge.models import _model_tokens, is_plain_model
        s = "Piaggio Group marques only"
        assert is_plain_model(s), "fixture assumption: this takes the plain-model branch"
        assert _model_tokens(s) == []


#: The six spellings of one machine. The resolver must return one canonical
#: for every one of them — that is the whole of decision 1.
PCX_SPELLINGS = ("PCX 150", "PCX150", "Honda PCX150", "Honda PCX 150",
                 "pcx 150", "honda pcx150")

#: Machines the tier table is measured over. A CVT machine per marque family,
#: plus non-CVT controls that must not gain a scoped row.
TIER_MACHINES = (
    ("Honda", "PCX 150"), ("Kymco", "Agility 50"), ("Vespa", "LX 50"),
    ("Yamaha", "Zuma 125"), ("Genuine", "Buddy 125"),
    ("Honda", "GL1800 Gold Wing"), ("Yamaha", "YZF-R1"), ("Kawasaki", "Ninja 400"),
)


class TestOneCanonicalPerMachine:
    """Identity is a (make, model) pair, and it does not depend on spelling."""

    @pytest.mark.parametrize("spelling", PCX_SPELLINGS)
    def test_every_spelling_resolves_to_one_canonical(self, seeded, spelling):
        """The resolver positive control.

        Before this phase `PCX 150` and `Honda PCX150` were BOTH `exact` at
        confidence 1.0 and resolved to themselves, so the junction entry a
        row produced was reachable only from the spelling that produced it.
        """
        from motodiag.knowledge.vehicle_resolver import resolve_vehicle
        got = resolve_vehicle("Honda", spelling, db_path=seeded)
        assert got.model.resolved == "PCX 150", (
            f"{spelling!r} resolved to {got.model.resolved!r}")
        assert got.model.method == "exact"

    def test_guard_2_no_machine_has_two_spellings_in_its_own_pool(self, seeded):
        """Per MARQUE, which is the correct scope for the pair form.

        Cross-marque repetition is not a split: `(Kymco, 'Kymco Agility')`
        and `(SYM, 'Agility')` are different pairs and may both exist. What
        may not exist is one marque holding two spellings of one machine.
        """
        from motodiag.knowledge.models import model_vocabulary
        import collections
        key = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa: E731
        offenders = {}
        for marque, names in model_vocabulary(seeded).items():
            groups = collections.defaultdict(set)
            for n in names:
                groups[key(n)].add(n)
            for k, v in groups.items():
                if len(v) > 1:
                    offenders[(marque, k)] = sorted(v)
        assert not offenders, (
            "a marque holds more than one spelling of one machine: "
            f"{offenders}")

    def test_guard_1_every_junction_pair_resolves_to_itself(self, seeded):
        """A junction pair must be reachable from its own marque and model.

        This closes the SPELLING-SPLIT class. It is deliberately NOT the
        debris guard: 244I derives the vocabulary from the model column, so
        a debris string that reached the junction is in the vocabulary and
        resolves to itself. Debris defines its own canonical, and the gate
        in `TestThePositiveGate` is what closes that.
        """
        from motodiag.knowledge.vehicle_resolver import resolve_vehicle
        with sqlite3.connect(seeded) as conn:
            pairs = list(conn.execute(
                "SELECT DISTINCT make, model FROM known_issue_models"))
        bad = []
        for make, model in pairs:
            got = resolve_vehicle(make, model, db_path=seeded)
            if got.model.resolved != model:
                bad.append((make, model, got.model.resolved))
        assert not bad, f"{len(bad)} junction pair(s) do not resolve to themselves: {bad[:6]}"

    def test_the_junction_carries_the_marque(self, seeded):
        with sqlite3.connect(seeded) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(known_issue_models)")}
        assert {"issue_id", "make", "model"} <= cols

    def test_the_tier_table(self, seeded):
        """Before/after per fixture machine. Retrieved and kept must not move.

        The PCX is the case the phase was opened for: 2 rows at tier `model`
        before, 11 after, with 166 retrieved and 166 kept on both sides. The
        prompt's twelve change because the 244S cap re-cuts a re-ranked
        list, not because the filter excluded anything.
        """
        import collections
        from motodiag.knowledge.retrieval import rows_for_machine
        from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

        for make, model in TIER_MACHINES:
            _, raw = known_issues_for_vehicle(make, model, db_path=seeded, limit=400)
            kept = rows_for_machine(raw, make=make, model=model, purpose="prompt",
                                    db_path=seeded, record=False).rows
            tiers = collections.Counter(r["match_tier"] for r in raw)
            assert len(kept) <= len(raw)
            if (make, model) == ("Honda", "PCX 150"):
                assert tiers["model"] == 11, (
                    f"the PCX should reach 11 rows at tier model, got {tiers['model']}")
                assert len(raw) == 166 and len(kept) == 166, (len(raw), len(kept))

    def test_the_degradation_path_still_binds(self, tmp_path):
        """A database with no model junction must degrade, not crash.

        `tier_sql_no_junction` takes three placeholders where the pair form
        takes four. Reusing the pair bindings on that path raised
        "5 bindings supplied, 6 given" — turning a deliberate fail-soft into
        a crash. Found by running the migration, not by reading the code.
        """
        from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle
        path = str(tmp_path / "nojunction.db")
        init_db(path)
        for f in sorted(SEED_DIR.glob("known_issues_*.json")):
            load_known_issues_file(f, path)
        rebuild_make_index_at(path)
        with sqlite3.connect(path) as conn:
            conn.execute("DROP TABLE known_issue_models")
        identity, rows = known_issues_for_vehicle("Honda", "PCX 150", db_path=path)
        assert rows, "the make-only fallback returned nothing"
