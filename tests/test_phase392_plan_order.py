"""Phase 392 — the plan of record, read exactly (`plan_order.py`).

The real "Next, in order" list and `docs/decisions.md`'s Covers column read
with nothing wrong; each refusal of `check` fires on its own known-bad copy
of the real files; `bearing` and `cite_line` give a rank what bears on its
phase; `answer` matches one covering K-id and never a rule-1 stop (K50).
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
import plan_order as P  # noqa: E402

FILES = (P.PLAN, P.DECISIONS, "docs/ROADMAP.md", *P.TRIAGE_REPORTS)


@pytest.fixture
def copy(tmp_path):
    for rel in FILES:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    return tmp_path


def edit(root: pathlib.Path, rel: str, old: str, new: str) -> None:
    p = root / rel
    text = p.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{old!r} occurs {text.count(old)} times in {rel}"
    p.write_text(text.replace(old, new), encoding="utf-8")


class TestTheRealRecord:
    def test_the_list_and_the_covers_column_read_exactly(self):
        assert P.check(ROOT) == []

    def test_the_list_is_the_plans_order(self):
        order = P.parse_order((ROOT / P.PLAN).read_text(encoding="utf-8"))
        assert [e.phase for e in order.entries] == ["392", "303", "348", "345", "343", "371",
                                                      "372", "330", "334", "344", "210"]
        assert order.as_of == ("2026-10-27", "K48")

    def test_392_is_a_builders_and_303_348_need_nothing(self):
        e = {x.phase: x for x in P.parse_order((ROOT / P.PLAN).read_text()).entries}
        assert (e["392"].kind, e["392"].built_by) == ("fleet", "builder")
        assert e["303"].need is None and e["348"].need is None
        assert e["345"].need == "an outside account" and e["371"].need == "a fork"
        assert e["334"].need == "an outside person"

    def test_every_decision_has_a_covers_line(self):
        rows = P.decisions((ROOT / P.DECISIONS).read_text())
        assert [d.kid for d in rows] == [f"K{n}" for n in range(32, 32 + len(rows))]
        assert all(d.covers for d in rows)

    def test_first_shop_is_wave_1(self):
        assert P.first_shop((ROOT / P.PLAN).read_text()) == [
            "382", "345", "343", "303", "348", "371", "372", "330", "334", "344", "210"]


class TestCheckRefuses:
    @pytest.mark.parametrize("rel,old,new,why", [
        (P.PLAN, "## Next, in order\n", "## The order\n", "has no '## Next, in order'"),
        (P.PLAN, "As of 2026-10-27, K48.", "As of now.", "no 'As of"),
        (P.PLAN, "As of 2026-10-27, K48.", "As of 2026-10-28, K48.", "no entry under"),
        (P.PLAN, "As of 2026-10-27, K48.", "As of 2026-10-27, K99.", "K99, which does not"),
        (P.PLAN, "As of 2026-10-27, K48.", "As of 2026-10-27, K47.", "does not cite K47"),
        (P.PLAN, "| 2 | 303 | shop | fleet | nothing |", "| 2 | 303 | shop | robots | nothing |",
         "its builder 'robots'"),
        (P.PLAN, "| 3 | 348 | shop | fleet | nothing |", "| 3 | 348 | store | fleet | nothing |",
         "its kind 'store'"),
        (P.PLAN, "| 8 | 330 | shop | fleet | nothing |", "| 8 | 330 | shop | fleet | a favour |",
         "its need 'a favour'"),
        (P.PLAN, "| 8 | 330 | shop | fleet | nothing |",
         "| 8 | 330 | shop | fleet | an outside account |", "its need"),
        (P.PLAN, "| 11 | 210 | shop | fleet | nothing | Wave 1, item 6 · K48 |",
         "| 11 | 210 | shop | fleet | nothing | Wave 1, item 6 |", "cites no K-id"),
        (P.PLAN, "| 11 | 210 |", "| 11 | 999 |", "phase 999 has no ROADMAP row"),
        (P.PLAN, "| 11 | 210 |", "| 11 | 303 |", "phase 303 is listed twice"),
        (P.PLAN, "| 11 | 210 |", "| 12 | 210 |", "not numbered"),
        (P.PLAN, "Wave 1, item 6 · K48", "Wave 1, item 6 · K98", "cites K98"),
        (P.DECISIONS, "| K51 | 2026-10-27 |", "| K51 | 2026-10-27 |", None),
    ], ids=["no-section", "no-as-of", "as-of-undated", "as-of-unresolved", "as-of-uncited",
            "builder", "kind", "need-unknown", "need-without-what", "entry-no-kid",
            "phase-no-row", "phase-twice", "numbering", "entry-kid-unresolved", "control"])
    def test_each_on_its_own_copy(self, copy, rel, old, new, why):
        edit(copy, rel, old, new)
        fails = P.check(copy)
        if why is None:
            assert fails == []                           # the copy itself is clean
        else:
            assert any(why in f for f in fails), fails

    @pytest.mark.parametrize("covers,why", [
        ("stop=fork subject=303", "a rule-1 stop"),
        ("stop=live-database-change subject=303", "a rule-1 stop"),
        ("stop=test-cannot-be-green subject=303", "a rule-1 stop"),
        ("stop=lunch subject=303", "not one of"),
        ("when it seems right", "is not 'no stop'"),
        ("", "is not 'no stop'"),
    ])
    def test_a_covers_line_that_is_not_a_lookup(self, copy, covers, why):
        text = (copy / P.DECISIONS).read_text()
        k51 = next(ln for ln in text.splitlines() if ln.startswith("| K51 |"))
        edit(copy, P.DECISIONS, k51, k51[: k51.rindex("| no stop |")] + f"| {covers} |")
        assert any(f.startswith("K51:") and why in f for f in P.check(copy)), P.check(copy)


class TestNext:
    def test_the_builders_phase_is_next_while_it_is_open(self):
        order = P.parse_order((ROOT / P.PLAN).read_text())
        rows = {"392": ("🚧", "x"), "303": ("🔲", "y")}
        assert P.next_entry(order, rows).phase == "392"

    def test_after_392_closes_303_is_next_then_348(self):
        order = P.parse_order((ROOT / P.PLAN).read_text())
        assert P.next_entry(order, {"392": ("✅", "")}).phase == "303"
        assert P.next_entry(order, {"392": ("✅", ""), "303": ("✅", "")}).phase == "348"

    def test_all_done_is_none(self):
        order = P.parse_order((ROOT / P.PLAN).read_text())
        assert P.next_entry(order, {e.phase: ("✅", "") for e in order.entries}) is None


class TestBearing:
    def test_303_gets_its_entry_its_dated_changes_and_k43(self):
        b = P.bearing(ROOT, "303")
        assert b.entry.n == 2
        assert {d for d, _, _ in b.changes} >= {"2026-10-26", "2026-10-26, later"}
        assert "K43" in [d.kid for d in b.decisions]
        line = P.cite_line(ROOT, "303")
        assert "'Next, in order' #2" in line and "K43" in line

    def test_392_cites_k44(self):
        assert "K44" in P.cite_line(ROOT, "392")
        assert "392 goes between 391 and 303/348" in P.brief_block(ROOT, "392")

    def test_a_phase_nothing_names_says_so(self):
        assert "names this phase nowhere" in P.cite_line(ROOT, "999")
        assert "no entry puts it in order" in P.brief_block(ROOT, "999")

    @pytest.mark.parametrize("text,phase,named", [
        ("303 and 348", "303", True), ("(303/348)", "348", True), ("phase-303-row", "303", True),
        ("3030", "303", False), ("K303", "303", False), ("391_step0.md", "391", False),
        ("v3.03", "303", False), ("389A", "389", False), ("389A's row", "389A", True),
    ])
    def test_names_is_a_number_of_its_own(self, text, phase, named):
        assert P.names(text, phase) is named


class TestAnswer:
    def covered(self, copy, covers: str, kid: str = "K51"):
        text = (copy / P.DECISIONS).read_text()
        row = next(ln for ln in text.splitlines() if ln.startswith(f"| {kid} |"))
        edit(copy, P.DECISIONS, row, row[: row.rindex("| no stop |")] + f"| {covers} |")

    def test_the_real_record_answers_nothing_yet(self):
        for kind in P.ANSWERABLE + P.RULE1_KINDS:
            assert P.answer(ROOT, kind, "303") is None

    def test_one_covering_k_id_answers_its_kind_and_subject(self, copy):
        self.covered(copy, "stop=third-bug-fix subject=303,348")
        d = P.answer(copy, "third-bug-fix", "348")
        assert d is not None and d.kid == "K51" and d.words.startswith('"4: LimitNOFILE')
        assert P.answer(copy, "third-bug-fix", "345") is None          # another subject
        assert P.answer(copy, "guard-blocked-twice", "303") is None    # another kind

    def test_a_rule_1_kind_is_never_answered(self, copy):
        self.covered(copy, "stop=fork subject=303")
        assert P.answer(copy, "fork", "303") is None

    def test_two_covering_k_ids_answer_nothing(self, copy):
        self.covered(copy, "stop=third-bug-fix subject=303", "K51")
        self.covered(copy, "stop=third-bug-fix subject=303", "K50")
        assert P.answer(copy, "third-bug-fix", "303") is None
