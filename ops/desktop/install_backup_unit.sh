#!/bin/sh
# Phase 345: install the nightly offsite backup. Run once, with sudo:
#   sudo sh ops/desktop/install_backup_unit.sh
# Installs motodiag-backup.service and motodiag-backup.timer, enables and
# starts the timer, and lists it.
set -eu
install -m 644 "$(dirname "$0")/motodiag-backup.service" /etc/systemd/system/motodiag-backup.service
install -m 644 "$(dirname "$0")/motodiag-backup.timer" /etc/systemd/system/motodiag-backup.timer
systemctl daemon-reload
systemctl enable --now motodiag-backup.timer
systemctl list-timers motodiag-backup.timer
