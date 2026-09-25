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

HASH=$(git rev-parse --short HEAD)
if [ "$MODE" = parallel ]; then
  ARGS="-n auto --dist load"
else
  ARGS="-p no:xdist"
fi
CMD="python -m pytest $ARGS"

OUT="$HOME/.cache/motodiag/regressions"; mkdir -p "$OUT"
STEM="$OUT/${HASH}_${MODE}_$(date +%Y%m%d_%H%M%S)"
KEEP_AWAKE=""; command -v caffeinate >/dev/null 2>&1 && KEEP_AWAKE="caffeinate -i"

echo "regression.sh: $CMD at $HASH ($MODE); log $STEM.log"
T0=$(date +%s)
# shellcheck disable=SC2086
PYTHONUTF8=1 $KEEP_AWAKE "$PY" -m pytest $ARGS -rA --junitxml="$STEM.xml" > "$STEM.log" 2>&1
RC=$?
WALL=$(( $(date +%s) - T0 ))

SUMMARY=$(grep -E '^=+ .*(passed|failed|error|no tests ran).* =+$' "$STEM.log" | tail -1)
count() { echo "$SUMMARY" | grep -oE "[0-9]+ $1" | grep -oE '^[0-9]+' || echo 0; }
P=$(count passed); F=$(count failed); E=$(count 'errors?'); S=$(count skipped)

tail -n 25 "$STEM.log"
echo
echo "Regression of record: $P passed, $F failed, $S skipped, $E errors at \`$HASH\`" \
     "($((WALL / 60)) min $((WALL % 60)) s wall, \`$CMD\`, exit $RC)"
exit $RC
