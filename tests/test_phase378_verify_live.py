"""Phase 378, K25 — `deploy.py verify-live <phase>`, read-only.

Every deploy since 359 was checked against its backup with scripts kept in a
session scratchpad, and `/tmp` cleanup wiped them once (370). verify_phase's
check 8 printed only the schema version and a row count, and opened live
read-write. This reads live and the phase's backup through SQLite's backup
API (the backup opened immutable, so no `-shm` or `-wal` is left beside it)
and prints what changed, whether that is the approved diff, and live's
integrity and foreign keys.

Every case runs on 358's fixture repository and databases.
"""

from __future__ import annotations

import pathlib
import sqlite3

from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    D, PHASE, ROOT, _apply, _commit_diff, _dryrun, env,
)


def _deployed(env):
    assert _dryrun(env) == 0
    _commit_diff(env)
    assert _apply(env) == 0


def _verify(env, capsys) -> tuple[int, str]:
    code = D.verify_live(PHASE, db=env["live"], repo=env["repo"])
    return code, capsys.readouterr().out


def _backup(env) -> pathlib.Path:
    return pathlib.Path(D._header(D.diff_path(env["repo"], PHASE).read_text())["Backup"])


class TestReadingItBack:
    def test_a_clean_deploy_reads_back_as_the_approved_diff(self, env, capsys):
        _deployed(env)
        code, out = _verify(env, capsys)
        assert code == 0
        assert "rows: workflow_templates +1 ~0 -0" in out
        assert "rows: checklist_items +0 ~1 -0" in out
        assert "equals the approved exact diff: yes" in out
        assert "integrity: ok; foreign keys: ok" in out

    def test_it_changes_nothing_and_leaves_no_file(self, env, capsys):
        _deployed(env)
        before_live = D.dump(env["live"])
        bk = _backup(env)
        before_files = sorted(p.name for p in bk.parent.iterdir())
        before_bytes = bk.read_bytes()
        _verify(env, capsys)
        assert D.dump(env["live"]) == before_live
        assert sorted(p.name for p in bk.parent.iterdir()) == before_files
        assert bk.read_bytes() == before_bytes
        assert not list((env["repo"] / "data" / "deploy_scratch").glob(f"{PHASE}_verify_*"))

    def test_a_wal_backup_gets_no_shm_or_wal(self, env, capsys):
        """Live is in WAL mode, so its backups are. The control: a plain
        read-only open of a WAL file leaves `-shm` beside it; verify-live's
        immutable copy does not."""
        _deployed(env)
        bk = _backup(env)
        c = sqlite3.connect(bk)
        assert c.execute("pragma journal_mode=wal").fetchone()[0] == "wal"
        c.close()
        for side in ("-shm", "-wal"):
            bk.with_name(bk.name + side).unlink(missing_ok=True)
        control = bk.parent / "control.db"
        control.write_bytes(bk.read_bytes())
        plain = D._ro(control)
        plain.execute("select count(*) from sqlite_master").fetchone()
        assert control.with_name("control.db-shm").exists()
        plain.close()
        for p in bk.parent.glob("control.db*"):
            p.unlink()

        _verify(env, capsys)
        assert not bk.with_name(bk.name + "-shm").exists()
        assert not bk.with_name(bk.name + "-wal").exists()

    def test_a_row_outside_the_approved_diff_is_reported(self, env, capsys):
        _deployed(env)
        c = sqlite3.connect(env["live"])
        c.execute("update known_issues set description = 'changed later' where id = 1")
        c.commit()
        c.close()
        code, out = _verify(env, capsys)
        assert code == 3  # Phase 379, F197: a mismatch fails (it was 0)
        assert "rows: known_issues +0 ~1 -0" in out
        assert "the difference is not a later migration's" in out
        assert "equals the approved exact diff: no" in out
        assert "known_issues" in out.split("equals the approved exact diff: no", 1)[1]

    def test_a_foreign_key_break_fails(self, env, capsys):
        _deployed(env)
        c = sqlite3.connect(env["live"])
        c.executescript("create table child (id integer primary key, template_id integer "
                        "references workflow_templates(id)); "
                        "insert into child values (1, 999);")
        c.close()
        code, out = _verify(env, capsys)
        assert code == 1
        assert "foreign keys: 1 violation(s)" in out


class TestRefusals:
    def test_a_phase_with_no_deploy(self, env, capsys):
        code, out = _verify(env, capsys)
        assert code == 2 and "the phase has no deploy" in out

    def test_a_missing_backup(self, env, capsys):
        _deployed(env)
        _backup(env).unlink()
        code, out = _verify(env, capsys)
        assert code == 1 and "is missing" in out


def test_a_masked_clock_matches_any_timestamp_and_nothing_else():
    """The approved diff masked the migration's own clock as `<clock>`; read
    back days later, any timestamp-shaped value matches it, and nothing
    else does."""
    approved = {"rows": {"schema_version": {"added": {"83": {"applied_at": D.CLOCK,
                                                             "version": 84}}}}}

    def now(at):
        return {"rows": {"schema_version": {"added": {"83": {"applied_at": at,
                                                             "version": 84}}}}}

    assert D.shape_gaps(approved, now("2026-10-07 22:03:25")) == []
    assert D.shape_gaps(approved, now("2026-10-08T02:03:25.000+00:00")) == []
    assert len(D.shape_gaps(approved, now("not a time"))) == 1
    missing = " ".join(D.shape_gaps(approved, {"rows": {}}))
    assert "applied_at: approved '<clock>', live '(absent)'" in missing
    assert "version: approved 84, live '(absent)'" in missing


def test_verify_phase_check_8_calls_it_and_opens_live_read_only():
    script = (ROOT / ".claude" / "skills" / "closeout" / "verify_phase.sh").read_text()
    check_8 = script.split('=== 8.', 1)[1].split('=== 9.', 1)[0]
    assert "deploy.py\" verify-live" in check_8
    assert "mode=ro" in check_8
    assert "sqlite3.connect('data/motodiag.db')" not in check_8
