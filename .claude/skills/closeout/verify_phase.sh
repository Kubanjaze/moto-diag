#!/bin/sh
# verify_phase.sh — the operator's terminal check, parameterised.
#
# From the block supplied on 2026-09-22, ten numbered checks preserved in
# order and wording. Two changes, both forced by decisions already taken:
#
#   Check 6 was  awk '{print "tokens:", NF-1}'  over the WHOLE row — pipes,
#   phase number and title included. That is a THIRD counting method,
#   different from both of the two that were argued about, and it is the one
#   that would have passed a 122-word row. Decision 6 says one
#   implementation, so check 6 calls roadmap_words.py.
#
#   Check 5 is tightened to the register format the 255C log uses: not merely
#   that "bug fix #" appears somewhere, but that the numbering is contiguous
#   from #1 and every entry names its commit. closeout_check.py decides that,
#   so this does not become a second implementation either.
#
# Usage:  verify_phase.sh <PHASE> <REG_HASH> <TIP>
set -u
PHASE=${1:?usage: verify_phase.sh PHASE REG_HASH TIP}
REG_HASH=${2:?usage: verify_phase.sh PHASE REG_HASH TIP}
TIP=${3:?usage: verify_phase.sh PHASE REG_HASH TIP}

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$DIR/../../.." && pwd)
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY=python3
cd "$REPO" || exit 1
GIT=/Library/Developer/CommandLineTools/usr/bin/git
[ -x "$GIT" ] || GIT=git

echo "=== 1. master pushed, tree clean ==="
$GIT fetch origin >/dev/null 2>&1
$GIT log origin/master --oneline | grep -E "$TIP" || echo "MISSING"
$GIT status --short; echo "--- unpushed (empty) ---"; $GIT log origin/master..master --oneline

echo "=== 2. no code after regression hash ==="
$GIT diff "$REG_HASH".."$TIP" --stat -- src/ tests/ | tail -3; echo "(empty = docs only)"

echo "=== 3. docs in completed ==="
ls docs/phases/completed/ | grep "^${PHASE}_"
echo "--- in_progress (empty) ---"; ls docs/phases/in_progress/ 2>/dev/null | grep "^${PHASE}_"

echo "=== 4. stubs ==="
grep -n -i "TODO\|TBD\|placeholder\|fill in" docs/phases/completed/${PHASE}_*.md || echo "none"

echo "=== 5. deviations + bug-fix register ==="
grep -n -i "^## .*deviation" docs/phases/completed/${PHASE}_implementation.md
grep -n -i "bug fix #" docs/phases/completed/${PHASE}_phase_log.md | head
echo "--- register contiguous from #1, each naming its commit ---"
"$PY" -B "$DIR/closeout_check.py" "$REPO" "$PHASE" | grep '^A4' || echo "  A4 ok"

echo "=== 6. roadmap row (<=120 words, body cell, links count as one) ==="
"$PY" -B "$DIR/roadmap_words.py" "$PHASE" --check && echo "  within cap"

echo "=== 7. findings header ==="
grep -n -i "highest assigned" docs/FOLLOWUPS.md

echo "=== 8. schema + live db ==="
"$PY" -c "
import sqlite3; c=sqlite3.connect('data/motodiag.db'); q=lambda s:c.execute(s).fetchone()[0]
print('schema', q('select max(version) from schema_version'), '| rows', q('select count(*) from known_issues'))"

echo "=== 9. backup ==="; ls -lh ~/backups/motodiag/

echo "=== 10. targeted tests ==="
PYTHONUTF8=1 "$PY" -m pytest -k "$PHASE" -q 2>&1 | tail -3

echo "=== 11. closeout contract (all seven artefacts) ==="
"$PY" -B "$DIR/closeout_check.py" "$REPO" "$PHASE" && echo "  closeout complete"

echo "=== 12. refuter checklist, if the phase ran one ==="
if grep -q "^## Refuter pass" docs/phases/completed/${PHASE}_phase_log.md 2>/dev/null; then
  "$PY" -B "$DIR/../refute/refute_check.py" \
      "docs/phases/completed/${PHASE}_phase_log.md" && echo "  every row has a verdict, a quote and a page"
else
  echo "  no refuter block (the phase ran no pass, or did not record one)"
fi

echo "=== 13. findings resolve ==="
"$PY" -B "$DIR/../finding/finding_check.py" "$REPO" && echo "  every cited F-number resolves"
