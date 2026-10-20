# Phase 383 — the desktop's steps (087 through the deploy skill)

Run by the operator, or a session on DESKTOP-76S9BQV, in the desktop's
**development checkout** of moto-diag (not `~/motodiag/server`, which
follows master). Paste each step's output back to the Mac session. The
Mac does not commit between a desktop commit and its pull.

Set once per shell:

    REPO=<the desktop's development checkout of moto-diag>
    cd "$REPO"

## D1 — the dry run (live only read)

    git fetch origin && git switch phase-383 && git pull --ff-only
    git log -1 --format=%h
    .venv/bin/python -B .claude/skills/deploy/deploy.py dryrun 383; echo "dryrun exit $?"
    git add docs/phases/in_progress/383_dryrun_diff.md
    git commit -m "Phase 383: 087's dry-run diff, from the desktop"
    git push
    git log -1 --format=%h

Expected: `scope problems: none`, `Migrations applied on the copy: [87]`,
exit 0; six `videos` rows changed (`file_path` only, each to
`videos/shop_1/session_N/I.mp4`) and one `schema_version` row added. Any
other table or row, or a photo or transcript row, is a scope problem: stop.

After D1 the Mac pulls, shows the diff to the operator (a rule-1 stop:
it changes existing rows), and runs the regression of record.

## D2 — the apply, with the API stopped (the operator's 3A)

Only after the operator's approval is in the phase log and the Mac has
pushed the regression of record:

    git pull --ff-only
    git log -1 --format=%h
    sudo -n systemctl stop motodiag-api.service
    systemctl is-active motodiag-api.service; echo "(expect inactive)"
    .venv/bin/python -B .claude/skills/deploy/deploy.py apply-live 383; echo "apply exit $?"
    .venv/bin/python -B .claude/skills/deploy/deploy.py verify-live 383; echo "verify exit $?"
    git add docs/phases/in_progress/383_live_diff.md
    git commit -m "Phase 383: 087's live diff, from the desktop"
    git push
    git log -1 --format=%h

The API stays stopped until D3.

## D3 — after the merge: the server, then verify_phase

    git -C ~/motodiag/server pull --ff-only
    git -C ~/motodiag/server log -1 --format=%h
    sudo -n systemctl start motodiag-api.service
    sleep 3; systemctl is-active motodiag-api.service
    curl -s http://127.0.0.1:8000/healthz; echo
    git switch master && git pull --ff-only
    .claude/skills/closeout/verify_phase.sh 383 <regression hash> <merge hash>; echo "verify_phase exit $?"
