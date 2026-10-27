#!/bin/sh
# Phase 390 (F221): let lilcu run `fstrim -v /`, that one command line and
# nothing else, without a password, so the fleet's dispatcher can hand the
# space Ubuntu has freed back to Windows (the disk image is sparse). A model
# call cannot use it: the fence's bubblewrap sets no_new_privs, so sudo
# inside the fence fails. Run once:  sudo sh ops/desktop/install_fstrim_sudoers.sh
set -eu
RULE=/etc/sudoers.d/motodiag-fstrim
TMP=$(mktemp)
cat > "$TMP" <<'RULES'
lilcu ALL=(root) NOPASSWD: /usr/sbin/fstrim -v /
RULES
visudo -cf "$TMP"
install -m 440 "$TMP" "$RULE"
rm -f "$TMP"
visudo -c
