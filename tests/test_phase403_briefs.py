"""Phase 403 (d) — the briefs say what the checks hold (F275, F264, F261).

Phase 389's lesson: where a check and a brief could disagree, the brief
states the check's rule. Each brief is read against its real failure:
- F275: 372's second session ended on the edit guard's refusal of
  `> $b.inner` (`tests/fixtures/phase403/stops_372.json`); the guard
  refuses `sed -i` wherever it points;
- F264: 371's phase log at `f0b3512` (the commit before `260cf7f`), whose
  regression line had no skip lines under it, so the live apply could not
  read it;
- F261: a code finding's row, `1 · code · open`, as 371's round 2 wrote it.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "phase403"
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "closeout"))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "refute"))

import _edit_guard  # noqa: E402
import closeout_check as C  # noqa: E402
import engineer as E  # noqa: E402
import red_team  # noqa: E402
import refute_check  # noqa: E402

CWD = "/fleet/moto-diag"
STOP = json.loads((FIX / "stops_372.json").read_text(encoding="utf-8"))[1]


def flat(text: str) -> str:
    return " ".join(text.split())


# ------------------------------------------------------------------ F275
def test_the_engineers_rule_3_states_the_guards_rule():
    """Red on the old brief: it named sed -i and redirects under src/ and
    tests/ only."""
    brief = flat(E.session_brief("372", 59))
    assert "The edit guard refuses sed -i wherever it points" in brief
    assert "whose target is not a literal path it can read" in brief
    assert "a variable, a substitution or a glob is refused wherever it would land" in brief
    assert "Write scratch files to a literal directory, /fleet/run/" in brief
    assert "The same refusal twice ends your session" in brief


def test_what_rule_3_says_is_what_the_guard_does():
    """The positive control: the refusal 372 hit, and the way out the brief
    gives, through the guard itself."""
    assert "the edit guard cannot tell where the redirect `>` `$b." in STOP["stop_text"]
    assert _edit_guard.check("cat /fleet/run/a > $b.inner", CWD), "a variable's target passed"
    assert _edit_guard.check("printf x > /fleet/run/scratch.txt", CWD) is None
    for target in ("docs/phases/in_progress/372_phase_log.md", "src/motodiag/x.py",
                   "/fleet/run/notes.md"):
        assert _edit_guard.check(f"sed -i 's/a/b/' {target}", CWD), f"sed -i on {target} passed"


# ------------------------------------------------------------------ F264
def test_rule_6_names_the_whole_record_and_the_read_back():
    brief = flat(E.session_brief("371", 54))
    assert f'every "{C.SKIP_PREFIX}" line right under it' in brief
    assert "and the coverage line after them" in brief
    assert ".venv/bin/python .claude/skills/fleet/engineer.py record 371" in brief
    assert "read it back as rule 6 says (the live apply reads it the same way)" in brief


def test_the_read_back_says_why_371s_log_had_no_record(tmp_path):
    """371's first entry, as the hold of 2026-11-08 12:46 EST read it: the
    read-back the brief gives finds no record, and says why."""
    log = tmp_path / "docs" / "phases" / "in_progress" / "371_phase_log.md"
    log.parent.mkdir(parents=True)
    text = (FIX / "371_phase_log_before_260cf7f.md").read_text(encoding="utf-8")
    log.write_text(text, encoding="utf-8")
    rc, said = E.record_said(tmp_path, "371")
    assert rc == 1 and "the lines below it name 0" in said
    assert said.startswith("no regression of record in docs/phases/in_progress/371_phase_log.md")


def test_the_read_back_finds_a_whole_record():
    """The control: 399's log, closed with its whole record, is read."""
    rc, said = E.record_said(ROOT, "399")
    assert rc == 0 and "passed at `2bb35de`" in said, said


def test_the_read_back_command_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert E.main(["record", "999"]) == 1
    assert "no 999_phase_log.md" in capsys.readouterr().out
    assert E.main(["nothing"]) == 2


# ------------------------------------------------------------------ F261
def test_the_red_teams_table_line_gives_a_code_finding_the_kind_factual():
    """Red on the old brief: "code" was a finding's kind and no row's."""
    brief = flat(red_team.brief(2))
    assert 'The table has no kind "code": a code finding' in brief
    assert "is written in this table with the kind factual" in brief


def test_the_checker_refuses_code_and_takes_factual():
    """The row as 371's round 2 wrote it, and as the brief now says."""
    table = ("## Refuter pass\n\n| claim | verdict | quote | source | round · kind · outcome |\n"
             "|---|---|---|---|---|\n"
             '| the list types its fields | killed | "channel: str" | src/x.py p. 121 | {} |\n')
    bad = refute_check.check(table.format("1 · code · open"))
    assert any(f.startswith("C5 ") and "1 · code · open" in f for f in bad)
    good = refute_check.check(table.format("1 · factual · open"))
    assert [f[:3] for f in good] == ["C6 "], good
