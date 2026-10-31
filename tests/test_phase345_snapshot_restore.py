"""Phase 345 — taking a snapshot, and reading one back.

A fresh database (``init_db`` on a temp path) and media files on temp
paths, an in-memory store, and a fixed clock. No test reads the live
database.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timezone

import pytest
from support.phase345 import FAKE_VALUES, MemoryStore, add_row, cheap_crypto, clock_at, make_live

from motodiag.backup import snapshot as snap
from motodiag.backup.crypt import BackupTampered, decrypt_file
from motodiag.backup.restore import (
    NoSnapshotBefore,
    RestoreRefused,
    list_snapshots,
    parse_at,
    pick,
    restore,
    verify,
)
from motodiag.backup.settings import BackupSettings
from motodiag.backup.snapshot import Manifest, SnapshotRefused, take_snapshot

T1 = "2026-10-01T03:00:00.000+00:00"
T2 = "2026-10-02T03:00:00.000+00:00"
T3 = "2026-10-03T03:00:00.000+00:00"


@pytest.fixture(autouse=True)
def _cheap(monkeypatch):
    cheap_crypto(monkeypatch)


@pytest.fixture
def settings(tmp_path):
    v = list(FAKE_VALUES.values())
    return BackupSettings(tmp_path / "backup.env", *v)


@pytest.fixture
def live(tmp_path):
    return make_live(tmp_path)


@pytest.fixture
def work(tmp_path):
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


def _manifest(store, folder, settings, tmp_path) -> Manifest:
    (tmp_path / "m.enc").write_bytes(store.objects[folder + "manifest.json.enc"])
    decrypt_file(tmp_path / "m.enc", tmp_path / "m.json", settings.passphrase)
    return Manifest.from_json((tmp_path / "m.json").read_text())


def _dump(db) -> dict:
    conn = sqlite3.connect(db)
    try:
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {n: sorted(map(repr, conn.execute(f'SELECT * FROM "{n}"'))) for n in names}
    finally:
        conn.close()


def _runs(work) -> list[dict]:
    return [json.loads(line) for line in (work / "runs.log").read_text().splitlines()]


class TestTakingASnapshot:
    def test_the_first_run_uploads_the_database_three_media_and_the_manifest(
            self, live, settings, work, tmp_path):
        db, data = live
        store = MemoryStore()
        result = take_snapshot(db, data, settings, store, work, clock_at(T1), label="nightly")
        folder = "snapshots/20261001T030000Z/"
        assert sorted(store.objects) == sorted(
            [folder + "motodiag.db.enc", folder + "manifest.json.enc"]
            + [e.key for e in result.manifest.media])
        assert (result.media_uploaded, result.media_skipped) == (3, 0)
        assert store.puts[-1] == folder + "manifest.json.enc"  # the manifest goes last
        m = _manifest(store, folder, settings, tmp_path)
        assert sorted(e.path for e in m.media) == [
            "audio/shop_1/1.m4a", "photos/shop_1/work_order_1/1.jpg",
            "videos/shop_1/session_1/1.mp4"]
        for e in m.media:
            assert e.sha256 == snap.sha256_of(data / e.path)
            assert e.key == f"media/{e.sha256}.enc"
        assert m.db_sha256 and m.schema_version and m.label == "nightly"
        assert m.taken_at == "2026-10-01T03:00:00+00:00"
        assert _runs(work)[-1]["outcome"] == "ok"

    def test_the_second_run_uploads_only_the_new_media_with_the_control(
            self, live, settings, work):
        db, data = live
        store = MemoryStore()
        first = take_snapshot(db, data, settings, store, work, clock_at(T1))
        (data / "photos" / "shop_1" / "new.jpg").write_bytes(b"a new photo")
        store.puts.clear()
        second = take_snapshot(db, data, settings, store, work, clock_at(T2))
        media_puts = [k for k in store.puts if k.startswith("media/")]
        assert len(media_puts) == 1 and (second.media_uploaded, second.media_skipped) == (1, 3)
        assert set(store.puts) - set(media_puts) == {
            "snapshots/20261002T030000Z/motodiag.db.enc",
            "snapshots/20261002T030000Z/manifest.json.enc"}
        # The control: a media object gone from the store is uploaded again.
        gone = first.manifest.media[0].key
        del store.objects[gone]
        store.puts.clear()
        third = take_snapshot(db, data, settings, store, work, clock_at(T3))
        assert [k for k in store.puts if k.startswith("media/")] == [gone]
        assert third.media_uploaded == 1
        assert [r["media_uploaded"] for r in _runs(work)] == [3, 1, 1]

    def test_a_copy_that_fails_its_integrity_check_uploads_nothing(
            self, live, settings, work, monkeypatch):
        db, data = live
        real_copy = snap.copy_database

        def copy_then_corrupt(src, dst):
            real_copy(src, dst)
            raw = bytearray(dst.read_bytes())
            for page in range(1, len(raw) // 4096):
                raw[page * 4096: page * 4096 + 16] = b"\xff" * 16
            dst.write_bytes(bytes(raw))

        monkeypatch.setattr(snap, "copy_database", copy_then_corrupt)
        store = MemoryStore()
        with pytest.raises(SnapshotRefused, match="integrity"):
            take_snapshot(db, data, settings, store, work, clock_at(T1))
        assert store.objects == {}
        last = _runs(work)[-1]
        assert last["outcome"] == "failed" and "integrity check" in last["error"]

    def test_no_plaintext_remains_after_a_success_or_a_failure(
            self, live, settings, work, monkeypatch):
        db, data = live
        store = MemoryStore()
        take_snapshot(db, data, settings, store, work, clock_at(T1))
        assert sorted(p.name for p in work.iterdir()) == ["runs.log"]

        def broken_put(key, path, sha256):
            raise OSError("the network went away")

        monkeypatch.setattr(store, "put", broken_put)
        (data / "videos" / "new.mp4").write_bytes(b"new")
        with pytest.raises(OSError):
            take_snapshot(db, data, settings, store, work, clock_at(T2))
        assert sorted(p.name for p in work.iterdir()) == ["runs.log"]
        assert _runs(work)[-1]["error"] == "OSError: the network went away"

    def test_a_database_with_no_schema_version_table(self, tmp_path):
        db = tmp_path / "bare.db"
        sqlite3.connect(db).execute("CREATE TABLE t (x)").connection.commit()
        assert snap.schema_version_of(db) is None


@pytest.fixture
def three(live, settings, work):
    """Three snapshots at T1 < T2 < T3, each after one more marker row."""
    db, data = live
    store = MemoryStore()
    dumps = {}
    for name, when in (("T1", T1), ("T2", T2), ("T3", T3)):
        add_row(db, name)
        take_snapshot(db, data, settings, store, work, clock_at(when))
        dumps[name] = _dump(db)
    return store, dumps


def _markers(db) -> list[str]:
    return [r[0] for r in sqlite3.connect(db).execute("SELECT name FROM phase345_marker")]


class TestListingAndPicking:
    def test_newest_first(self, three):
        store, _ = three
        assert [r.stamp for r in list_snapshots(store)] == [
            "20261003T030000Z", "20261002T030000Z", "20261001T030000Z"]

    def test_pick_between_t2_and_t3_is_t2_and_latest_is_t3(self, three):
        refs = list_snapshots(three[0])
        assert pick(refs, parse_at("2026-10-02T12:00:00+00:00")).stamp == "20261002T030000Z"
        assert pick(refs, parse_at("2026-10-02T03:00:00Z")).stamp == "20261002T030000Z"
        assert pick(refs, parse_at("latest")).stamp == "20261003T030000Z"

    def test_before_t1_refuses_naming_t1(self, three):
        refs = list_snapshots(three[0])
        with pytest.raises(NoSnapshotBefore, match="2026-10-01T03:00:00"):
            pick(refs, parse_at("2026-09-30T00:00:00+00:00"))

    def test_an_empty_store(self):
        assert list_snapshots(MemoryStore()) == []
        with pytest.raises(NoSnapshotBefore, match="no snapshot has been taken"):
            pick([], None)

    def test_a_naive_time_is_local(self):
        assert parse_at("2026-10-02T03:00").utcoffset() is not None

    def test_a_folder_without_a_manifest_is_not_listed_with_the_control(self, three):
        store, _ = three
        key = "snapshots/20261004T030000Z/manifest.json.enc"
        store.objects["snapshots/20261004T030000Z/motodiag.db.enc"] = b"db"
        assert "20261004T030000Z" not in [r.stamp for r in list_snapshots(store)]
        store.objects[key] = b"manifest"
        assert list_snapshots(store)[0].stamp == "20261004T030000Z"

    def test_a_folder_whose_name_is_not_a_time_is_ignored(self, three):
        store, _ = three
        store.objects["snapshots/junk/motodiag.db.enc"] = b"x"
        store.objects["snapshots/junk/manifest.json.enc"] = b"x"
        assert len(list_snapshots(store)) == 3


class TestRestore:
    def test_the_restored_database_and_media_equal_the_source_at_that_time(
            self, three, settings, live, tmp_path):
        store, dumps = three
        db, data = live
        ref = pick(list_snapshots(store), parse_at("2026-10-02T12:00:00+00:00"))
        to = tmp_path / "restored"
        report = restore(ref, store, settings, to, current_db=db, current_data_dir=data)
        assert _dump(to / "motodiag.db") == dumps["T2"]
        assert _markers(to / "motodiag.db") == ["T1", "T2"]
        for rel in ("videos/shop_1/session_1/1.mp4", "photos/shop_1/work_order_1/1.jpg",
                    "audio/shop_1/1.m4a"):
            assert (to / rel).read_bytes() == (data / rel).read_bytes()
        assert report.media_count == 3 and report.rows["phase345_marker"] == 2
        assert not (to / ".incoming").exists()

    def test_db_only(self, three, settings, live, tmp_path):
        store, _ = three
        ref = list_snapshots(store)[0]
        report = restore(ref, store, settings, tmp_path / "r", db_only=True)
        assert sorted(p.name for p in (tmp_path / "r").iterdir()) == ["motodiag.db"]
        assert report.media_count == 0

    def test_a_non_empty_target_refuses(self, three, settings, tmp_path):
        store, _ = three
        (tmp_path / "busy").mkdir()
        (tmp_path / "busy" / "keep.txt").write_text("mine")
        with pytest.raises(RestoreRefused, match="not an empty folder"):
            restore(list_snapshots(store)[0], store, settings, tmp_path / "busy")
        assert (tmp_path / "busy" / "keep.txt").read_text() == "mine"

    @pytest.mark.parametrize("where", ["inside", "is", "holds"])
    def test_a_target_over_live_refuses(self, three, settings, live, tmp_path, where):
        store, _ = three
        db, data = live
        to = {"inside": data / "restore", "is": data, "holds": tmp_path}[where]
        with pytest.raises(RestoreRefused, match="never writes over live"):
            restore(list_snapshots(store)[0], store, settings, to,
                    current_db=db, current_data_dir=data)
        assert not (data / "restore").exists()

    def test_the_control_a_sibling_of_live_is_not_refused(self, three, settings, live, tmp_path):
        store, _ = three
        db, data = live
        restore(list_snapshots(store)[0], store, settings, data.parent / "restore_check",
                current_db=db, current_data_dir=data)
        assert (data.parent / "restore_check" / "motodiag.db").is_file()

    def test_a_corrupted_media_object_refuses_and_leaves_no_folder(
            self, three, settings, tmp_path):
        store, _ = three
        key = next(k for k in store.objects if k.startswith("media/"))
        raw = bytearray(store.objects[key])
        raw[-20] ^= 0x01
        store.objects[key] = bytes(raw)
        with pytest.raises(BackupTampered):
            restore(list_snapshots(store)[0], store, settings, tmp_path / "r")
        assert not (tmp_path / "r").exists()

    def test_a_failure_in_a_folder_that_existed_empties_it(self, three, settings, tmp_path):
        store, _ = three
        key = next(k for k in store.objects if k.startswith("media/"))
        store.objects[key] = b"MDBK" + b"\x01\x0a" + b"\0" * 60
        (tmp_path / "r").mkdir()
        with pytest.raises(BackupTampered):
            restore(list_snapshots(store)[0], store, settings, tmp_path / "r")
        assert (tmp_path / "r").is_dir() and list((tmp_path / "r").iterdir()) == []

    def test_a_media_file_whose_hash_differs_from_the_manifest_refuses(
            self, three, settings, tmp_path, monkeypatch):
        store, _ = three
        from motodiag.backup import restore as restore_mod
        monkeypatch.setattr(restore_mod, "sha256_of", lambda p: "0" * 64)
        with pytest.raises(BackupTampered, match="sha256"):
            restore(list_snapshots(store)[0], store, settings, tmp_path / "r")
        assert not (tmp_path / "r").exists()

    def test_a_wrong_passphrase_refuses(self, three, tmp_path):
        store, _ = three
        wrong = BackupSettings(tmp_path / "e", *list(FAKE_VALUES.values())[:4], "wrong")
        with pytest.raises(BackupTampered, match="wrong passphrase"):
            restore(list_snapshots(store)[0], store, wrong, tmp_path / "r")
        assert not (tmp_path / "r").exists()


class TestVerify:
    def test_verify_reads_the_database_back_and_leaves_nothing(
            self, three, settings, tmp_path, monkeypatch):
        store, _ = three
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(scratch))
        report = verify(list_snapshots(store)[0], store, settings)
        assert report.rows["phase345_marker"] == 3 and report.media_count == 0
        assert list(scratch.iterdir()) == []

    def test_verify_refuses_a_tampered_database(self, three, settings):
        store, _ = three
        key = "snapshots/20261003T030000Z/motodiag.db.enc"
        raw = bytearray(store.objects[key])
        raw[100] ^= 0x01
        store.objects[key] = bytes(raw)
        with pytest.raises(BackupTampered):
            verify(list_snapshots(store)[0], store, settings)


def test_the_stamp_is_utc():
    when = datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc).astimezone()
    assert snap.stamp_of(when) == "20261031T233000Z"
