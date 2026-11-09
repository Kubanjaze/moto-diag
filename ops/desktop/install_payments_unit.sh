#!/bin/sh
# Phase 371: install the payments feed. Run once, with sudo:
#   sudo sh ops/desktop/install_payments_unit.sh
# Installs motodiag-payments.service, enables and starts it, and shows its
# status.
set -eu
install -m 644 "$(dirname "$0")/motodiag-payments.service" /etc/systemd/system/motodiag-payments.service
systemctl daemon-reload
systemctl enable --now motodiag-payments.service
systemctl status --no-pager motodiag-payments.service
