# Phase 409 prebuild — putting the server on api.getmekno.com

**For Kerwyn.** Nothing here runs until Phase 210 has merged and this branch's pull request has merged after it. Each step says which computer and which window, gives one block to paste, and the block ends with ALL GOOD or SOMETHING IS OFF. If you see SOMETHING IS OFF, stop and paste the last lines into the project chat.

The checks come first and change nothing. The steps that change something each say what they change and how it is undone.

What you decided on 2026-11-25 (the plan page, `docs/reports/2026-11-25_409_prebuild_plan.md`, has the reasons): the way in is a Cloudflare Tunnel; the name is `api.getmekno.com`; the API's help pages go off; share links stay off; manuals over 100 MB keep uploading over Tailscale for now. Step 5's settings carry these.

**Before Step 4 (the tunnel), two things must be true:** the privacy page on getmekno.com names Cloudflare for the app's traffic (Step 1 checks it), and the app's copy of the API has been refreshed.

---

### Step 1. Check the desktop, change nothing

**Which computer:** the home desktop. **Which window:** the Ubuntu terminal.

It checks that the app server and the payments feed are running, that the server answers on its own machine and only there, whether the server runs the code with the new protections yet, that getmekno.com's names are kept by Cloudflare, whether the privacy page names Cloudflare for the app, and whether a tunnel is installed yet.

```bash
bash <<'EOF409A'
set -u
bad() { echo; echo "SOMETHING IS OFF: $1"; exit 1; }
SRV=~/motodiag/server
for u in motodiag-api motodiag-payments; do
  [ "$(systemctl is-active "$u")" = active ] || bad "$u is not running; nothing was changed"
done
echo "The app server and the payments feed are running."
curl -fsS -m 10 http://127.0.0.1:8000/healthz | grep -q '"status":"ok"' || bad "the server does not answer healthy on this machine"
echo "The server answers healthy on this machine."
LISTEN=$(ss -Hltn 'sport = :8000' | awk '{print $4}')
[ "$LISTEN" = "127.0.0.1:8000" ] || bad "the server listens on '$LISTEN', not only on 127.0.0.1:8000"
echo "It listens only on this machine (127.0.0.1:8000)."
if [ -f "$SRV/src/motodiag/auth/login_throttle.py" ]; then
  echo "The server's code already has the new protections."
else
  echo "The server's code does not have the new protections yet (Step 2 brings them)."
fi
NS=$(curl -fsS -m 15 -H 'accept: application/dns-json' 'https://cloudflare-dns.com/dns-query?name=getmekno.com&type=NS') || bad "could not look up getmekno.com's name servers"
echo "$NS" | grep -qi 'ns.cloudflare.com' || bad "getmekno.com's names are not kept by Cloudflare"
echo "getmekno.com's names are kept by Cloudflare."
PRIV=$(curl -fsS -m 15 https://getmekno.com/privacy/ 2>/dev/null) || bad "could not read getmekno.com/privacy/"
if echo "$PRIV" | grep -qi 'cloudflare, for the connection'; then
  echo "The privacy page names Cloudflare for the app's traffic."
else
  echo "Note: the privacy page does not name Cloudflare for the app yet. Do not do Step 4 until it does."
fi
if command -v cloudflared >/dev/null 2>&1; then
  echo "Note: cloudflared is already installed ($(cloudflared --version 2>&1 | head -1)); Step 4 will reuse it."
else
  echo "No tunnel is installed yet."
fi
echo
echo "ALL GOOD"
EOF409A
```

### Step 2. Put the server on the merged code

**Which computer:** the Mac. **Which window:** Terminal. Only after this branch's pull request is merged (after 210's).

It asks GitHub for the merge and moves the server onto it through the Mac's way in, as every merge does. If the server or the payments feed does not come back, the code is put back and both are restarted on it. Nothing the server does changes yet: every new setting is off or as today until Step 5, except the sign-in guard, the protective headers and the size cap, which change nothing the app sees.

```bash
bash <<'EOF409B'
set -u
bad() { echo; echo "SOMETHING IS OFF: $1"; exit 1; }
R=Kubanjaze/moto-diag
BRANCH=prebuild-409-public-address
REPO=~/Projects/moto-diag
PY="$REPO/.venv/bin/python"
RM="$REPO/.claude/skills/deploy/remote.py"
export GH_PAGER=cat GH_PROMPT_DISABLED=1
{ [ -x "$PY" ] && [ -f "$RM" ]; } || bad "this is not the Mac with the project (run it on the Mac, in Terminal); nothing was changed"
MERGE=$(gh pr list -R "$R" --state merged --head "$BRANCH" --json mergeCommit --jq '.[0].mergeCommit.oid // empty' < /dev/null) || bad "GitHub could not be asked; nothing was changed, so paste this again in a minute"
[ -n "$MERGE" ] || bad "the pull request is not merged yet: merge it first; nothing was changed"
echo "The merge is $MERGE."
"$PY" "$RM" server-update "$MERGE" < /dev/null || bad "the server did not move onto the merged code (the lines above say why)"
echo
echo "ALL GOOD"
EOF409B
```

Then paste Step 1 again on the desktop: it must now say "The server's code already has the new protections."

### Step 3. Make the tunnel in Cloudflare (in the browser, no block)

**Which computer:** either. **Which window:** the browser, signed in to Cloudflare.

1. Open https://one.dash.cloudflare.com, then **Networks**, then **Tunnels**, then **Create a tunnel**.
2. Pick **Cloudflared**. Name it `mekno-api`. Save.
3. On the next page, under the install commands, choose **Debian**, **64-bit**. The command shown ends in a long token after `service install`. **Copy only that long token**, not the whole command. Do not paste it into the chat.
4. Click **Next**. Add a public hostname: subdomain `api`, domain `getmekno.com`, type **HTTP**, URL `127.0.0.1:8000`. It must be `127.0.0.1`, not `localhost`. Save.

### Step 4. Install the tunnel on the desktop

**Which computer:** the home desktop. **Which window:** the Ubuntu terminal. Have the token from Step 3 copied.

It first checks the privacy page names Cloudflare for the app. Then it downloads Cloudflare's tunnel program from Cloudflare's own release page, installs it, and asks you to paste the token (it is not shown on screen and not kept in the history). It sets the tunnel up as a service that starts with the desktop, and checks it connected. It asks for your Ubuntu password. To undo: the last block on this page.

```bash
bash <<'EOF409C'
set -u
bad() { echo; echo "SOMETHING IS OFF: $1"; exit 1; }
curl -fsS -m 15 https://getmekno.com/privacy/ | grep -qi 'cloudflare, for the connection' || bad "the privacy page does not name Cloudflare for the app yet; nothing was changed"
[ -f ~/motodiag/server/src/motodiag/auth/login_throttle.py ] || bad "the server's code does not have the new protections yet: do Step 2 first; nothing was changed"
if ! command -v cloudflared >/dev/null 2>&1; then
  TMP=$(mktemp -d)
  curl -fsSL -m 120 -o "$TMP/cloudflared.deb" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb || bad "could not download the tunnel program; nothing was changed"
  sudo dpkg -i "$TMP/cloudflared.deb" >/dev/null || bad "could not install the tunnel program"
  rm -rf "$TMP"
fi
echo "Tunnel program: $(cloudflared --version 2>&1 | head -1)"
if systemctl list-unit-files cloudflared.service >/dev/null 2>&1 && [ "$(systemctl is-active cloudflared)" = active ]; then
  echo "The tunnel service is already installed and running."
else
  printf "Paste the tunnel token from Cloudflare, then press Enter: "
  read -rs TOKEN < /dev/tty; echo
  [ "${#TOKEN}" -gt 100 ] || bad "that does not look like the token (it is very long); nothing was installed"
  sudo cloudflared service install "$TOKEN" >/dev/null 2>&1 || bad "Cloudflare did not take the token; copy it again from Step 3"
  unset TOKEN
fi
sleep 5
[ "$(systemctl is-active cloudflared)" = active ] || bad "the tunnel service is not running"
systemctl is-enabled cloudflared >/dev/null || bad "the tunnel will not start with the desktop"
echo "The tunnel is running and starts with the desktop."
ok=""
for i in $(seq 1 30); do
  curl -fsS -m 10 https://api.getmekno.com/healthz 2>/dev/null | grep -q '"status":"ok"' && { ok=1; break; }
  sleep 4
done
[ -n "$ok" ] || bad "api.getmekno.com does not answer healthy yet (check Step 3's public hostname, then paste this again)"
echo "https://api.getmekno.com/healthz answers healthy, with a valid certificate."
echo
echo "ALL GOOD"
EOF409C
```

### Step 5. Give the server its public settings

**Which computer:** the home desktop. **Which window:** the Ubuntu terminal.

It copies the server's settings file first (once: a second run keeps the first copy), then sets: the public address; the names the server answers to (the public one, the tailnet one, and this machine); the one web page allowed to call it from a browser; the help pages off; and the address shown in the API's description. It restarts the app server and checks it answers on this machine, on the tailnet name and on the public name. If the server does not come back healthy on this machine, the old settings are put back and it is restarted on them.

```bash
bash <<'EOF409D'
set -u
bad() { echo; echo "SOMETHING IS OFF: $1"; exit 1; }
ENVF=~/.config/motodiag/server.env
TS=desktop-76s9bqv.taila45995.ts.net
[ -f "$ENVF" ] || bad "the server's settings file is missing; nothing was changed"
BK="$ENVF.pre409"
if [ -f "$BK" ]; then
  echo "The settings from before the first run are already kept at $BK (kept as they are)."
else
  cp -p "$ENVF" "$BK" || bad "could not copy the settings; nothing was changed"
  echo "Old settings kept at $BK"
fi
RUNBK=$(mktemp)
cp -p "$ENVF" "$RUNBK"
NEW=$(mktemp)
grep -vE '^(MOTODIAG_PUBLIC_BASE_URL|MOTODIAG_API_ALLOWED_HOSTS|MOTODIAG_API_CORS_ORIGINS|MOTODIAG_API_DOCS_ENABLED|MOTODIAG_API_SERVERS)=' "$ENVF" > "$NEW"
cat >> "$NEW" <<SETTINGS
MOTODIAG_PUBLIC_BASE_URL=https://api.getmekno.com
MOTODIAG_API_ALLOWED_HOSTS=api.getmekno.com,$TS,127.0.0.1,localhost
MOTODIAG_API_CORS_ORIGINS=https://getmekno.com
MOTODIAG_API_DOCS_ENABLED=false
MOTODIAG_API_SERVERS=https://api.getmekno.com|Live
SETTINGS
install -m 600 "$NEW" "$ENVF"; rm -f "$NEW"
sudo /usr/bin/systemctl restart motodiag-api.service
ok=""
for i in $(seq 1 20); do
  sleep 2
  curl -fsS -m 5 http://127.0.0.1:8000/healthz 2>/dev/null | grep -q '"status":"ok"' && { ok=1; break; }
done
if [ -z "$ok" ]; then
  install -m 600 "$RUNBK" "$ENVF"; rm -f "$RUNBK"
  sudo /usr/bin/systemctl restart motodiag-api.service
  bad "the server did not come back healthy on the new settings; the old ones are back and it was restarted on them"
fi
rm -f "$RUNBK"
echo "The server answers healthy on this machine, on the new settings."
curl -fsS -m 20 https://api.getmekno.com/healthz | grep -q '"status":"ok"' || bad "api.getmekno.com does not answer healthy"
echo "The public name answers healthy."
if curl -fsS -m 20 "https://$TS/healthz" 2>/dev/null | grep -q '"status":"ok"'; then
  echo "The tailnet name still answers healthy, for shop one's phones."
else
  echo "Note: this window could not reach the tailnet name; check it from the phone (Step 6)."
fi
echo
echo "ALL GOOD"
EOF409D
```

### Step 6. Check from outside

**Which computer:** the Mac. **Which window:** Terminal. Then the phone.

The block asks the public name what anyone on the internet would get: healthy with a valid certificate and the protective headers, no help pages, no shop's details without signing in, a wrong name at sign-in refused, and nothing else on the desktop reachable. It changes nothing.

```bash
bash <<'EOF409E'
set -u
bad() { echo; echo "SOMETHING IS OFF: $1"; exit 1; }
B=https://api.getmekno.com
code() { curl -s -o /dev/null -m 20 -w '%{http_code}' "$@"; }
curl -fsS -m 20 "$B/healthz" | grep -q '"status":"ok"' || bad "$B/healthz does not answer healthy over https with a valid certificate"
echo "healthz: healthy, valid certificate."
H=$(curl -sS -m 20 -D - -o /dev/null "$B/healthz")
echo "$H" | grep -qi '^strict-transport-security:' || bad "the answer has no HSTS header"
echo "$H" | grep -qi '^x-content-type-options: *nosniff' || bad "the answer has no nosniff header"
echo "Protective headers: present."
for p in /docs /redoc /openapi.json; do
  [ "$(code "$B$p")" = 404 ] || bad "$p is open on the public name"
done
echo "Help pages: off."
[ "$(code "$B/v1/shops/1")" = 401 ] || bad "a shop's details answer without signing in"
echo "A shop's details: refused without signing in."
[ "$(code -X POST -H 'Content-Type: application/json' -d '{"username":"nobody-409-check","password":"x"}' "$B/v1/auth/login")" = 401 ] || bad "sign-in did not refuse a wrong name"
echo "Sign-in: a wrong name is refused."
for port in 22 8000 8080; do
  if nc -z -w 5 api.getmekno.com "$port" 2>/dev/null; then bad "port $port answers on the public name"; fi
done
echo "Ports 22, 8000, 8080: nothing answers."
echo
echo "ALL GOOD"
EOF409E
```

**On the phone:** turn Wi-Fi off (mobile data only), open Safari, go to `https://api.getmekno.com/healthz`. It should show `"status":"ok"`. Then go to `https://api.getmekno.com/docs`: it should say `Not Found`. Turn Wi-Fi back on.

---

### To undo all of it

**Which computer:** the home desktop. **Which window:** the Ubuntu terminal.

It stops and removes the tunnel service (the public name stops answering at once), and puts back the settings Step 5 copied, then restarts the server. The tailnet way in is untouched throughout. The tunnel itself can then be deleted in Cloudflare (Networks, Tunnels, `mekno-api`, Delete).

```bash
bash <<'EOF409F'
set -u
bad() { echo; echo "SOMETHING IS OFF: $1"; exit 1; }
if command -v cloudflared >/dev/null 2>&1; then
  sudo cloudflared service uninstall >/dev/null 2>&1 || true
fi
[ "$(systemctl is-active cloudflared 2>/dev/null)" != active ] || bad "the tunnel service is still running"
echo "The tunnel is stopped and removed."
BK=~/.config/motodiag/server.env.pre409
if [ -f "$BK" ]; then
  install -m 600 "$BK" ~/.config/motodiag/server.env
  sudo /usr/bin/systemctl restart motodiag-api.service
  sleep 5
  echo "The settings from before Step 5 are back (from $BK, which is kept)."
else
  echo "Step 5 never ran, so the settings were not touched."
fi
curl -fsS -m 10 http://127.0.0.1:8000/healthz | grep -q '"status":"ok"' || bad "the server does not answer healthy on this machine"
echo "The server answers healthy on this machine."
echo
echo "ALL GOOD"
EOF409F
```

---

**What was tested, and how.** Every block was run through `bash -n` and `shellcheck`, and Step 5's settings change and its put-back were run against a stand-in settings file and stand-in commands in a scratch folder, in the cloud. None has been run on the desktop or the Mac yet: the first real run is yours, read-only first (Step 1).
