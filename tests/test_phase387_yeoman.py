"""Phase 387 — the Yeoman, `yeoman.py`: `decide` and `digest`.

`decide`: one row, the next K-id, the words verbatim; a K-id that does not
resolve is refused. "Resolve" is read from the three files that define
K-ids, never a repo-wide grep (K75 is a BMW).

`digest`: one day by time window. The fixture repository's commits carry
chosen dates, so "a row changed the day before is out, one changed that
day is in" is tested on real git history, not on a stub of it.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))

import rank_call  # noqa: E402
import yeoman  # noqa: E402

REPORT_A = """# Triage one

### K1. One command
Text.

- **K2 — park.** Text.
"""
REPORT_B = """# Triage two

### K3. A deploy order
"""
DECISIONS = """# Decisions

| K-id | Date | The operator's words | The check it became |
|---|---|---|---|
| K4 | 2026-10-08 | "first" | No check. |
"""


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "docs" / "reports").mkdir(parents=True)
    (root / yeoman.TRIAGE_REPORTS[0]).write_text(REPORT_A)
    (root / yeoman.TRIAGE_REPORTS[1]).write_text(REPORT_B)
    (root / yeoman.DECISIONS).write_text(DECISIONS)
    (root / "docs" / "other.md").write_text("### K75. A BMW, not a decision\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_real.py").write_text("")
    return root


def rows(root):
    return [ln for ln in (root / yeoman.DECISIONS).read_text().splitlines()
            if yeoman._KID_ROW.match(ln)]


class TestDecide:
    def test_the_k_ids_come_from_the_three_files_only(self, repo):
        assert yeoman.defined_kids(repo) == {1, 2, 3, 4}

    def test_one_row_with_the_next_k_id_and_the_words_verbatim(self, repo):
        rc = yeoman.decide("keep it | simple, as K3 says", "`tests/test_real.py`", root=repo,
                           date="2026-10-22", out=lambda s: None)
        assert rc == 0
        assert rows(repo)[-1] == ('| K5 | 2026-10-22 | "keep it \\| simple, as K3 says" | '
                                  '`tests/test_real.py` |')
        assert len(rows(repo)) == 2

    @pytest.mark.parametrize("kwargs,why", [
        ({"words": "as K75 said", "check": "No check."}, "do not resolve: K75"),
        ({"words": "fine", "check": "same as K9"}, "do not resolve: K9"),
        ({"words": "fine", "check": "No check.", "kid": "K9"}, "not the next K-id; the next is K5"),
        ({"words": "two\nlines", "check": "No check."}, "one line"),
        ({"words": "fine", "check": "`tests/no_such.py`"}, "do not exist: tests/no_such.py"),
        ({"words": " ", "check": "No check."}, "both the words"),
        ({"words": "fine", "check": "No check.", "date": "22/10/2026"}, "not YYYY-MM-DD"),
    ], ids=["unresolved-in-words", "unresolved-in-check", "wrong-kid", "newline", "missing-path",
            "no-words", "bad-date"])
    def test_refusals_write_nothing(self, repo, kwargs, why):
        seen: list[str] = []
        before = (repo / yeoman.DECISIONS).read_text()
        assert yeoman.decide(root=repo, out=seen.append, **kwargs) == 1
        assert any(why in s for s in seen), seen
        assert (repo / yeoman.DECISIONS).read_text() == before

    def test_the_real_file_resolves_k1_to_k39_with_no_gap(self):
        known = yeoman.defined_kids(ROOT)
        assert set(range(1, 40)) <= known


# ---------------------------------------------------------------- digest
TZ = dt.datetime.now().astimezone().tzinfo
DAY = dt.date(2026, 10, 22)


def commit(root, when: dt.datetime, msg: str):
    env = {**os.environ, "GIT_AUTHOR_DATE": when.isoformat(), "GIT_COMMITTER_DATE": when.isoformat(),
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", msg], check=True, env=env)


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


ROADMAP = "| Phase | Title | Status | Notes |\n|---|---|---|---|\n"
HANDOFF = "# Handoff\n\n## What is open\n\n- the thing left\n\n## What is next\n\n- the next row\n"


@pytest.fixture()
def history(tmp_path):
    root = tmp_path / "hist"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    day_before = dt.datetime.combine(DAY - dt.timedelta(days=1), dt.time(12), TZ)
    write(root, "docs/ROADMAP.md", ROADMAP + "| 901 | Old | 🚧 | Started. |\n")
    write(root, "docs/FOLLOWUPS.md", "### F1\n\n**The first finding**\n\n### F2 — CLOSED by 900\n")
    commit(root, day_before, "the day before")
    write(root, "docs/ROADMAP.md", ROADMAP + "| 901 | Old | ✅ | **CLOSED.** |\n"
                                             "| 902 | New | 🚧 | Started today. |\n")
    write(root, "docs/FOLLOWUPS.md", "### F1 — CLOSED by 901\n\n### F2 — CLOSED by 900\n\n"
                                     "### F3\n\n**A finding filed today**\n")
    write(root, "docs/handoffs/2026-10-22_901_closed.md", HANDOFF)
    commit(root, dt.datetime.combine(DAY, dt.time(15), TZ), "the day")
    write(root, "docs/ROADMAP.md", ROADMAP + "| 901 | Old | ✅ | **CLOSED.** |\n"
                                             "| 902 | New | ✅ | Closed tomorrow. |\n")
    commit(root, dt.datetime.combine(DAY + dt.timedelta(days=1), dt.time(9), TZ), "the day after")
    return root


def gh_issues(items):
    def run(cmd, **kw):
        if cmd[0] == "gh":
            label = cmd[cmd.index("--label") + 1]
            return subprocess.CompletedProcess(
                cmd, 0, json.dumps([i for i in items if label in [x["name"] for x in i["labels"]]]), "")
        raise AssertionError(cmd)
    return run


ISSUE_OPEN = {"number": 3, "title": "Sign in to the desktop", "url": "u3", "state": "OPEN",
              "updatedAt": "2026-10-01T10:00:00Z", "labels": [{"name": "needs-hands"}]}
ISSUE_OLD = {"number": 4, "title": "Closed long ago", "url": "u4", "state": "CLOSED",
             "updatedAt": "2026-10-01T10:00:00Z", "labels": [{"name": "needs-admiral"}]}


class TestTheWindow:
    def test_the_day_shows_what_changed_that_day_and_nothing_after(self, history):
        text = yeoman.facts(history, DAY, gh_issues([]))
        assert "**902** 🚧 (new)" in text and "**901** ✅ (🚧 → ✅)" in text
        assert "Closed tomorrow" not in text
        assert "Rows in progress at the window's end: 902." in text

    def test_the_day_before_does_not_see_the_day(self, history):
        text = yeoman.facts(history, DAY - dt.timedelta(days=1), gh_issues([]))
        assert "**901** 🚧 (new)" in text and "902" not in text

    def test_findings_open_filed_and_closed_by_the_heading(self, history):
        text = yeoman.facts(history, DAY, gh_issues([]))
        assert "Open at the window's end: 1. Filed in the window: F3. Closed in the window: F1." in text
        assert "- F3: A finding filed today" in text

    def test_the_newest_handoff_by_the_window_end(self, history):
        text = yeoman.facts(history, DAY, gh_issues([]))
        assert "docs/handoffs/2026-10-22_901_closed.md" in text
        assert "- the thing left" in text and "- the next row" in text
        before = yeoman.facts(history, DAY - dt.timedelta(days=1), gh_issues([]))
        assert "None by the window's end." in before

    def test_issues_open_or_updated_in_the_window_only(self, history):
        text = yeoman.facts(history, DAY, gh_issues([ISSUE_OPEN, ISSUE_OLD]))
        assert "#3 [open] Sign in to the desktop" in text and "#4" not in text


class TestTheDigestFile:
    def stand(self, summary="Two rows moved; nothing waits on you.", usage=True,
              model=rank_call.HAIKU):
        def run(cmd, **kw):
            if cmd[0] == "gh":
                return subprocess.CompletedProcess(cmd, 0, "[]", "")
            out = {"is_error": False, "session_id": "s-9", "num_turns": 1, "duration_ms": 900,
                   "total_cost_usd": 0.01, "structured_output": {"summary": summary},
                   "modelUsage": {model: {}},
                   "usage": {"input_tokens": 5, "output_tokens": 30} if usage else {}}
            run.cmd = cmd
            return subprocess.CompletedProcess(cmd, 0, json.dumps(out), "")
        return run

    @pytest.fixture(autouse=True)
    def ledger(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))

    def test_written_with_the_summary_the_facts_and_the_call(self, history):
        run = self.stand()
        assert yeoman.digest(DAY, root=history, run=run, out=lambda s: None) == 0
        page = (history / yeoman.DIGESTS / "2026-10-22.md").read_text()
        assert "Two rows moved" in page and "The facts below are the script's" in page
        assert "session `s-9`" in page and "**902** 🚧 (new)" in page
        assert run.cmd[run.cmd.index("--model") + 1] == rank_call.HAIKU
        assert run.cmd[run.cmd.index("--tools") + 1] == "Read,Grep,Glob"

    def test_a_summary_naming_what_the_facts_do_not_hold_is_set_aside(self, history):
        """Bug fix #2: the first real digest said 2022 where the facts said 2026."""
        run = self.stand(summary="Phase 902 started on 2022-10-22; F3 was filed; K9 applies.")
        assert yeoman.digest(DAY, root=history, run=run, out=lambda s: None) == 0
        page = (history / yeoman.DIGESTS / "2026-10-22.md").read_text()
        head = page.split("\n---\n")[0]
        assert "set aside: it named 2022-10-22, K9" in head
        assert "Phase 902 started" not in head
        assert "**902** 🚧 (new)" in page

    def test_a_summary_from_the_facts_is_kept(self, history):
        run = self.stand(summary="Phase 902 started; 901 closed; F3 was filed on October 22, "
                                 "2026-10-22.")
        yeoman.digest(DAY, root=history, run=run, out=lambda s: None)
        assert "Phase 902 started" in (history / yeoman.DIGESTS / "2026-10-22.md").read_text()

    @pytest.mark.parametrize("kw", [{"usage": False}, {"model": rank_call.OPUS}, {"summary": " "}],
                             ids=["no-usage", "wrong-model", "empty"])
    def test_a_stop_writes_no_file(self, history, kw):
        assert yeoman.digest(DAY, root=history, run=self.stand(**kw), out=lambda s: None) == 3
        assert not (history / yeoman.DIGESTS).exists()
