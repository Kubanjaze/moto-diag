#!/usr/bin/env python3
"""Every video the API holds, fetched through its file route on a copy of live (Phase 384).

382's `382_video_serve.py`, made a tool: nobody had fetched the six videos
since 383 stored their paths relative to the data folder. Live is copied
read-only by SQLite's backup API into a temporary folder; the API is built
in-process on the copy, with `data_dir` set to live's own folder (where the
service finds them, ops/desktop/motodiag-api.service). Each video's owner
stands in for an API key, so no key is made and live is never written.

A video not soft-deleted passes only with a 200 whose sha256 equals the
one its row recorded at upload (382's script compared the body with the file
the route had just read, which a changed file passes); a soft-deleted one
only with a 404. Exit 0 only when there is at
least one video and every one passes.

    media_check.py                  live, from live.json (exit 4 elsewhere)
    media_check.py <db> <data_dir>  any database and data folder (tests)
"""
from __future__ import annotations

import hashlib
import pathlib
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import live as L  # noqa: E402


def serve_all(db: pathlib.Path, data_dir: pathlib.Path) -> list[tuple[int, bool, int, str]]:
    """Each video's (id, soft-deleted, status, detail)."""
    from fastapi.testclient import TestClient

    from motodiag.api.app import create_app
    from motodiag.auth.deps import AuthedUser, get_current_user
    from motodiag.core.config import Settings

    with sqlite3.connect(db) as c:
        rows = c.execute(
            "SELECT v.id, v.deleted_at IS NOT NULL, v.session_id, v.file_path, v.sha256,"
            " s.user_id"
            " FROM videos v JOIN diagnostic_sessions s ON s.id = v.session_id"
            " ORDER BY v.id").fetchall()
    app = create_app(settings=Settings(db_path=str(db), data_dir=str(data_dir)),
                     db_path_override=str(db))
    results = []
    for video_id, deleted, session_id, stored, recorded, user_id in rows:
        app.dependency_overrides[get_current_user] = lambda uid=user_id: AuthedUser(
            id=uid, username=f"owner{uid}", is_active=True, api_key_id=0,
            api_key_prefix="probe384")
        r = TestClient(app, raise_server_exceptions=False).get(
            f"/v1/sessions/{session_id}/videos/{video_id}/file")
        if r.status_code == 200:
            served = hashlib.sha256(r.content).hexdigest()
            detail = (f"{len(r.content)} bytes, sha256 {served[:12]}, "
                      f"{'equals' if served == recorded else 'DIFFERS FROM'} the upload's "
                      f"({stored})")
        else:
            try:
                detail = str(r.json().get("detail"))
            except ValueError:
                detail = r.text[:120]
        results.append((video_id, bool(deleted), r.status_code, detail))
    return results


def check(db: pathlib.Path, data_dir: pathlib.Path) -> int:
    with tempfile.TemporaryDirectory(prefix="motodiag_media_check_") as tmp:
        copy = pathlib.Path(tmp) / "live_copy.db"
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as s, sqlite3.connect(copy) as d:
            s.backup(d)
        results = serve_all(copy, data_dir)
    ok = bool(results)
    print(f"media-check: {len(results)} video(s) in {db.name}, served from {data_dir}")
    for video_id, deleted, status, detail in results:
        passed = status == 404 if deleted else (status == 200 and " equals " in detail)
        ok &= passed
        print(f"  video {video_id}{' (soft-deleted)' if deleted else ''}: {status} {detail}"
              f"{'' if passed else '  <- FAILS'}")
    print("PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if len(argv) == 2:
        return check(pathlib.Path(argv[0]), pathlib.Path(argv[1]))
    try:
        db = L.where()
    except L.LiveElsewhere as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return L.REFUSED
    return check(db, db.parent)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
