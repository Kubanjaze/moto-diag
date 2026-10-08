"""Phase 379, F197 — `deploy.py verify-live` fails when live does not equal
the approved diff, and verify_phase's check 8 fails with it.

Found by the advisor verifying 378: `verify-live 376` printed "no" and
exited 0, and check 8 never read the exit code. Now a mismatch exits 3 and
says whether live's schema is past the phase's own migrations; check 8 fails
on any exit but 0 (equal) and 2 (no deploy).
"""

from __future__ import annotations

import json
import pathlib
import re
import sqlite3
import subprocess

from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    D, PHASE, ROOT, _apply, _commit_diff, _dryrun, env,
)

VERIFY = ROOT / ".claude" / "skills" / "closeout" / "verify_phase.sh"


def _deployed(env):
    assert _dryrun(env) == 0
    _commit_diff(env)
    assert _apply(env) == 0


def _verify(env, capsys) -> tuple[int, str]:
    code = D.verify_live(PHASE, db=env["live"], repo=env["repo"])
    return code, capsys.readouterr().out


def test_an_approved_diff_missing_a_live_row_fails(env, capsys):
    """The known-bad case F197 asks for: the approved diff lacks one row that
    live holds, at the phase's own schema head."""
    _deployed(env)
    f = D.diff_path(env["repo"], PHASE)
    text = f.read_text()
    head, _, rest = text.partition(D.EXACT)
    body = json.loads(rest.split("```json", 1)[1].split("```", 1)[0])
    assert body["rows"]["workflow_templates"]["added"], "the fixture adds a template"
    body["rows"]["workflow_templates"]["added"] = {}
    f.write_text(head + D.EXACT + "\n```json\n" + json.dumps(body, indent=1, sort_keys=True)
                 + "\n```\n")
    code, out = _verify(env, capsys)
    assert code == 3
    assert "equals the approved exact diff: no" in out
    assert "the difference is not a later migration's" in out


def test_a_later_migration_is_named_as_the_cause_and_still_fails(env, capsys):
    _deployed(env)
    c = sqlite3.connect(env["live"])
    c.execute("insert into schema_version values (72)")
    c.execute("insert into workflow_templates values (3, 'tpl_c', 'a later phase')")
    c.commit()
    c.close()
    code, out = _verify(env, capsys)
    assert code == 3
    assert "live is at schema 72, past this phase's 71: later migrations explain" in out


def test_equal_still_passes(env, capsys):
    _deployed(env)
    assert _verify(env, capsys)[0] == 0


# --- check 8, run as a shell block with a stand-in deploy.py ---


def _check_8(tmp_path: pathlib.Path, live_code: int, with_diff: bool = True) -> tuple[int, str]:
    script = VERIFY.read_text()
    block = script.split('echo "=== 8.', 1)[1].split('echo "=== 9.', 1)[0]
    block = 'echo "=== 8.' + block
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    c = sqlite3.connect(repo / "data" / "motodiag.db")
    c.executescript("create table schema_version (version integer); "
                    "insert into schema_version values (84); "
                    "create table known_issues (id integer);")
    c.close()
    if with_diff:
        (repo / "docs" / "phases" / "completed").mkdir(parents=True)
        (repo / "docs" / "phases" / "completed" / "999_dryrun_diff.md").write_text("x")
    skills = tmp_path / "skills"
    (skills / "closeout").mkdir(parents=True)
    (skills / "deploy").mkdir(parents=True)
    (skills / "deploy" / "deploy.py").write_text(f"import sys; sys.exit({live_code})\n")
    run = subprocess.run(
        ["sh", "-c", f'FAILED=0\n{block}\nexit $FAILED'], cwd=repo, capture_output=True,
        text=True, env={"PATH": "/usr/bin:/bin", "PHASE": "999", "PY": "python3",
                        "DIR": str(skills / "closeout")})
    return run.returncode, run.stdout


def test_check_8_fails_on_a_mismatch_or_a_broken_database(tmp_path):
    for code in (1, 3):
        rc, out = _check_8(tmp_path / str(code), code)
        assert rc == 1 and f"CHECK 8 FAILED: verify-live exited {code}" in out


def test_check_8_passes_when_equal_or_with_no_deploy(tmp_path):
    assert _check_8(tmp_path / "eq", 0)[0] == 0
    assert _check_8(tmp_path / "nodeploy", 2)[0] == 0
    assert _check_8(tmp_path / "nodiff", 1, with_diff=False)[0] == 0


def test_verify_phase_exits_with_the_failure():
    script = VERIFY.read_text()
    assert script.rstrip().endswith("exit $FAILED")
    assert re.search(r"^FAILED=0$", script, re.M)
