# Phase 409 — the operator's steps, in order

Each `.txt` here is one paste block, `bash <<'EOF409x'` … `EOF409x`, ending
ALL GOOD or SOMETHING IS OFF. The advisor tests each before the operator
runs it. The handoff carries them inline, in this order.

| step | where | file | changes |
|---|---|---|---|
| 1 | the home desktop, Ubuntu | `1_desktop_measured.txt` | nothing: Step 0's owed measurement; its output goes in the phase log |
| — | the operator merges the server's pull request (after the app's); nothing else merges to master until step 2 has run, because `server-update` refuses unless master is exactly that merge | — | master |
| 2 | the Mac, Terminal | `2_backup_and_server_update.txt` | a copy of live (`remote.py backup pre409`), then the server and the feed onto the merge (`remote.py server-update`) |
| 3a | the Mac, Terminal | `3a_site_upload_file.txt` | writes `~/Downloads/getmekno-site-409.zip` from master |
| 3b | a browser, Cloudflare | below | the site: privacy policy 1.2 live |
| 3c | the Mac, Terminal | `3c_site_check.txt` | nothing: the live pages are master's |
| 4 | the home desktop, Ubuntu | `4_server_settings.txt` | `server.env` (copied first to `server.env.pre409`), the server restarted; put back by itself if this machine or the tailnet name stops answering, or if the help pages or a stranger's host name still answer |
| 5 | a browser, Cloudflare | below | the tunnel `mekno-api` and its public hostname |
| 6 | the home desktop, Ubuntu | `6_tunnel_installed.txt` | the tunnel program and its service; refuses unless the privacy page is live, the new code runs and the settings are in |
| 7 | the Mac, Terminal, then the phone | `7_outside_check.txt` | nothing |
| undo | the home desktop, Ubuntu | `8_undo.txt` | the tunnel removed, `server.env.pre409` put back, the server restarted |

The order holds the operator's conditions: the shop route is closed (the
new code, step 2) and the privacy line is live (step 3) before the tunnel
(step 6); the help pages are off and the server answers only to its own
names (step 4) before anything is public.

## Step 3b, in the browser (no block)

On the operator's own Cloudflare login. If a screen looks different, stop
and say so in the project thread.
1. The Cloudflare dashboard, **Workers & Pages**, the project **getmekno**.
2. **Create deployment**, left on **Production**.
3. Drag `getmekno-site-409.zip` from Downloads into the upload box, then
   **Save and Deploy**.

The way back: the project's **Deployments** list, the previous
deployment's menu, **Rollback**.

## Step 5, in the browser (no block)

1. https://one.dash.cloudflare.com, then **Networks**, **Tunnels**,
   **Create a tunnel**.
2. **Cloudflared**. Name it `mekno-api`. Save.
3. Under the install commands, choose **Debian**, **64-bit**. The command
   shown ends in a long token after `service install`. Copy **only that
   long token**. It goes into step 6's prompt, never into a chat.
4. **Next**. Add a public hostname: subdomain `api`, domain `getmekno.com`,
   type **HTTP**, URL `127.0.0.1:8000` (`127.0.0.1`, not `localhost`).
   Save.

## Step 7, on the phone

Wi-Fi off (mobile data only), Safari, `https://api.getmekno.com/healthz`:
it shows `"status":"ok"`. Then `https://api.getmekno.com/docs`: it says
`Not Found`. Wi-Fi back on.

## How the blocks were tested

- `bash -n` and `shellcheck -s bash -S warning` on each block's body: clean.
- `standin/`: each block run in a scratch home with stand-in commands
  (`systemctl`, `ss`, `tailscale`, `curl` as a small simulated server that
  honours the settings file, `sudo`, `cloudflared`, `gh`, `nc`, and the
  Mac's `remote.py`), each condition broken on purpose. `cases.py`: 30 of
  30; `cases3.py` (the site blocks against a local copy of this branch as
  master, and the token never echoed): 6 of 6. Run with
  `python3 standin/cases.py` and `python3 standin/cases3.py` from this
  folder, with the repository's `.venv` built.
- Not run anywhere real: they read the desktop's services, Tailscale,
  GitHub and Cloudflare, which the cloud cannot reach. The first real run
  is step 1, which changes nothing.
