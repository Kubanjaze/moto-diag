#!/bin/sh
# Phase 406 (K93): put this checkout's dispatcher where Phase 384 put it,
# root-owned, and add the password-free restarts the Mac's new operations
# need. Run once, from the development checkout at the merge, in the
# Ubuntu window:
#
#     sudo sh ops/desktop/update_remote.sh
#
# It changes no SSH setting and no key: those are install_remote.sh's, and
# the lock stays as 384 made it.
set -eu
[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
DISPATCHER=/usr/local/libexec/motodiag-remote
NEW="$REPO/ops/desktop/motodiag_remote.py"
[ -f "$DISPATCHER" ] || { echo "no dispatcher at $DISPATCHER: run install_remote.sh first"; exit 1; }
python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' "$NEW" \
  || { echo "the new dispatcher does not parse; nothing changed"; exit 1; }
echo "--- 1. the dispatcher"
install -o root -g root -m 755 "$NEW" "$DISPATCHER"
echo "--- 2. the password-free restarts"
sh "$REPO/ops/desktop/install_sudoers.sh"
echo "installed: $DISPATCHER, root-owned, sha256 $(sha256sum "$DISPATCHER" | cut -c1-16)"
