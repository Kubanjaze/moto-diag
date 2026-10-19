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

## M4's result, and M4b: the transfer again

M4 ran 2026-10-14 23:57 EDT: "unchanged since M3: True"; live renamed to
`data/motodiag_mac_retired_382.db` (with `-shm`/`-wal`); the Mac's
`live.json` written. **The Taildrop failed:** "desktop-76s9bqv is not
replying", `502 Bad Gateway`, 0 bytes sent. M4's `echo "sent"` ran whatever
`file cp` returned; that line was wrong, and M4b chains it.

M4b sends only what M4 already made; the Mac's data is not touched again:

    TS=/Applications/Tailscale.app/Contents/MacOS/Tailscale
    $TS ping -c 3 desktop-76s9bqv
    echo probe > ~/382_cutover/probe.txt
    $TS file cp ~/382_cutover/probe.txt desktop-76s9bqv: && echo "probe sent"
    $TS file cp ~/382_cutover/motodiag_before.db ~/382_cutover/videos.tar desktop-76s9bqv: && echo "both sent"

## M4b's result, and M4c: the desktop pulls over the tailnet

M4b, 2026-10-15 00:01 EDT: `tailscale ping` direct (10.0.0.55:41641,
3 ms), then the same "not replying" and `502 Bad Gateway`, 0 bytes.
On the desktop: its peer API answers itself (a GET and a PUT, 200), and a
Taildrop from the desktop to the Mac exits 0. So the Mac's connection into
the desktop's peer API fails, while the desktop's connections out work.

M4c serves only the two files, on the Mac's **tailnet address only**
(100.80.109.103; not the LAN, not Funnel); the desktop is already polling
for it and pulls both. The first `curl` is a diagnostic for the log:

    curl -s -m 5 -o /dev/null -w 'desktop peer API from the Mac: %{http_code}\n' http://100.75.113.50:41476/ || echo "desktop peer API from the Mac: no connection"
    mkdir -p ~/382_cutover/send && chmod 700 ~/382_cutover/send
    ln -f ~/382_cutover/motodiag_before.db ~/382_cutover/videos.tar ~/382_cutover/send/
    cd ~/382_cutover/send && /usr/bin/python3 -m http.server 8382 --bind 100.80.109.103

If macOS asks whether python may accept incoming connections, allow it.
Leave it running until the desktop's session says both files arrived and
match, then Ctrl-C it.

## The cut-over, done by USB (3B), 2026-10-19

The operator carried a fresh backup-API copy taken 09:01 EDT (sha256
`7c3020…2eed`, equal to M3's) and `videos.tar` on a USB drive. Live is on
the desktop from 14:35:04 EDT (the phase log has the receiving check).

## M5: the tailnet and the LAN, from the Mac (read only)

The same block runs twice: **M5a before** the desktop turns on `tailscale
serve` (the tailnet line must fail), and **M5b after** it (the tailnet line
must print 200 and the body). The LAN lines must fail both times. The two
controls show the Mac does reach the desktop's LAN address (the ping's path)
and that its curl works on the LAN (the router).

    TS=/Applications/Tailscale.app/Contents/MacOS/Tailscale
    date
    U=https://desktop-76s9bqv.taila45995.ts.net/healthz
    curl -sS -m 15 -w ' tailnet: %{http_code}\n' "$U"; echo " tailnet exit $?"
    for u in http://10.0.0.55:8000/healthz https://10.0.0.55/healthz https://10.0.0.55:8000/healthz http://10.0.0.55/healthz; do
      curl -sS -k -m 5 -o /dev/null -w " $u: %{http_code}\n" "$u"; echo " LAN exit $?"
    done
    $TS ping -c 1 desktop-76s9bqv
    curl -s -m 5 -o /dev/null -w ' control, router 10.0.0.1: %{http_code}\n' http://10.0.0.1/; echo " router exit $?"
