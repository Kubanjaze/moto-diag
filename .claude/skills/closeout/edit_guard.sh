#!/bin/sh
# Phase 360 edit guard — thin wrapper. All logic is in _edit_guard.py.
# It fails closed: any exit status other than 0 becomes 2, the status that
# blocks the Bash call, so a crash or a missing interpreter never lets a
# command through.
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$DIR/../../.." && pwd)
PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY=python3
"$PY" -B "$DIR/_edit_guard.py"
rc=$?
[ "$rc" -eq 0 ] && exit 0
[ "$rc" -eq 2 ] || echo "edit guard: blocked — the guard exited $rc, and fails closed." >&2
exit 2
