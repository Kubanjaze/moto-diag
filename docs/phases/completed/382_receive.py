"""Phase 382: take the Mac's copy and videos into live, checked before anything opens them.

Run on the desktop after M4: `.venv/bin/python -I docs/phases/in_progress/382_receive.py <inbox>`.
1. Both files' sha256 must equal M3's; the same check must refuse a copy
   with one byte flipped (the control).
2. Each video in the tar must match its row's sha256, read from a scratch
   copy of the database, never from live.
3. The database goes to live (mode 600) and its sha256 is taken again
   there, before the API first opens it. Live must not exist yet.
"""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import sqlite3
import sys
import tarfile
import tempfile

DB_SHA = "7c302011e3cff0a8acbd95ecb61d96f2e438f2a69d879daa6fe81c0390b12eed"
TAR_SHA = "665f8528e9bc89e4fb091cf31945911b6b9beec7e7f9deb2d619e4f7133db6f4"
LIVE_DIR = pathlib.Path("/home/lilcu/motodiag/live")


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def matches(path: pathlib.Path, expected: str) -> bool:
    got = sha256(path)
    print(f"  {path.name}: {got} {'==' if got == expected else '!='} M3")
    return got == expected


def main(inbox: pathlib.Path) -> int:
    db_in, tar_in = inbox / "motodiag_before.db", inbox / "videos.tar"
    live = LIVE_DIR / "motodiag.db"
    assert not live.exists(), f"{live} exists already; refusing to overwrite"
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        print("1. sha256 against M3")
        flipped = work / "motodiag_before.db"
        shutil.copyfile(db_in, flipped)
        with open(flipped, "r+b") as f:
            f.seek(4096)
            byte = f.read(1)
            f.seek(4096)
            f.write(bytes([byte[0] ^ 1]))
        print(" control, one byte flipped (must be !=):")
        if matches(flipped, DB_SHA):
            print("FAILED: the check passed a changed copy")
            return 1
        print(" the received files:")
        if not (matches(db_in, DB_SHA) and matches(tar_in, TAR_SHA)):
            print("FAILED: a received file differs from M3's")
            return 1

        print("2. each video against its row (scratch copy of the database)")
        scratch = work / "scratch.db"
        shutil.copyfile(db_in, scratch)
        c = sqlite3.connect(f"file:{scratch}?mode=ro", uri=True)
        rows = {pathlib.Path(p).name: (vid, s) for vid, p, s in
                c.execute("select id, file_path, sha256 from videos order by id")}
        c.close()
        unpacked = work / "unpacked"
        with tarfile.open(tar_in) as t:
            t.extractall(unpacked, filter="data")
        files = sorted((unpacked / "videos").rglob("*.mp4"))
        assert len(files) == len(rows) == 6, (len(files), len(rows))
        for f in files:
            vid, expected = rows[f.name]
            got = sha256(f)
            print(f"  video {vid} {f.name}: equals its row: {got == expected}")
            if got != expected:
                return 1

        print("3. into live")
        LIVE_DIR.mkdir(mode=0o700, exist_ok=True)
        shutil.copytree(unpacked / "videos", LIVE_DIR / "videos")
        shutil.copyfile(db_in, live)
        live.chmod(0o600)
        if not matches(live, DB_SHA):
            print("FAILED: live differs after the copy")
            return 1
        print(f"  {live}: mode {oct(live.stat().st_mode & 0o777)}, {live.stat().st_size} bytes")
        print(f"  videos: {len(list((LIVE_DIR / 'videos').rglob('*.mp4')))} mp4 in {LIVE_DIR / 'videos'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1])))
