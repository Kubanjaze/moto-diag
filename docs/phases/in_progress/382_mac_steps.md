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
