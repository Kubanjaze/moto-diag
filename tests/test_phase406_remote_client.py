"""Phase 406 (K93) — `remote.py deploy-step`, the database step from the Mac.

The operator's condition: "the database step from the Mac must still show me
the dry run's list before it asks for yes". So the dry run's lines are shown
as they come, the yes is asked only after the dry run has ended, and only a
yes sends the apply, naming the sha256 the dry run's last line gave. These
cases run the client with a stand-in for SSH and for the Mac's terminal.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "deploy"))

import remote as M  # noqa: E402

WAY = {"ssh": "lilcu@motodiag-ops", "key": "/k"}
BRANCH = "phase-334-terms-of-service-liability-framework"
COMMIT = "b" * 40
SHA = "c" * 64
DRY = ["Step 1 of 3: trying the change on a copy of the live database (live is only read)...",
       "", "On the copy, this change:", "  - adds a new table, terms_acceptances, with 5 columns",
       "", "Nothing is applied: the Mac asks you for yes.", f"dry-run diff sha256: {SHA}"]


class Desk:
    """What the operator sees, in order: the dry run, the question, the apply."""

    def __init__(self, lines=DRY, code=0, answer="yes"):
        self.lines, self.code, self.answer = lines, code, answer
        self.events: list[str] = []
        self.applied: list[list[str]] = []

    def dry(self, argv):
        assert argv[-1] == f"deploy-dryrun 334 {BRANCH} {COMMIT}"
        self.events.append("dry run shown")
        return self.code, list(self.lines)

    def ask(self, prompt):
        assert "Type yes" in prompt
        self.events.append("yes asked")
        return self.answer

    def apply(self, argv):
        self.events.append("apply sent")
        self.applied.append(argv)
        return 0


def step(desk, monkeypatch):
    monkeypatch.setattr(M, "run", desk.apply)
    return M.deploy_step(WAY, "334", BRANCH, COMMIT, run_lines=desk.dry, ask=desk.ask)


def test_the_list_comes_before_the_question_and_yes_sends_that_diff(monkeypatch):
    desk = Desk()
    assert step(desk, monkeypatch) == 0
    assert desk.events == ["dry run shown", "yes asked", "apply sent"]
    (argv,) = desk.applied
    assert argv[-1] == f"deploy-apply 334 {BRANCH} {COMMIT} {SHA}"


@pytest.mark.parametrize("answer", ["no", "y", "", "yes please"])
def test_anything_but_yes_sends_nothing_more(monkeypatch, capsys, answer):
    desk = Desk(answer=answer)
    assert step(desk, monkeypatch) == 2
    assert desk.events == ["dry run shown", "yes asked"]
    assert "nothing was applied" in capsys.readouterr().out


def test_a_yes_with_spaces_or_capitals_is_a_yes(monkeypatch):
    desk = Desk(answer="  Yes ")
    assert step(desk, monkeypatch) == 0
    assert desk.events[-1] == "apply sent"


def test_a_dry_run_that_fails_asks_nothing(monkeypatch):
    desk = Desk(code=1)
    assert step(desk, monkeypatch) == 1
    assert desk.events == ["dry run shown"]


@pytest.mark.parametrize("lines", [
    DRY[:-1],                                              # no sha256 line
    DRY + [f"dry-run diff sha256: {'d' * 64}"],            # two of them
    DRY[:-1] + ["dry-run diff sha256: cafe"],               # not a sha256
])
def test_no_single_sha256_asks_nothing(monkeypatch, capsys, lines):
    desk = Desk(lines=lines)
    assert step(desk, monkeypatch) == 1
    assert desk.events == ["dry run shown"]
    assert "nothing to say yes to" in capsys.readouterr().err


def test_already_applied_asks_nothing(monkeypatch):
    desk = Desk(lines=["This change is already on the live database; nothing is applied again.",
                       "  equals the approved exact diff: yes"])
    assert step(desk, monkeypatch) == 0
    assert desk.events == ["dry run shown"]


def test_stream_shows_each_line_and_keeps_it(capsys):
    code, lines = M.stream([sys.executable, "-c", "print('one'); print('two')"])
    assert (code, lines) == (0, ["one", "two"])
    assert capsys.readouterr().out == "one\ntwo\n"


def test_stream_passes_the_exit_through():
    code, _ = M.stream([sys.executable, "-c", "import sys; print('x'); sys.exit(3)"])
    assert code == 3


@pytest.mark.parametrize("args", [
    ["334", "main", COMMIT],                # not a phase branch
    ["334", BRANCH, "abc"],                 # not a commit
    ["33", BRANCH, COMMIT],                 # not a phase
    ["334", BRANCH],                        # missing the commit
])
def test_main_refuses_what_deploy_step_cannot_hold(monkeypatch, capsys, tmp_path, args):
    key = tmp_path / "key"
    key.write_text("k")
    cfg = tmp_path / "live.json"
    cfg.write_text('{"live": null, "remote": {"ssh": "lilcu@motodiag-ops", "key": "%s"}}' % key)
    sent: list[list[str]] = []
    monkeypatch.setattr(M, "run", lambda argv: sent.append(argv) or 0)
    monkeypatch.setattr(M, "deploy_step", lambda *a, **k: sent.append(["deploy_step"]) or 0)
    assert M.main(["deploy-step", *args], config=cfg) == M.REFUSED
    assert sent == []
    assert "deploy-step takes" in capsys.readouterr().err


def test_main_sends_a_good_deploy_step_to_deploy_step(monkeypatch, tmp_path):
    key = tmp_path / "key"
    key.write_text("k")
    cfg = tmp_path / "live.json"
    cfg.write_text('{"live": null, "remote": {"ssh": "lilcu@motodiag-ops", "key": "%s"}}' % key)
    got = []
    monkeypatch.setattr(M, "deploy_step", lambda way, *a: got.append((way["ssh"], a)) or 0)
    assert M.main(["deploy-step", "334", BRANCH, COMMIT], config=cfg) == 0
    assert got == [("lilcu@motodiag-ops", ("334", BRANCH, COMMIT))]


def test_the_ssh_words_reach_the_desktop_as_one_quoted_command():
    argv = M.ssh_argv(WAY, ["deploy-apply", "334", BRANCH, COMMIT, SHA])
    assert argv[-1] == f"deploy-apply 334 {BRANCH} {COMMIT} {SHA}"
    assert argv[0] == "ssh" and "-T" in argv
