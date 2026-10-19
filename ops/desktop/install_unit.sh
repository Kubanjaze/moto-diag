#!/bin/sh
# Phase 382: install and enable the live API's unit. Run once, with sudo:
#   sudo sh ops/desktop/install_unit.sh
# It does not start the service; the cut-over does, after live's sha256 check.
set -eu
install -m 644 "$(dirname "$0")/motodiag-api.service" /etc/systemd/system/motodiag-api.service
systemctl daemon-reload
systemctl enable motodiag-api.service
systemctl is-enabled motodiag-api.service
