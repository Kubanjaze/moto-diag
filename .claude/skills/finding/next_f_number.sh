#!/bin/sh
# The next free F-number. F-numbers are ONE global sequence across both
# repositories, so both files are read; taking the next from one file alone
# is how two findings end up sharing a number.
set -u
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$DIR/../../.." && pwd)
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY=python3
exec "$PY" -B -c "
import pathlib, re, sys
sys.path.insert(0, '$DIR')
from finding_check import entries
files = [pathlib.Path('$REPO/docs/FOLLOWUPS.md'),
         pathlib.Path('$REPO/../moto-diag-mobile/docs/FOLLOWUPS.md')]
seen, where = set(), {}
for f in files:
    e = entries(f)
    seen |= e
    if e: where[f.name + ' (' + f.parent.parent.name + ')'] = max(e)
for k, v in where.items(): print('  highest in', k, '= F%d' % v)
print('next free: F%d' % ((max(seen) + 1) if seen else 1))
"
