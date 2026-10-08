#!/bin/sh
# clock_check.sh — Phase 378, K19. The tests that turn the real clock into a
# day, month, year or minute, run with the whole process's clock faked.
#
# The files are tests/support/clock_census.py's: every line its census pins,
# and the files whose lines were fixed (CLEARED). Each is run under
# libfaketime, in New York, at Phase 375's four moments: a month's last
# evening, an ordinary evening, New Year's Eve, and 00:30 the next day.
# libfaketime fakes Python's clocks and SQLite's 'now' alike; 370's
# frozen-clock plugin replaces only the session modules' datetime.
#
# Before each moment the script checks its own control: Python's local
# clock and SQLite's localtime both read the faked minute. A clock that was
# not faked is a refusal (exit 2), never a pass.
#
#   clock_check.sh          run them; exit 1 if any moment is red
#   clock_check.sh --list   print the files and stop
#
# Run before a regression of record on a month's last evening (the
# close-out skill, step 1). Needs `brew install libfaketime` (K26: a builder
# may install a Homebrew core tool a test needs, named in the log).
set -u
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$DIR/../../.." && pwd)
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY=python3
cd "$REPO" || exit 2

FILES=$("$PY" -B -c "
import sys
sys.path.insert(0, 'tests')
from support.clock_census import files_to_check
print(' '.join('tests/' + f for f in files_to_check()))") || exit 2

if [ "${1:-}" = "--list" ]; then
  for f in $FILES; do echo "$f"; done
  exit 0
fi

if ! command -v faketime >/dev/null 2>&1; then
  echo "clock_check: faketime is not installed (brew install libfaketime)" >&2
  exit 2
fi

ZONE=America/New_York
rc=0
for MOMENT in "2026-10-31 21:00:00" "2026-10-07 21:00:00" "2026-12-31 21:00:00" \
              "2026-11-01 00:30:00"; do
  WANT=${MOMENT%:00}
  SEEN=$(TZ=$ZONE faketime "$MOMENT" "$PY" -B -c "
import datetime, sqlite3
py = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
db = sqlite3.connect(':memory:').execute(\"select datetime('now', 'localtime')\").fetchone()[0][:16]
print(py if py == db else py + ' / sqlite ' + db)")
  if [ "$SEEN" != "$WANT" ]; then
    echo "clock_check: the clock was not faked at $MOMENT $ZONE (saw: $SEEN)" >&2
    exit 2
  fi
  OUT=$(TZ=$ZONE faketime "$MOMENT" "$PY" -B -m pytest -q -p no:cacheprovider $FILES 2>&1)
  CODE=$?
  echo "== $MOMENT $ZONE: $(printf '%s\n' "$OUT" | tail -1)"
  if [ $CODE -ne 0 ]; then
    printf '%s\n' "$OUT" | grep -E "^(FAILED|ERROR)" >&2
    rc=1
  fi
done
exit $rc
