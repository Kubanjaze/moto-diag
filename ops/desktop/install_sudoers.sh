#!/bin/sh
# Phase 382: let lilcu start, stop and restart the live API's unit, and
# nothing else, without a password (the deploy skill's restart after a
# merge). Run once:  sudo sh ops/desktop/install_sudoers.sh
set -eu
RULE=/etc/sudoers.d/motodiag-api
TMP=$(mktemp)
cat > "$TMP" <<'RULES'
lilcu ALL=(root) NOPASSWD: /usr/bin/systemctl start motodiag-api.service, /usr/bin/systemctl stop motodiag-api.service, /usr/bin/systemctl restart motodiag-api.service
RULES
visudo -cf "$TMP"
install -m 440 "$TMP" "$RULE"
rm -f "$TMP"
visudo -c
