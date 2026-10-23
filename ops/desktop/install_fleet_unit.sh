#!/bin/sh
# Phase 388: install and enable the fleet dispatcher's unit. Run once, with sudo:
#   sudo sh ops/desktop/install_fleet_unit.sh
# It does not start the service: the operator does, once the fleet's token is
# in ~/.config/motodiag/anthropic.env.
set -eu
install -m 644 "$(dirname "$0")/motodiag-fleet.service" /etc/systemd/system/motodiag-fleet.service
systemctl daemon-reload
systemctl enable motodiag-fleet.service
systemctl is-enabled motodiag-fleet.service
