# Phase 382 — the steps on the Mac

Run by the operator or the advisor's session on the Mac; the output goes
back to the desktop's session. M1 and M2 are in `382_step0.md`.

## M3: the Tailscale start, and the cut-over's before-state (live only read)

Start the Tailscale app on the Mac (it was stopped), then:

    TS=/Applications/Tailscale.app/Contents/MacOS/Tailscale
    $TS status | head -5
    $TS ping -c 1 desktop-76s9bqv
    cd ~/Projects/moto-diag && mkdir -p ~/382_cutover && chmod 700 ~/382_cutover
    .venv/bin/python - <<'PY'
    import hashlib, os, pathlib, sqlite3
    out = pathlib.Path.home() / "382_cutover"
    src = sqlite3.connect("file:data/motodiag.db?mode=ro", uri=True)
    copy = out / "motodiag_before.db"
    dst = sqlite3.connect(copy); src.backup(dst); dst.close(); src.close()
    c = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
    print("schema", c.execute("select max(version) from schema_version").fetchone()[0])
    print("integrity", c.execute("pragma integrity_check").fetchone()[0],
          "| fk violations", len(c.execute("pragma foreign_key_check").fetchall()))
    tables = [t for (t,) in c.execute("select name from sqlite_master where type='table' "
                                      "and name not like 'sqlite_%' order by name")]
    print("tables", len(tables), "| rows", sum(c.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables))
    for t in tables:
        n = c.execute(f'select count(*) from "{t}"').fetchone()[0]
        if n: print(" ", t, n)
    for vid, path, sha in c.execute("select id, file_path, sha256 from videos order by id"):
        got = hashlib.sha256(open(path, "rb").read()).hexdigest()
        print("video", vid, "file sha256 equals the row's:", got == sha)
    c.close()
    print("copy", copy, copy.stat().st_size, "bytes")
    print("sha256", hashlib.sha256(copy.read_bytes()).hexdigest())
    PY
    tar -C data -cf ~/382_cutover/videos.tar videos && tar -tf ~/382_cutover/videos.tar | grep -c '\.mp4$'
    shasum -a 256 ~/382_cutover/videos.tar

Nothing is sent yet. The cut-over (M4) waits for the operator's word.

## M3's result

Run 2026-10-13 00:05 EDT (in the log). The copy
`~/382_cutover/motodiag_before.db`: 32301056 bytes, sha256
`7c302011e3cff0a8acbd95ecb61d96f2e438f2a69d879daa6fe81c0390b12eed`;
`videos.tar` (6 mp4) sha256
`665f8528e9bc89e4fb091cf31945911b6b9beec7e7f9deb2d619e4f7133db6f4`.

## M4: the cut-over (only on the operator's word)

The Mac stops being live. Nothing is deleted; no row changes.

    TS=/Applications/Tailscale.app/Contents/MacOS/Tailscale
    cd ~/Projects/moto-diag
    chmod 444 data/motodiag.db
    .venv/bin/python - <<'PY'
    import hashlib, pathlib, sqlite3
    out = pathlib.Path.home() / "382_cutover"
    src = sqlite3.connect("file:data/motodiag.db?mode=ro", uri=True)
    again = out / "motodiag_at_cutover.db"
    dst = sqlite3.connect(again); src.backup(dst); dst.close(); src.close()
    a = hashlib.sha256((out / "motodiag_before.db").read_bytes()).hexdigest()
    b = hashlib.sha256(again.read_bytes()).hexdigest()
    print("before ", a); print("cutover", b); print("unchanged since M3:", a == b)
    if a != b:
        dump = lambda p: list(sqlite3.connect(f"file:{p}?mode=ro", uri=True).iterdump())
        print("logically equal:", dump(out / "motodiag_before.db") == dump(again))
    PY
    mv data/motodiag.db data/motodiag_mac_retired_382.db
    for s in -shm -wal; do [ -e data/motodiag.db$s ] && mv data/motodiag.db$s data/motodiag_mac_retired_382.db$s; done
    ls -l data/motodiag_mac_retired_382.db* data/motodiag.db 2>&1
    mkdir -p ~/.config/motodiag
    printf '{"live": null, "host": "desktop-76s9bqv"}\n' > ~/.config/motodiag/live.json; cat ~/.config/motodiag/live.json
    $TS file cp ~/382_cutover/motodiag_before.db ~/382_cutover/videos.tar desktop-76s9bqv:
    echo "sent"

If "unchanged since M3" prints False, stop and send the output: the
desktop does not take a copy that differs from the before-state.
