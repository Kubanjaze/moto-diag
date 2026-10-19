"""Phase 382: the API's video-file route serves the six rewritten paths.

The app cannot stream a backend-only video yet (M6: "Video not cached
locally"), so playback is proved here instead, through the real route,
`GET /v1/sessions/{id}/videos/{video_id}/file`, in-process. Each video's
owner is resolved from the database and stands in for the API key, so no
key is made and live is never written: live is copied read-only, by
SQLite's backup API, into a scratch folder.

The failing case is the pre-382 backup, which still holds the Mac's paths:
every video must be refused there ("file missing on disk").

Run from the repository root:
`.venv/bin/python docs/phases/in_progress/382_video_serve.py`
"""

from __future__ import annotations

import hashlib
import pathlib
import sqlite3
import sys
import tempfile

from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.deps import AuthedUser, get_current_user

LIVE = pathlib.Path.home() / "motodiag/live/motodiag.db"
BACKUP = pathlib.Path.home() / "backups/motodiag/motodiag_pre382_20261019_145601.db"


def copy(src: pathlib.Path, dst: pathlib.Path) -> pathlib.Path:
    with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as s, sqlite3.connect(dst) as d:
        s.backup(d)
    return dst


def serve_all(db: pathlib.Path) -> list[tuple[int, bool, int, str]]:
    """Each video's (id, soft-deleted, status, detail): the body's sha256 on a 200."""
    with sqlite3.connect(db) as c:
        rows = c.execute(
            "SELECT v.id, v.deleted_at IS NOT NULL, v.session_id, v.file_path, s.user_id"
            " FROM videos v JOIN diagnostic_sessions s ON s.id = v.session_id"
            " ORDER BY v.id").fetchall()
    app = create_app(db_path_override=str(db))
    results = []
    for video_id, deleted, session_id, file_path, user_id in rows:
        app.dependency_overrides[get_current_user] = lambda uid=user_id: AuthedUser(
            id=uid, username=f"owner{uid}", is_active=True, api_key_id=0,
            api_key_prefix="probe382")
        r = TestClient(app).get(f"/v1/sessions/{session_id}/videos/{video_id}/file")
        if r.status_code == 200:
            served = hashlib.sha256(r.content).hexdigest()
            on_disk = hashlib.sha256(pathlib.Path(file_path).read_bytes()).hexdigest()
            detail = f"{len(r.content)} bytes, sha256 {served[:12]}, " \
                     f"{'equals' if served == on_disk else 'DIFFERS FROM'} {file_path}"
        else:
            detail = r.json()["detail"]
        results.append((video_id, bool(deleted), r.status_code, detail))
    return results


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory(prefix="motodiag_382_serve_") as tmp:
        for name, src, live in (("live", LIVE, True), ("pre-382 backup", BACKUP, False)):
            print(f"{name} ({src.name}): a video not soft-deleted must give "
                  f"{'200, its file' if live else '404, file missing on disk'}")
            results = serve_all(copy(src, pathlib.Path(tmp) / f"{name.split()[0]}.db"))
            for video_id, deleted, status, detail in results:
                print(f"  video {video_id}{' (soft-deleted)' if deleted else ''}: {status} {detail}")
                if deleted:
                    ok &= status == 404
                elif live:
                    ok &= status == 200 and " equals " in detail
                else:
                    ok &= status == 404 and "file missing on disk" in detail
            ok &= len(results) == 6 and sum(not d for _, d, _, _ in results) == 5
    print("PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
