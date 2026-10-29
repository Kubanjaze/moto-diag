#!/bin/bash
# regression.sh — the regression of record, one implementation (Phase 355).
#
# Runs the full suite in parallel and prints the regression line the phase
# log records: the counts, the commit and the command that produced them.
#
#   regression.sh            the canonical run: pytest -n auto --dist load
#   regression.sh --serial   the fallback: the same suite, one process
#
# Serial is for a machine without pytest-xdist, or for bisecting a failure
# that appears only in parallel. Phase 355 measured both on one tree and
# proved the same 9,375 passed IDs either way.
#
# It refuses a dirty tree: the hash has to name the tree that was tested.
# It runs under caffeinate because pytest's clock stops while the Mac sleeps.
# In 355's serial baseline, a 49:40 wall read 30:33.
# Logs and junit go to ~/.cache/motodiag/regressions/, never into the repo.
set -u
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$DIR/../../.." && pwd)
cd "$REPO" || exit 2
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY=python3

MODE=parallel
case "${1:-}" in
  "") ;;
  --serial) MODE=serial ;;
  *) echo "usage: regression.sh [--serial]" >&2; exit 2 ;;
esac

if [ -n "$(git status --porcelain)" ]; then
  echo "regression.sh: the tree is dirty; commit first so the hash names what was tested" >&2
  git status --short >&2
  exit 2
fi

# Phase 358 (K1): the whole-tree command's --full mode must have passed on
# exactly this commit first, as a record only wholetree.sh can write.
"$PY" -B "$DIR/wholetree.py" verify || exit 2

HASH=$(git rev-parse --short HEAD)
if [ "$MODE" = parallel ]; then
  ARGS="-n auto --dist load"
else
  ARGS="-p no:xdist"
fi
# Phase 393 (K54): the regression of record measures line coverage. The
# data and the JSON go beside the log, never into the repository.
ARGS="$ARGS --cov=motodiag"
CMD="python -m pytest $ARGS"

OUT="$HOME/.cache/motodiag/regressions"; mkdir -p "$OUT"
STEM="$OUT/${HASH}_${MODE}_$(date +%Y%m%d_%H%M%S)"
export COVERAGE_FILE="$STEM.coverage"
KEEP_AWAKE=""; command -v caffeinate >/dev/null 2>&1 && KEEP_AWAKE="caffeinate -i"

echo "regression.sh: $CMD at $HASH ($MODE); log $STEM.log"
T0=$(date +%s)
# shellcheck disable=SC2086
PYTHONUTF8=1 $KEEP_AWAKE "$PY" -m pytest $ARGS --cov-report="json:$STEM.coverage.json" \
  --cov-report= -rA --junitxml="$STEM.xml" > "$STEM.log" 2>&1
RC=$?
WALL=$(( $(date +%s) - T0 ))

# Phase 393: coverage may not fall below its pin (tests/support/quality_counts.py).
# Below it, the run is not of record: RC=1 makes its line "FAILED".
GATE=$("$PY" -B "$REPO/scripts/code_quality.py" coverage-gate "$STEM.coverage.json" "$HASH") \
  || RC=1

tail -n 25 "$STEM.log"
echo
# F206 (Phase 383): the line's writer sits beside A5's reader, in one file.
# A failing run prints "Regression run FAILED (not of record):"; each skip
# follows on its own line, with its file and reason.
"$PY" -B "$DIR/closeout_check.py" --format-regression "$STEM.log" "$HASH" "$WALL" "$CMD" "$RC" \
  || exit 2
echo "$GATE"
echo "Coverage data: $STEM.coverage.json"
exit $RC
