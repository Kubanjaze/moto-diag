"""Phase 392 — a stop the record already answers is answered from it.

The operator's K50: "The record may answer a stop only when one K-id's own
words cover the same kind of stop and the same subject; the answer quotes
it verbatim and cites the K-id; never a rule-1 stop … give each K-id a
"covers" line so matching is a lookup; anything else comes to me." On 389's
walk-through (phase 902, a planted trial): a K-id covering the Engineer's
third-bug-fix stop on 902 answers it, verbatim, and the Engineer runs again
with those words; the same stop twice, a stop on another phase, and a
rule-1 stop all go to the operator.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / "tests"))
import dispatcher as D  # noqa: E402
from test_phase389_dispatcher import go_to_approved, labels, step, world  # noqa: E402,F401
from test_phase389_fleet_git import git  # noqa: E402

WORDS = '"on 902, a third bug fix may go on: they share no cause"'


def covering(origin: pathlib.Path, covers: str) -> None:
    dec = origin / "docs" / "decisions.md"
    dec.write_text(dec.read_text() + f"| K93 | 2026-10-27 | {WORDS} | No check. | {covers} |\n")
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qam", "K93", cwd=origin)


@pytest.fixture
def prompts(world):
    """Each Engineer session's prompt, in order."""
    engineer = world[4]
    seen: list[str] = []
    real = engineer.__call__

    class Recording(type(engineer)):
        def __call__(self, cmd, stdout, stderr, **kw):
            seen.append(cmd[cmd.index("-p") + 1])
            return real(cmd, stdout, stderr, **kw)

    engineer.__class__ = Recording
    return seen


def stops_once(monkeypatch, reason="third-bug-fix: the phase log reached Bug fix #3."):
    said = iter([reason])
    monkeypatch.setattr(D.engineer, "watch", lambda *a: next(said, None))


def test_a_covered_stop_is_answered_verbatim_and_the_engineer_runs_again(world, prompts,
                                                                         monkeypatch):
    fleet, host, clock, origin, engineer, *_ = world
    covering(origin, "stop=third-bug-fix subject=902")
    go_to_approved(world)
    stops_once(monkeypatch)
    step(clock, fleet, host)
    assert "needs-admiral" not in labels(host) and "build:open" in labels(host)
    said = host.comments(31)[-1]
    assert said.startswith(f"{D.ANSWER_M} kid=K93 stop=third-bug-fix")
    assert WORDS in said and "Answered from the record, not by the operator" in said
    step(clock, fleet, host)                       # the Engineer, again, with the answer
    assert engineer.runs == 2
    assert WORDS in prompts[1] and "applied literally" in prompts[1]
    assert WORDS not in prompts[0]
    assert "review:open" in labels(host)           # it went on to its pull request


def test_the_same_stop_twice_goes_to_the_operator(world, monkeypatch):
    fleet, host, clock, origin, *_ = world
    covering(origin, "stop=third-bug-fix subject=902")
    go_to_approved(world)
    monkeypatch.setattr(D.engineer, "watch", lambda *a: "third-bug-fix: Bug fix #3.")
    step(clock, fleet, host)
    assert "needs-admiral" not in labels(host)
    step(clock, fleet, host)
    assert "needs-admiral" in labels(host)
    assert sum(c.startswith(D.ANSWER_M) for c in host.comments(31)) == 1


def test_a_k_id_covering_another_phase_answers_nothing(world, monkeypatch):
    fleet, host, clock, origin, *_ = world
    covering(origin, "stop=third-bug-fix subject=303")
    go_to_approved(world)
    stops_once(monkeypatch)
    step(clock, fleet, host)
    assert "needs-admiral" in labels(host)
    assert not any(c.startswith(D.ANSWER_M) for c in host.comments(31))


def test_a_rule_1_stop_is_never_answered(world):
    fleet, host, clock, origin, engineer, *_ = world
    covering(origin, "stop=fork subject=902")
    go_to_approved(world)
    engineer.result = {"outcome": "stop", "kind": "fork", "question": "Which of two plans?"}
    step(clock, fleet, host)
    assert "needs-admiral" in labels(host) and "Which of two plans?" in host.comments(31)[-1]
    assert not any(c.startswith(D.ANSWER_M) for c in host.comments(31))
