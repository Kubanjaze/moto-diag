# Phase 388 — the operator's steps

Four steps, all on the **home desktop** (the Windows PC). Each is one block
to paste, and each ends by printing **ALL GOOD** or **SOMETHING IS OFF**.
Send back what it printed. Steps 1 to 3 are for tonight or tomorrow
morning; step 4 is the restart test, whenever suits.

The "Ubuntu window" is the Ubuntu terminal on the desktop (Start menu,
type Ubuntu). The "administrator PowerShell" is Start menu, type
PowerShell, right-click it, "Run as administrator".

---

## Step 1 — give the fleet its own sign-in to Claude

**Why:** the dispatcher runs Claude by itself, inside a locked box that
cannot see your own Claude login (on purpose). It needs a sign-in of its
own: a long-lived token tied to your Max subscription. Only you can make
one.

**Where:** the desktop, the Ubuntu window.

**What happens:** the first command prints a web address. Open it, sign in
with your Claude account (the Max one), and approve. The terminal then
prints a long token starting with `sk-ant-oat`. Copy it, and when the
second prompt says "Paste the token here", paste it and press Enter. It
will not show as you paste: that is on purpose. **Never paste the token
into a chat, a message or a document.**

```
claude setup-token && read -rsp "Paste the token here (it will not show), then press Enter: " T && echo && mkdir -p ~/.config/motodiag && printf 'CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$T" > ~/.config/motodiag/anthropic.env && chmod 600 ~/.config/motodiag/anthropic.env; unset T; F=~/.config/motodiag/anthropic.env; if [ "$(grep -c '' "$F" 2>/dev/null)" = 1 ] && [ "$(grep -cE '^CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat[A-Za-z0-9_-]+$' "$F")" = 1 ] && [ "$(grep -o 'sk-ant-oat' "$F" | grep -c '')" = 1 ] && [ -n "$(find "$F" -perm 600 2>/dev/null)" ]; then echo "ALL GOOD"; else echo "SOMETHING IS OFF"; fi
```

The check passes only when the file is one line holding exactly one token,
made only of letters, digits, `-` and `_`, with nothing after it, and only
you can read the file. (Its first version checked only how the line
started, and passed a file holding the token five times with a stray
control character, 2026-10-22.) If it says SOMETHING IS OFF, run the block
again: the paste may have been doubled.

**Then:** tell me it printed ALL GOOD. I run the rest of the checks
myself: one tiny test message to confirm the token is billed to your
subscription and not to an API account, the locked box with the token in
it, and the dispatcher's first real review.

**After my tiny test message:** open claude.ai, Settings, Usage, and the
Anthropic Console's billing page. I will say when. Usage should move (it
may not move by a whole percent for one message); the Console's billing
must not.

---

## Step 2 — install the dispatcher as a service, then restart it once

**Why:** so the dispatcher runs all the time in the background and starts
by itself whenever Ubuntu starts. Installing it needs your password
(`sudo`), so it is yours to run. The block installs it, starts it, restarts
it once, and checks it came back.

**Where:** the desktop, the Ubuntu window. **Only after step 1 printed
ALL GOOD and I have said the first review worked.**

```
sudo sh ~/motodiag/fleet/code/ops/desktop/install_fleet_unit.sh && sudo systemctl start motodiag-fleet.service && sleep 10 && sudo systemctl restart motodiag-fleet.service && sleep 10 && systemctl show motodiag-fleet.service -p ActiveState -p ActiveEnterTimestamp -p NRestarts && if systemctl is-active --quiet motodiag-fleet.service; then echo "ALL GOOD"; else echo "SOMETHING IS OFF"; systemctl status motodiag-fleet.service --no-pager | tail -15; fi
```

---

## Step 3 — make Windows keep Ubuntu running for the dispatcher at startup

**Why:** Windows stops Ubuntu when nothing is using it. The live server
already has a startup task that keeps Ubuntu up; this adds a second one,
just for the dispatcher, so it does not depend on the server's. Creating a
startup task needs an administrator.

**Where:** the desktop, the administrator PowerShell.

```
$xml = "\\wsl.localhost\Ubuntu-26.04\home\lilcu\motodiag\fleet\code\ops\desktop\motodiag-fleet-boot.xml"; Register-ScheduledTask -TaskPath "\motodiag\" -TaskName "fleet-boot" -Xml ((Get-Content $xml -Raw) -replace '^<\?xml[^>]*\?>\s*','') | Out-Null; Start-ScheduledTask -TaskPath "\motodiag\" -TaskName "fleet-boot"; Start-Sleep 5; $s = (Get-ScheduledTask -TaskPath "\motodiag\" -TaskName "fleet-boot").State; if ("$s" -eq "Running") { "ALL GOOD" } else { "SOMETHING IS OFF: the task is $s" }
```

(It registers the task with `Register-ScheduledTask` and drops the file's
first line, the `<?xml … encoding="UTF-8"?>` declaration: `schtasks
/Create /XML` refuses a UTF-8 task file with "unable to switch the
encoding", as it did for the live server's task.)

---

## Step 4 — the restart test (whenever suits; about 15 minutes)

**Why:** to see the dispatcher come back by itself after Windows restarts,
with nobody signed in, the same test the live server passed on October 19.
It runs twice: once with the dispatcher's startup task switched off (it
should **fail**: the dispatcher waits for you), once with it on (it should
**pass**). The live server's own task is switched off both times, to show
the dispatcher no longer depends on it; the last block switches it back on.
The live server is down for those few minutes.

**4a. The failing run.** In the administrator PowerShell:

```
schtasks /Change /TN "\motodiag\fleet-boot" /DISABLE; schtasks /Change /TN "\motodiag\wsl-boot" /DISABLE; if ($LASTEXITCODE -eq 0) { "ALL GOOD: restarting in 30 seconds"; shutdown /r /t 30 } else { "SOMETHING IS OFF" }
```

Wait until the PC has restarted and **five minutes more without signing
in**. Then sign in, open the Ubuntu window, and paste:

```
python3 ~/motodiag/fleet/code/ops/desktop/fleet_boot_check.py
```

**This one should print SOMETHING IS OFF** ("it waited for you"): with no
startup task, Ubuntu only starts when you open it.

**4b. The passing run.** In the administrator PowerShell:

```
schtasks /Change /TN "\motodiag\fleet-boot" /ENABLE; if ($LASTEXITCODE -eq 0) { "ALL GOOD: restarting in 30 seconds"; shutdown /r /t 30 } else { "SOMETHING IS OFF" }
```

Again wait for the restart and **five minutes more without signing in**.
Then sign in, open the Ubuntu window, and paste:

```
python3 ~/motodiag/fleet/code/ops/desktop/fleet_boot_check.py
```

**This one should print ALL GOOD** ("came up … before you signed in").

**4c. Switch the live server's task back on.** In the administrator
PowerShell:

```
schtasks /Change /TN "\motodiag\wsl-boot" /ENABLE; schtasks /Run /TN "\motodiag\wsl-boot" | Out-Null; Start-Sleep 5; $s = (schtasks /Query /TN "motodiag\wsl-boot" /FO LIST | Select-String "Status:" | Out-String).Trim(); if ($s -match "Running") { "ALL GOOD" } else { "SOMETHING IS OFF: $s" }
```

Send me what 4a, 4b and 4c printed.
