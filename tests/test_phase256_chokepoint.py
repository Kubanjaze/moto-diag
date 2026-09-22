"""Phase 256 — one chokepoint, and the fixtures that stop it being split.

Phase 255 filtered the door it knew about. Three more were found afterwards,
one at a time, each by someone noticing. This file asserts, per door, what
each machine must and must not receive — so the next door cannot be added,
or quietly unwired, without a named machine failing.

**Read the door-4 block with its history.** Door 4 leaks nothing today, and
it is safe for the wrong reason: it matches `LOWER(make) = ?`, exact string
equality, and nine of the eleven transmission-scoped rows carry
`make = "Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine"`, which is never
equal to `"yamaha"`. The 244C-244I substring defect on that door is acting as
accidental protection.

**Routing it through the resolver is what creates the exposure.** The moment
door 4 matches through the junction, an R1 becomes eligible for all nine. So
these fixtures are committed **before** the rewire: they pass now (nothing
scoped matches), they pass after (the filter withholds), and **they fail in
between** — which is what makes "filter and rewire land together" enforced
rather than written down.

A fixture green on both sides cannot tell the two reasons apart on its own,
so the rewire commit carries a positive control: remove the filter call,
watch these fail, restore it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"

#: The D8 matrix. `keeps_scoped` is the whole point: True means this machine
#: is entitled to transmission-scoped rows, False means receiving even one is
#: a defect. Each is named, so deleting one is a visible edit.
MACHINES = [
    ("Honda", "GL1800 Gold Wing", 2020, False, "ambiguous: manual or DCT, never CVT"),
    ("Honda", "CBR1000RR", 2019, False, "unknown: six-speed sportbike"),
    ("Honda", "Grom", 2022, False, "unknown: five-speed, the Step 0 poster child"),
    ("Honda", "Africa Twin", 2021, False, "ambiguous, column NULL: manual or DCT"),
    ("Yamaha", "YZF-R1", 2016, False, "unknown: six-speed, and a LIVE vehicle"),
    ("Kawasaki", "Ninja 400", 2020, False, "the isolating control: never had them"),
    ("Honda", "PCX 150", 2020, True, "model-sourced cvt: MUST keep them"),
]


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p256") / "p256.db")
    init_db(path)
    for f in sorted(SEED.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    with sqlite3.connect(path) as conn:
        for i, (mk, md, yr, _keep, _why) in enumerate(MACHINES, start=8100):
            conn.execute(
                "INSERT INTO vehicles (id, make, model, year) VALUES (?,?,?,?)",
                (i, mk, md, yr),
            )
    reset_settings()
    return path


def scoped_ids(db_path: str) -> set[int]:
    """Every row that declares anything on the transmission axis."""
    with sqlite3.connect(db_path) as conn:
        return {r[0] for r in conn.execute(
            "SELECT id FROM known_issues WHERE applicability IS NOT NULL"
        )}


def vehicle_id_of(db_path: str, make: str, model: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT id FROM vehicles WHERE make = ? AND model = ?", (make, model)
        ).fetchone()[0]


# --- the doors, each as the product actually calls it ----------------------
#
# Each returns (before_filter, after_filter) as id sets, so a test can ask
# what the FILTER did rather than what the twelve-row cap did. That
# distinction is not pedantry: a PCX 150 retrieves 165 rows of which 8 are
# transmission-scoped, and none of the 8 reaches the final twelve, because
# Phase 244S caps the prompt and PCX-specific rows outrank a generic CVT
# layer. Asserting "the PCX's prompt contains a scoped row" would fail on
# correct behaviour and tempt someone to loosen the filter to satisfy it.
# The property that matters is that the filter WITHHOLDS NOTHING from a
# machine entitled to them.


def _no_candidate_cap(db_path: str) -> int:
    """Every row that could possibly match — the corpus itself, not a number.

    This was `GUARD_FETCH = 400`, and 400 was the door-2 problem wearing a
    different hat: safe by arithmetic until the corpus grows past it, at
    which point a scoped row could sit beyond the fetch and the guard would
    pass on leaking code without anyone touching the guard.

    Measured before removing it, on a 1,045-row corpus: the worst
    unfiltered match count across the fixture machines is **165 rows, 16%
    of the corpus**, and fetching the whole corpus costs **17.6 ms against
    17.6 ms** for the capped fetch — the cap was doing no work at all. So
    there is no cost to removing it, and the bound is now definitional
    rather than chosen.

    **The only cap in this file is post-filter**, where a cap belongs: it
    decides presentation, never correctness.
    """
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0])


def door1_diagnose(db_path, make, model, year):
    """The diagnose/code path. Asserted pre-cap.

    The product caps this at twelve (`KNOWN_ISSUE_PROMPT_LIMIT`). The guard
    does not, because a cap is a presentation decision: raise it tomorrow
    and a property proved through it stops being proved.
    """
    from motodiag.knowledge.retrieval import rows_for_machine
    from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

    _identity, raw = known_issues_for_vehicle(make, model, db_path=db_path,
                                              limit=_no_candidate_cap(db_path))
    kept = rows_for_machine(raw, make=make, model=model, purpose="prompt",
                            db_path=db_path).rows
    return {r["id"] for r in raw}, {r["id"] for r in kept}


def door2_ask(db_path, make, model, year):
    """The video /ask path. Asserted pre-cap, and that matters here.

    The endpoint fetches twenty-five. A Gold Wing's scoped rows start at
    position 56, so at twenty-five this door cannot leak them **whatever
    the filter does** — safety by arithmetic, not by design, and it
    evaporates the day someone raises the limit. The guard therefore fetches
    wide and asserts that the FILTER withholds them.
    """
    from motodiag.knowledge.retrieval import rows_for_machine
    from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

    _identity, issues = known_issues_for_vehicle(make, model, db_path=db_path,
                                                 limit=_no_candidate_cap(db_path))
    kept = rows_for_machine(issues, make=make, model=model, purpose="prompt",
                            db_path=db_path).rows
    return {r["id"] for r in issues}, {r["id"] for r in kept}


def door4_priority(db_path, make, model, year):
    """Asserted BEFORE the five-row cap, deliberately.

    The first version of this helper read `_find_kb_matches_safe`, which
    caps at five. That made the tripwire useless: with the filter removed,
    a Gold Wing's scoped rows sit at resolver positions 56, 64, 75, 81, 113
    and 115, so the cap hid every one and the guard passed on leaking code.
    """
    from motodiag.shop.priority_scorer import _kb_candidates_for_vehicle
    from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

    vid = vehicle_id_of(db_path, make, model)
    _identity, raw = known_issues_for_vehicle(make, model, db_path=db_path,
                                              limit=_no_candidate_cap(db_path))
    after = {r["id"] for r in _kb_candidates_for_vehicle(vid, db_path)}
    return {r["id"] for r in raw}, after


def door3_predict(db_path, make, model, year):
    """`predict_failures` AS THE PRODUCT CALLS IT.

    The first version of this helper rebuilt the candidate pool here and
    called `rows_for_machine` on it. That tested the filter and not the
    wiring: bypassing the filter inside `predict_failures` left all 60
    assertions green. A guard that passes whether or not the product is
    wired is the same defect as the cap-masking two doors ago, and the same
    defect Phase 254 shipped.

    So it calls the real function. `before` is the unfiltered candidate
    pool, reconstructed the way `predict_failures` builds it, purely so the
    test can show the scoped rows WERE reachable.

    `_MAX_PREDICTIONS` caps the output at 50, which could in principle hide
    a scoped row ranked below that — so this is paired with a source-level
    wiring assertion in `TestTheDoorsAreActuallyWired`. Neither alone is
    enough.
    """
    from motodiag.advanced.predictor import predict_failures
    from motodiag.knowledge.issues_repo import search_known_issues

    pool = {}
    for issue in search_known_issues(make=make, model=model, db_path=db_path):
        pool[issue["id"]] = issue
    for issue in search_known_issues(make=make, model=None, db_path=db_path):
        pool.setdefault(issue["id"], issue)

    preds = predict_failures(
        {"make": make, "model": model, "year": year, "mileage": 20000},
        horizon_days=None, db_path=db_path,
    )
    return set(pool), {p.issue_id for p in preds}


def door3_filter_only(db_path, make, model, year):
    """Door 3's candidate pool, filter applied, nothing else.

    `predict_failures` drops rows for several reasons that have nothing to
    do with applicability: a 50-prediction cap, a horizon window, a
    severity floor, and an onset model that simply does not fire for every
    row. So "did this machine lose a scoped row?" cannot be asked of its
    output — a PCX 150 legitimately loses six scoped rows to the cap and
    the onset model, and asserting otherwise would demand the filter be
    loosened to satisfy a question it was never answering.

    The negative direction ("did a Gold Wing RECEIVE one?") is asked of the
    product output, because a leak must be caught wherever it surfaces.
    The positive direction is asked here, of the filter alone.
    """
    from motodiag.knowledge.issues_repo import search_known_issues
    from motodiag.knowledge.retrieval import rows_for_machine

    pool = {}
    for issue in search_known_issues(make=make, model=model, db_path=db_path):
        pool[issue["id"]] = issue
    for issue in search_known_issues(make=make, model=None, db_path=db_path):
        pool.setdefault(issue["id"], issue)
    kept = rows_for_machine(list(pool.values()), make=make, model=model,
                            purpose="prediction", db_path=db_path, record=False).rows
    return set(pool), {r["id"] for r in kept}


DOORS = {
    "1-diagnose": door1_diagnose,
    "2-video-ask": door2_ask,
    "3-predict-failures": door3_predict,
    "4-priority-scorer": door4_priority,
}


#: Split rather than skipped. A conditional `pytest.skip` inside a
#: parametrised matrix produces a skip count that reads as "18 tests did not
#: run" — and this project has a standing rule that a skip must stop a
#: close-out rather than vanish into a summary line. Two lists, no skips.
NOT_ENTITLED = [m for m in MACHINES if not m[3]]
ENTITLED = [m for m in MACHINES if m[3]]
_ids = lambda ms: [f"{m}-{d}" for m, d, _y, _k, _w in ms]


#: For the "nothing withheld" direction only, door 3 is probed at the filter
#: rather than at its output. See `door3_filter_only` for why.
WITHHOLD_PROBES = dict(DOORS)
WITHHOLD_PROBES["3-predict-failures"] = door3_filter_only


@pytest.mark.parametrize("door", sorted(DOORS))
class TestEveryDoorRespectsApplicability:
    @pytest.mark.parametrize("make,model,year,keeps_scoped,why", NOT_ENTITLED,
                             ids=_ids(NOT_ENTITLED))
    def test_a_machine_without_the_transmission_receives_no_scoped_row(
        self, db, door, make, model, year, keeps_scoped, why
    ):
        """The negative. Not 'fewer rows' — zero, named machine by named machine."""
        _before, after = DOORS[door](db, make, model, year)
        leaked = after & scoped_ids(db)
        assert leaked == set(), (
            f"door {door}: {make} {model} ({why}) received scoped row(s) "
            f"{sorted(leaked)}"
        )

    @pytest.mark.parametrize("make,model,year,keeps_scoped,why", MACHINES,
                             ids=_ids(MACHINES))
    def test_the_door_returns_something_at_all(
        self, db, door, make, model, year, keeps_scoped, why
    ):
        """Positive control for the negative above.

        Every "receives no scoped row" assertion also passes on a door that
        returns nothing whatsoever — which is precisely what door 4 did for
        its entire existence until F126 was fixed today. Without this, the
        negatives would be untestable by construction.
        """
        before, _after = DOORS[door](db, make, model, year)
        assert before, f"door {door} retrieved nothing at all for {make} {model}"

    @pytest.mark.parametrize("make,model,year,keeps_scoped,why", ENTITLED,
                             ids=_ids(ENTITLED))
    def test_an_entitled_machine_has_nothing_withheld(
        self, db, door, make, model, year, keeps_scoped, why
    ):
        """The filter must take nothing from a machine that may have it."""
        before, after = WITHHOLD_PROBES[door](db, make, model, year)
        scoped = scoped_ids(db)
        lost = (before & scoped) - after
        assert lost == set(), (
            f"door {door}: {make} {model} lost scoped row(s) {sorted(lost)} "
            "— the filter withheld from a machine entitled to them"
        )


class TestTheDoorsAreActuallyWired:
    """The behavioural fixtures above can pass on an unwired door.

    Door 3's output is capped at 50 and door 4's at five, so a scoped row
    ranked below the cap is invisible to a behavioural assertion. These
    read the source, through `code_of` so comments and docstrings are
    blanked — Phase 244G forbids raw-source matching precisely because a
    string in a comment keeps a guard green after the code is deleted.
    """

    @pytest.mark.parametrize("module_path,door", [
        ("motodiag.cli.diagnose", "1-diagnose"),
        ("motodiag.api.routes.videos", "2-video-ask"),
        ("motodiag.advanced.predictor", "3-predict-failures"),
        ("motodiag.shop.priority_scorer", "4-priority-scorer"),
    ])
    def test_the_door_calls_the_chokepoint(self, module_path, door):
        import importlib
        from support.source_guards import code_of

        code = code_of(importlib.import_module(module_path))
        assert "rows_for_machine(" in code, (
            f"door {door} ({module_path}) does not call the chokepoint"
        )


class TestTheKawasakiControlIsUnmoved:
    """Step 0 isolated the cause with Kawasaki; it must stay at zero."""

    @pytest.mark.parametrize("door", sorted(DOORS))
    def test_zero_before_and_after(self, db, door):
        before, after = DOORS[door](db, "Kawasaki", "Ninja 400", 2020)
        assert before & scoped_ids(db) == set()
        assert after & scoped_ids(db) == set()


# ---------------------------------------------------------------------------
# The structural guard — D5
# ---------------------------------------------------------------------------

#: Modules allowed to name `known_issues` in SQL. Everything else must go
#: through the chokepoint. Pinned as a set with reasons, not a count: eleven
#: schema pins accumulated one reasonable exception at a time (F124), and so
#: did four retrieval doors.
SQL_ALLOWED = {
    "knowledge/retrieval.py": "the chokepoint itself — it sizes the fetch",
    "knowledge/issues_repo.py": "the repo layer itself — the SQL lives here",
    "knowledge/vehicle_resolver.py": "the resolver's tiered retrieval",
    "knowledge/marques.py": "rebuilds the derived make junction",
    "knowledge/models.py": "rebuilds the derived model junction",
    "knowledge/loader.py": "seed writes",
    "core/migrations.py": "schema history; one-time, not a read path",
}

_KEY_PIAGGIO = "Piaggio's belt limit is three different numbers, and"
_KEY_REGULATOR = "What the regulator record shows for scooter CVTs — o"

#: Rows whose junction names a model their own `applicability` excludes.
#:
#: **This check is permanent, not phase-scoped.** It does not expire with
#: Phase 256 and it did not become 255B's to delete. Any NEW entry fails
#: the suite and has to be argued for, because the failure it describes —
#: a row written FOR a machine and then withheld FROM it — is invisible to
#: every other guard here. Those ask "does a machine get rows it may not
#: have"; this asks the opposite, and only a refuter thought to.
#:
#: The operator's decision, 2026-09-21: there is deliberately NO "an
#: explicit model match overrides the axis filter" rule, because that is
#: string-naming as authority — the exact pattern this axis exists to
#: replace. A row naming a machine is a claim; the lookup is evidence.
#:
#: **Phase 255B resolved the Kymco/Filly entry** by withdrawing the claim,
#: not by granting the row. 4609's model column dropped `Filly LX 50`, so
#: the row no longer names a machine it excludes and the key no longer has
#: anything to describe. The Filly's retrieval is UNCHANGED: it is absent
#: from the transmission lookup, resolves `unknown`, and a {cvt} row is
#: withheld from it before and after. No lookup entry, no override.
#: Entries are deleted when they resolve rather than re-worded, because
#: the guard asserts set equality against what it finds.
KNOWN_SELF_EXCLUDING = {
    (_KEY_PIAGGIO, "Piaggio Beverly 250"):
        "Named by the row, no document on disk. **Stays as-is** — "
        "F119 closed-unobtainable, operator's decision 2026-09-21.",
    (_KEY_REGULATOR, "Vespa 946"):
        "Named by the row, no document on disk. **Stays as-is** — "
        "F119 closed-unobtainable, operator's decision 2026-09-21.",
    (_KEY_REGULATOR, "SYM Symba"):
        "A genuine contradiction ON DISK: 4615 declares {'transmission': "
        "['cvt']} and names the Symba, which this phase's own lookup "
        "classifies `semi_auto_centrifugal` from SYM's manual ('Wet "
        "multi-plate type, auto centrifugal clutch'). Phase 255 flagged "
        "4615 as carrying a general half wider than CVT and deferred the "
        "split to 255B; this is what that deferral costs. "
        "**Resolution: the 255B split settles it** — the general half stops "
        "being declared `cvt` and the Symba naming becomes correct.",
}


def _sql_offenders() -> list[str]:
    """Modules naming known_issues in SQL, read via AST.

    AST, not grep: Phase 256's Step 0 positive control showed a grep misses
    dynamic table names, split string literals and multi-line SQL. `ast`
    joins adjacent literals for free.
    """
    import ast
    import re

    src_root = ROOT / "src" / "motodiag"
    pat = re.compile(r"\b(FROM|JOIN|INTO|UPDATE)\s+known_issues\b", re.I)
    out = []
    for f in sorted(src_root.rglob("*.py")):
        rel = str(f.relative_to(src_root))
        if rel in SQL_ALLOWED:
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            text = None
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
            elif isinstance(node, ast.JoinedStr):
                text = "".join(p.value for p in node.values
                               if isinstance(p, ast.Constant)
                               and isinstance(p.value, str))
            if text and pat.search(re.sub(r"\s+", " ", text)):
                out.append(f"{rel}:{node.lineno}")
    return sorted(set(out))


class TestNothingBypassesTheChokepoint:
    def test_no_module_outside_the_repo_layer_queries_known_issues(self):
        offenders = _sql_offenders()
        assert offenders == [], (
            "these modules query known_issues directly instead of going "
            "through knowledge/retrieval.py::rows_for_machine:\n  "
            + "\n  ".join(offenders)
        )

    def test_the_scanner_sees_a_planted_bypass(self, tmp_path):
        """Positive control. A guard never observed to fail is not a guard.

        Plants a real module inside the package — the shape door 4 had for
        its whole existence — and asserts the scanner reports it.
        """
        planted = ROOT / "src" / "motodiag" / "zz_planted_bypass.py"
        planted.write_text(
            "def leak(conn, make):\n"
            "    return conn.execute(\n"
            '        "SELECT * FROM known_issues WHERE make = ?", (make,)\n'
            "    ).fetchall()\n",
            encoding="utf-8",
        )
        try:
            assert any(o.startswith("zz_planted_bypass.py") for o in _sql_offenders()), (
                "the scanner did not see a planted raw query"
            )
        finally:
            planted.unlink()

    def test_the_scanner_sees_the_shapes_a_grep_would_miss(self, tmp_path):
        """The three blind spots Step 0's grep had, each planted."""
        shapes = {
            "dynamic": 'TBL = "known_issues"\n'
                       'def f(c):\n    return c.execute(f"SELECT * FROM {TBL}")\n',
            "split": 'def f(c):\n    return c.execute("SELECT * FROM "\n'
                     '                     "known_issues WHERE id = 1")\n',
            "multiline": 'def f(c):\n    return c.execute("""SELECT *\n'
                         '        FROM\n      known_issues""")\n',
        }
        for name, body in shapes.items():
            planted = ROOT / "src" / "motodiag" / f"zz_shape_{name}.py"
            planted.write_text(body, encoding="utf-8")
            try:
                seen = any(o.startswith(f"zz_shape_{name}.py") for o in _sql_offenders())
            finally:
                planted.unlink()
            if name == "dynamic":
                # An AST scan cannot see a table name that only exists at
                # runtime. Recorded rather than papered over: the dynamic
                # shape is caught by `test_no_dynamic_table_names` below.
                assert not seen
            else:
                assert seen, f"the {name} shape was missed"

    def test_no_dynamic_table_names_outside_the_repo_layer(self):
        """The one shape the AST scan cannot resolve, guarded separately.

        `f"SELECT * FROM {table}"` hides its target until runtime, so no
        AST scan can say what it reads.

        **Step 0 said there was one. There are four**, and Step 0's own
        dynamic search missed three of them for the same reason the first
        version of this test did: it looked for `FROM {`, and `{table}` is
        a FormattedValue that never appears in the literal text. The
        literal just ends with `"FROM "`. Step 0's eleven "hits" were prose
        in log messages and its one real find was luck.

        All four are safe, verified by reading every literal passed as the
        table argument — `intakes`, `customers`, `vehicles`, `work_orders`,
        `diagnostic_sessions`, `video_analyses` and so on. **`known_issues`
        is not among them in any of the four.** A fifth is a new door until
        someone proves otherwise.
        """
        import ast
        import re

        src_root = ROOT / "src" / "motodiag"
        # The table name is a FormattedValue, so it is NOT in the joined
        # literal text -- the literal simply ENDS with "FROM ". Matching on
        # "FROM {" finds nothing, which is how the first version of this
        # test saw zero of the one query that exists. Matching on "ends with
        # FROM" alone then found thirteen, twelve of them prose in log
        # messages. Both halves are needed: it must LOOK like SQL, and a
        # literal must end where a table name would go.
        looks_like_sql = re.compile(r"^\s*(SELECT|INSERT|DELETE|UPDATE|WITH)\b", re.I)
        ends_at_table = re.compile(r"\b(FROM|JOIN|INTO)\s*$", re.I)
        found = []
        for f in sorted(src_root.rglob("*.py")):
            rel = str(f.relative_to(src_root))
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.JoinedStr):
                    continue
                parts = [p.value for p in node.values
                         if isinstance(p, ast.Constant) and isinstance(p.value, str)]
                if not parts or not looks_like_sql.search("".join(parts)):
                    continue
                if any(ends_at_table.search(p) for p in parts):
                    found.append(f"{rel}:{node.lineno}")
        assert sorted(set(found)) == [
            "capture/stats.py:19",
            "shop/intake_repo.py:90",
            "shop/issue_repo.py:173",
            "shop/work_order_repo.py:112",
        ], f"new dynamic table-name query: {sorted(set(found))}"


def _key_of(title: str) -> str:
    """Stable identity for a row: a title prefix, not its id.

    Row ids are assigned in seed order, so the operator's database says
    4609 where a fresh fixture says 158. Keying a pinned set on ids would
    make this guard pass or fail depending on which database it ran
    against — the guard would be measuring the fixture.
    """
    return " ".join(str(title or "").split())[:52]


class TestNoRowExcludesAMachineItNames:
    """A row that names a machine and is then withheld from it.

    Found by a refuter attacking the door-3 change, not by this suite —
    worth recording, because the suite was asking "does a machine get rows
    it may not have" and never "does a machine miss rows written FOR it".
    """

    def test_the_self_excluding_set_is_exactly_the_known_four(self, db):
        from motodiag.knowledge.applicability import row_applies
        from motodiag.knowledge.transmission import resolve_transmission

        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            rows = {r["id"]: dict(r) for r in conn.execute(
                "SELECT id, title, make, model, applicability FROM known_issues "
                "WHERE applicability IS NOT NULL")}
            found = set()
            for iid, row in rows.items():
                for (model,) in conn.execute(
                    "SELECT model FROM known_issue_models WHERE issue_id = ?", (iid,)
                ):
                    makes = [m.strip() for m in (row["make"] or "").split(",")]
                    res = next(
                        (resolve_transmission(mk, model) for mk in makes
                         if resolve_transmission(mk, model).provenance == "model-sourced"),
                        resolve_transmission(makes[0] if makes else "", model),
                    )
                    if not row_applies(row, "transmission", res.candidates):
                        # keyed on the title, because row ids are
                        # seed-order-relative and differ between a fresh
                        # fixture and the operator's database
                        found.add((_key_of(row["title"]), model))
        assert found == set(KNOWN_SELF_EXCLUDING), (
            "the set of rows naming a model they exclude has changed.\n"
            f"  new:  {sorted(found - set(KNOWN_SELF_EXCLUDING))}\n"
            f"  gone: {sorted(set(KNOWN_SELF_EXCLUDING) - found)}"
        )
