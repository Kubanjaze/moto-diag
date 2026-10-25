"""Phase 389 — the Science Officer: Step 0 from a mission, counts by script.

What must hold: every count in the report shows the query that made it
(P3 holds by construction, 257's census shape); what the model reads is
bounded (257's candidates shape); a report that counts things in its prose
gets one corrective call and then stops; the prompt is saved verbatim when
the phase has none. Model replies are hand-written fixtures; git is real.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = SKILL / "fixtures" / "scout"
sys.path.insert(0, str(SKILL))

import plan_check  # noqa: E402
import rank_call  # noqa: E402
import scout  # noqa: E402
from test_phase388_dispatcher import claude_json  # noqa: E402

TERMS = json.loads((FIX / "terms_good.json").read_text())
GOOD = json.loads((FIX / "assess_good.json").read_text())
COUNTED = json.loads((FIX / "assess_counts_in_prose.json").read_text())
ROW = "| 385 | The push token's own write | 🚧 | Steps. |"
MISSION = "Add device_tokens.last_seen_at to SERVER_WRITES.\n\n<!-- fleet-trial -->"


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


class Replies:
    def __init__(self, *structured):
        self.queue = [claude_json(s, model=rank_call.HAIKU) for s in structured]
        self.calls: list[list[str]] = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, self.queue.pop(0), "")


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "clone"
    (r / "src" / "motodiag" / "push").mkdir(parents=True)
    (r / "src" / "motodiag" / "push" / "registry.py").write_text(
        "def register_token():\n    # refreshes last_seen_at\n    return 'last_seen_at'\n")
    (r / "tests").mkdir()
    (r / "tests" / "test_push.py").write_text("def test_it():\n    assert 'last_seen_at'\n")
    (r / "docs" / "prompts").mkdir(parents=True)
    (r / "docs" / "ROADMAP.md").write_text(f"| Phase | Title | Status | Notes |\n|---|---|---|---|\n{ROW}\n")
    subprocess.run(["git", "init", "-q", "-b", "master", str(r)], check=True)
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(r), "-c", "user.name=t", "-c", "user.email=t@l", "commit",
                    "-qm", "x"], check=True)
    return r


@pytest.fixture
def mobile(tmp_path):
    m = tmp_path / "mobile"
    (m / "src").mkdir(parents=True)
    (m / "src" / "push.ts").write_text("// last_seen_at\n")
    subprocess.run(["git", "init", "-q", str(m)], check=True)
    subprocess.run(["git", "-C", str(m), "add", "-A"], check=True)
    return m


class TestTheCensus:
    def test_counts_per_area_with_the_mobile_repository(self, repo, mobile):
        rows = scout.census(repo, ["last_seen_at"], mobile)
        assert rows == [{"term": "last_seen_at", "counts": {"src": 2, "tests": 1, ".claude": 0,
                                                            "docs": 0, "mobile src": 1}}]

    def test_without_the_mobile_repository(self, repo):
        assert "mobile src" not in scout.census(repo, ["last_seen_at"], None)[0]["counts"]

    def test_the_table_shows_its_query_so_p3_holds(self, repo, mobile):
        table = scout.census_table(scout.census(repo, ["last_seen_at", "nowhere_at_all"], mobile))
        assert "`git grep -c -i -F -e <term> -- <area>`" in table
        assert plan_check.unshown_counts(table) == []

    def test_a_table_with_no_query_would_fail_p3(self):
        """The control: the same row with its lead paragraph gone."""
        bare = "| term | src |\n|---|---|\n| `x` | 14 files |"
        assert plan_check.unshown_counts(bare)


class TestTheCandidates:
    def test_bounded_per_term_and_in_all(self, repo, monkeypatch):
        got = scout.candidates(repo, ["last_seen_at"])
        assert len(got) <= scout.PER_TERM and all(e["term"] == "last_seen_at" for e in got)
        assert {e["where"].split(":")[0] for e in got} == {"src/motodiag/push/registry.py",
                                                          "tests/test_push.py"}
        monkeypatch.setattr(scout, "MAX_CHARS", 40)
        assert sum(len(e["text"]) for e in scout.candidates(repo, ["last_seen_at"])) <= 40

    def test_excerpts_carry_the_lines_around_the_hit(self, repo):
        e = next(x for x in scout.candidates(repo, ["register_token"]))
        assert e["where"] == "src/motodiag/push/registry.py:1" and "refreshes" in e["text"]


class TestTheCalls:
    def test_terms_dedupes_and_has_no_tools(self, repo):
        run = Replies(TERMS)
        found, _ = scout.terms(MISSION, ROW, cwd=repo, run=run)
        assert found == ["last_seen_at", "SERVER_WRITES", "register_token"]
        cmd = run.calls[0]
        assert cmd[cmd.index("--tools") + 1] == "" and rank_call.HAIKU in cmd

    def test_terms_that_are_not_strings_stop(self, repo):
        with pytest.raises(rank_call.Stop, match="not a list of strings"):
            scout.terms(MISSION, ROW, cwd=repo, run=Replies(json.loads(
                (FIX / "terms_not_strings.json").read_text())))

    def test_counts_in_prose_get_one_more_call(self, repo):
        run = Replies(COUNTED, GOOD)
        v, calls = scout.assess(MISSION, ROW, "table", [], "", cwd=repo, run=run)
        assert v == GOOD and len(calls) == 2
        assert scout.RECOUNT in run.calls[1][2] and "14 files" in run.calls[1][2]

    def test_a_bare_phase_number_is_a_count_to_the_checker(self, repo):
        """Phase 389, bug fix #1: the trial's first report said "No row for
        385 exists", which P3 reads as a count. The brief and the corrective
        call both say to write the word Phase before a phase number."""
        bare = json.loads((FIX / "assess_bare_phase_number.json").read_text())
        assert plan_check.unshown_counts(bare["reason"])
        assert not plan_check.unshown_counts(bare["reason"].replace("for 385", "for Phase 385"))
        assert '"Phase 385", never "385" alone' in " ".join(scout.ASSESS_BRIEF.split())
        run = Replies(bare, GOOD)
        scout.assess(MISSION, ROW, "table", [], "", cwd=repo, run=run)
        assert '"Phase 385"' in run.calls[1][2] and "385 exists" in run.calls[1][2]

    def test_counts_in_prose_twice_is_a_stop(self, repo):
        with pytest.raises(rank_call.Stop, match="no query"):
            scout.assess(MISSION, ROW, "table", [], "", cwd=repo, run=Replies(COUNTED, COUNTED))

    def test_no_classification_is_a_stop(self, repo):
        with pytest.raises(rank_call.Stop, match="no classification"):
            scout.assess(MISSION, ROW, "t", [], "", cwd=repo, run=Replies(json.loads(
                (FIX / "assess_no_classification.json").read_text())))


class TestTheReport:
    def test_end_to_end_writes_the_report_and_the_prompt(self, repo, mobile):
        written = scout.run_scout("385", "Phase 385: the push token's own write", 12, MISSION, ROW,
                                  clone=repo, run=Replies(TERMS, GOOD), mobile=mobile)
        assert written == ["docs/phases/in_progress/385_step0.md",
                           "docs/prompts/385_the_push_token_s_own_write.txt"]
        text = (repo / written[0]).read_text()
        assert "Classification: **extension.**" in text and "| `last_seen_at` |" in text
        assert plan_check.unshown_counts(text) == [], "P3 fails on the Science Officer's report"
        m = re.search(r"^\W*Classification\W*\s*(\w+)", text, re.M | re.I)
        assert m.group(1).lower() == "extension"           # what P4 reads
        assert (repo / written[1]).read_text() == MISSION + "\n"

    def test_an_existing_prompt_is_kept(self, repo, mobile):
        (repo / "docs" / "prompts" / "385_already.txt").write_text("The operator's.\n")
        written = scout.run_scout("385", "Phase 385: x", 12, MISSION, ROW, clone=repo,
                                  run=Replies(TERMS, GOOD), mobile=mobile)
        assert written == ["docs/phases/in_progress/385_step0.md"]
        assert (repo / "docs" / "prompts" / "385_already.txt").read_text() == "The operator's.\n"

    def test_a_reshape_is_written_as_found(self, repo):
        """The XO's P4 then sends it to the Admiral (387)."""
        written = scout.run_scout("385", "Phase 385: x", 12, MISSION, ROW, clone=repo,
                                  run=Replies(TERMS, {**GOOD, "classification": "reshape"}),
                                  mobile=None)
        assert "Classification: **reshape.**" in (repo / written[0]).read_text()

    @pytest.mark.parametrize("title,expected", [
        ("Phase 389A: 385's ROADMAP row", "385_s_roadmap_row"),
        ("a title with many more than six words in it", "a_title_with_many_more_than"),
        ("!!!", "mission"),
    ])
    def test_slug(self, title, expected):
        assert scout.slug(title) == expected
