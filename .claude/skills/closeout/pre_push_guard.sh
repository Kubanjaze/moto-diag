#!/bin/sh
# Phase 255D push guard — thin wrapper. All logic is in _pre_push_guard.py,
# which filters itself: it exits 0 unless the command really is a git push.
# See that file's docstring for why it does not rely on the hook's `if`.
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$DIR/../../.." && pwd)
PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY=python3
exec "$PY" -B "$DIR/_pre_push_guard.py"
