"""Phase 293 — ``motodiag manuals``: the reviewers and the page images.

On ``motodiag.cli.main.cli`` through ``CliRunner``, on a temporary database
(``support.phase293.manuals_db``). A grant of an unknown username exits 1 and
writes nothing; ``render`` makes deleted images again and prints the count.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
from support.phase293 import make_shop, make_user, manuals_db, pdf_bytes  # noqa: F401

from motodiag.cli.main import cli
from motodiag.core.config import get_settings
from motodiag.core.database import get_connection
from motodiag.manuals import render, review, storage
from motodiag.media.paths import stored_media_path
from motodiag.reference import manual_repo
from motodiag.reference.models import ManualReference, ManualSource

ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str):
    return CliRunner().invoke(cli, ["manuals", *args])


def test_the_group_and_its_four_commands():
    assert "manuals" in cli.commands
    group = cli.commands["manuals"]
    assert set(group.commands) == {"reviewer", "render"}
    assert set(group.commands["reviewer"].commands) == {"grant", "revoke", "list"}
    out = CliRunner().invoke(cli, ["manuals", "--help"]).output
    assert "reviewer" in out and "render" in out
    out = CliRunner().invoke(cli, ["manuals", "reviewer", "--help"]).output
    assert all(word in out for word in ("grant", "revoke", "list"))


def test_main_registers_it_once():
    text = (ROOT / "src" / "motodiag" / "cli" / "main.py").read_text()
    assert text.count("from motodiag.cli.manuals import register_manuals") == 1
    assert text.count("register_manuals(cli)") == 1


def test_grant_list_revoke(manuals_db):
    uid = make_user(manuals_db, "operator", None)
    r = _run("reviewer", "grant", "operator")
    assert r.exit_code == 0, r.output
    assert "operator now reviews uploaded manuals." in r.output
    assert review.is_reviewer(uid, db_path=manuals_db)
    assert "already reviews" in _run("reviewer", "grant", "operator").output
    assert "operator (user" in _run("reviewer", "list").output
    r = _run("reviewer", "revoke", "operator")
    assert r.exit_code == 0 and "no longer reviews" in r.output
    assert not review.is_reviewer(uid, db_path=manuals_db)
    assert "No one reviews" in _run("reviewer", "list").output


def test_an_unknown_username_exits_1_and_writes_nothing(manuals_db):
    r = _run("reviewer", "grant", "nobody")
    assert r.exit_code == 1
    assert "no user named 'nobody'" in r.output
    with get_connection(manuals_db) as conn:
        assert conn.execute("SELECT count(*) FROM manual_reviewers").fetchone()[0] == 0
    assert _run("reviewer", "revoke", "nobody").exit_code == 1


def test_render_writes_the_missing_images_and_prints_the_count(manuals_db):
    shop = make_shop(manuals_db, "alpha")
    data_dir = get_settings().data_dir
    mid = manual_repo.add_manual(ManualReference(
        source=ManualSource.OTHER, title="m", shop_id=shop.id), db_path=manuals_db)
    pdf = storage.manual_file_path(data_dir, shop.id, mid)
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(pdf_bytes(2))
    manual_repo.set_file(mid, stored_media_path(pdf, data_dir), "sha", 1, 2, db_path=manuals_db)
    render.render_manual(mid, manuals_db)
    image = storage.page_image_path(data_dir, shop.id, mid, 2)
    image.unlink()
    r = _run("render")
    assert r.exit_code == 0, r.output
    assert f"Manual {mid}: 1 page images written." in r.output
    assert "1 page images written in all." in r.output
    assert image.exists()
    assert "nothing to render" in _run("render").output
    storage.thumb_path(data_dir, shop.id, mid, 1).unlink()
    r = _run("render", "--manual", str(mid))
    assert f"Manual {mid}: 1 page images written." in r.output
