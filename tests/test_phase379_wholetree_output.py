"""Phase 379, F173 — the whole-tree command keeps pytest's whole output.

359's first `--full` lost two of its four FAILED lines, and every traceback,
because `wholetree.py` kept only the last 1500 characters (later the last 15
lines). The run behind F173's one parallel failure left nothing to read. Now
the whole output is written to `.git/motodiag_wholetree/last_<mode>.log`,
and a failing run prints every FAILED and ERROR line and the log's path.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "closeout"))

import wholetree as W  # noqa: E402

PLANTED = "\n".join(
    f"def test_planted_{i}():\n    assert {i} == -1, 'planted failure {i}'\n" for i in range(20))


def test_every_failed_line_and_the_whole_log(tmp_path, monkeypatch, capsys):
    planted = tmp_path / "test_planted_failures.py"
    planted.write_text(PLANTED)
    monkeypatch.setattr(W, "members", lambda mode, root: [str(planted)])
    monkeypatch.setattr(W, "records_dir", lambda root=None: tmp_path / "records")
    result = W.run("fast")
    out = capsys.readouterr().out
    assert not result.passed
    failed = [ln for ln in out.splitlines() if ln.startswith("FAILED")]
    assert len(failed) == 20, out
    log = tmp_path / "records" / "last_fast.log"
    assert f"is in {log}" in out
    text = log.read_text()
    assert all(f"planted failure {i}" in text for i in range(20))
    assert "assert 0 == -1" in text


def test_a_passing_run_keeps_its_log_too(tmp_path, monkeypatch, capsys):
    planted = tmp_path / "test_planted_pass.py"
    planted.write_text("def test_ok():\n    assert True\n")
    monkeypatch.setattr(W, "members", lambda mode, root: [str(planted)])
    monkeypatch.setattr(W, "records_dir", lambda root=None: tmp_path / "records")
    assert W.run("full").passed
    assert "1 passed" in (tmp_path / "records" / "last_full.log").read_text()
