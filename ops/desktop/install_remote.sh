#!/bin/sh
# Phase 384 (the operator's 1A): the Mac's way in to this desktop's deploy
# steps. Run once, from the development checkout, in the Ubuntu window:
#
#     sudo sh ops/desktop/install_remote.sh <the Mac's tailnet address> ['<the Mac's public key>']
#
# The key may be given as the second argument, so nothing the install runs
# can read it from the terminal first; without it, the script asks.
#
# 1. Tailscale inside Ubuntu, a second device, motodiag-ops, tagged (its key
#    does not expire), leaving Ubuntu's name lookups alone and Tailscale's
#    own SSH off (it serves file transfer itself, so it cannot hold a fixed
#    list). The operator signs it in once, in a browser.
# 2. OpenSSH listening on that device's tailnet IPv4 address only. The home
#    network has no such address. FreeBind lets the socket bind at boot
#    before Tailscale has the address.
# 3. Keys only, from the Mac's tailnet address only, user lilcu only, no
#    terminal, no forwarding, and every request runs the dispatcher.
# 4. The Mac's public key, restricted to the dispatcher and the Mac's address.
# 5. The dispatcher, root-owned outside the checkout: a branch pulled here
#    cannot change what the key may run.
set -eu
MAC_IP=${1:?usage: sudo sh ops/desktop/install_remote.sh <the Mac tailnet address>}
case "$MAC_IP" in 100.*.*.*) ;; *) echo "not a tailnet address: $MAC_IP"; exit 1 ;; esac
[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }
USER_NAME=${SUDO_USER:?run with sudo from your own Ubuntu account}
HOME_DIR=$(getent passwd "$USER_NAME" | cut -d: -f6)
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
DISPATCHER=/usr/local/libexec/motodiag-remote
MARK="# motodiag-ops (Phase 384): the Mac's key runs the fixed list only"

echo "--- 1. Tailscale inside Ubuntu"
command -v tailscale >/dev/null 2>&1 || curl -fsSL https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled
tailscale up --hostname=motodiag-ops --advertise-tags=tag:motodiag-ops \
  --accept-dns=false --ssh=false
TS4=$(tailscale ip -4)
case "$TS4" in 100.*.*.*) echo "motodiag-ops is $TS4" ;; *) echo "no tailnet address"; exit 1 ;; esac

echo "--- 2. OpenSSH"
apt-get install -y openssh-server >/dev/null
systemctl list-unit-files ssh.socket >/dev/null 2>&1 \
  || { echo "this Ubuntu has no ssh.socket"; exit 1; }

echo "--- 3. the dispatcher"
install -d -o root -g root -m 755 /usr/local/libexec
install -o root -g root -m 755 "$REPO/ops/desktop/motodiag_remote.py" "$DISPATCHER"

echo "--- 4. the SSH server's settings"
cat > /etc/ssh/sshd_config.d/10-motodiag-ops.conf <<EOF
$MARK
ListenAddress $TS4:22
AllowUsers $USER_NAME@$MAC_IP
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
DisableForwarding yes
PermitTTY no
PermitUserRC no
ForceCommand $DISPATCHER
EOF
sshd -t
mkdir -p /etc/systemd/system/ssh.socket.d
cat > /etc/systemd/system/ssh.socket.d/10-motodiag-ops.conf <<EOF
$MARK
[Socket]
ListenStream=
ListenStream=$TS4:22
FreeBind=yes
EOF

echo "--- 5. the Mac's key"
AK="$HOME_DIR/.ssh/authorized_keys"
if [ -s "$AK" ] && ! grep -qF "$MARK" "$AK"; then
  echo "$AK already holds keys this script did not write; nothing changed"; exit 1
fi
KEY=${2:-}
if [ -z "$KEY" ]; then
  printf "Paste the Mac's public key (one line starting ssh-ed25519), then press Enter: "
  read -r KEY
fi
case "$KEY" in "ssh-ed25519 "*) ;; *) echo "not an ssh-ed25519 public key"; exit 1 ;; esac
[ "$(printf '%s\n' "$KEY" | wc -w)" -le 3 ] || { echo "more than one key line"; exit 1; }
# A key copied from a wrapped window can carry a line break inside the quotes:
# two words, so the word count passes, and a broken key file (the advisor, 384).
[ "$(printf '%s' "$KEY" | wc -l)" -eq 0 ] || { echo "the key is broken across lines"; exit 1; }
install -d -o "$USER_NAME" -g "$USER_NAME" -m 700 "$HOME_DIR/.ssh"
printf '%s\nrestrict,from="%s",command="%s" %s\n' "$MARK" "$MAC_IP" "$DISPATCHER" "$KEY" > "$AK"
chown "$USER_NAME:$USER_NAME" "$AK"
chmod 600 "$AK"
[ "$(wc -l < "$AK")" -eq 2 ] || { echo "$AK is not the mark and one key line"; exit 1; }

echo "--- 6. start it, and show what listens on port 22"
systemctl daemon-reload
systemctl disable --now ssh.service >/dev/null 2>&1 || true
systemctl enable ssh.socket >/dev/null 2>&1
systemctl restart ssh.socket
LISTEN=$(ss -Hltn 'sport = :22' | awk '{print $4}')
echo "listening on port 22: $LISTEN"
[ "$LISTEN" = "$TS4:22" ] || { echo "port 22 listens somewhere else too"; exit 1; }
echo "installed: motodiag-ops $TS4, the Mac $MAC_IP only"
