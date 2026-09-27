#!/bin/sh
# The whole-tree command (Phase 358, K1) — thin wrapper. All logic is in
# wholetree.py; read its docstring.
#
#   wholetree.sh          fast mode: what the push guard runs
#   wholetree.sh --full   every whole-tree test: before the regression of
#                         record and before a commit to seed data or migrations
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$DIR/../../.." && pwd)
PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY=python3
cd "$REPO" || exit 2
exec "$PY" -B "$DIR/wholetree.py" "$@"
