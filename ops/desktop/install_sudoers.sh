#!/bin/sh
# Phase 382: let lilcu start, stop and restart the live API's unit, and
# nothing else, without a password (the deploy skill's restart after a
# merge). Run once:  sudo sh ops/desktop/install_sudoers.sh
# Phase 406 (K93): the second line, for the Mac's way in: the payments
# feed's start, stop and restart, and the fleet's restart. Nothing else:
# no other unit, no other verb, no systemd-run.
set -eu
RULE=/etc/sudoers.d/motodiag-api
TMP=$(mktemp)
cat > "$TMP" <<'RULES'
lilcu ALL=(root) NOPASSWD: /usr/bin/systemctl start motodiag-api.service, /usr/bin/systemctl stop motodiag-api.service, /usr/bin/systemctl restart motodiag-api.service
lilcu ALL=(root) NOPASSWD: /usr/bin/systemctl start motodiag-payments.service, /usr/bin/systemctl stop motodiag-payments.service, /usr/bin/systemctl restart motodiag-payments.service, /usr/bin/systemctl restart motodiag-fleet.service
RULES
visudo -cf "$TMP"
install -m 440 "$TMP" "$RULE"
rm -f "$TMP"
visudo -c
