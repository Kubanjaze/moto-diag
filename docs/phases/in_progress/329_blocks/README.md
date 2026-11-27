# Phase 329 — the operator's steps, in order

Each `.txt` here is one paste block, `bash <<'EOF329x'` … `EOF329x`, ending
ALL GOOD or SOMETHING IS OFF. The advisor tests each before the operator
runs it. The handoff carries them inline, in this order. The steps with no
block are below the table.

| step | where | file | changes |
|---|---|---|---|
| 1 | a browser, Resend and Cloudflare | below | a Resend account, the domain getmekno.com, its three records in Cloudflare's DNS, an API key (kept for step 4 only) |
| 1b | the Mac, Terminal | `1_dns_check.txt` | nothing: Resend's records are in DNS and support@ mail still reaches Gmail |
| 2a | the Mac, Terminal (the advisor) | `2a_migration_dry_run.txt` | nothing on live: the dry run of migration 093 on a copy, its list fetched, for the advisor to commit on the branch and show the operator |
| 2b | the Mac, Terminal (the advisor) | `2b_migration_apply.txt` | live: two new empty tables. Only after the operator's yes on the list and after the regression of record, before the close-out commit (K18) |
| — | the operator merges the pull request | — | master |
| 3 | the Mac, Terminal | `3_backup_and_server_update.txt` | a copy of live (`pre329`), then the server and the payments feed onto the merge |
| 4 | the home desktop, Ubuntu | `4_server_settings.txt` | `server.env` (copied first to `server.env.pre329`): Resend and its key (typed, never shown), the Individual sign-up and the reset by email on, the shops' sign-up off; both services restarted; put back by itself if anything does not answer as it should |
| 5a | the Mac, Terminal | `5a_site_upload_file.txt` | writes `~/Downloads/getmekno-site-329.zip` from master |
| 5b | a browser, Cloudflare | below | the site: privacy 1.3 and the sign-up and reset pages live |
| 5c | the Mac, Terminal | `5c_site_check.txt` | nothing: the live pages are master's, only the two form pages may post, the public sign-up answers |
| 6 | the phone, off Wi-Fi | below | one real Individual sign-up, paid with a real card |
| 6b | the home desktop, Ubuntu | `6b_signup_check.txt` | nothing: the newest sign-up went all the way through |
| 6c | the Mac, Terminal | `6c_sign_in_check.txt` | a sign-in and sign-out at the public address with the new account |
| 6d | a browser, Stripe | below | the $19 refunded and the subscription cancelled, by hand |
| undo | the home desktop, Ubuntu | `7_undo.txt` | `server.env.pre329` put back, both services restarted, sign-up and the reset off; then the site's rollback in Cloudflare |

The order holds the operator's conditions: Resend's records are in before
any email can leave (step 1), the server has the tables (2b) and the code
(3) before its switches go on (4), and the switches are on before the site
publishes forms that post to them (5b), so no published form answers 404.
The privacy policy naming Resend goes live in 5b, before anyone can use
the form.

## Step 1, in the browser (no block)

On the operator's own logins. If a screen looks different, stop and say so
in the project thread.
1. https://resend.com, **Sign up** (use support@getmekno.com or your own
   address; either is fine).
2. **Domains**, **Add domain**: `getmekno.com`, region **North Virginia
   (us-east-1)**. Resend shows three records: an **MX** and a **TXT** for
   `send`, and a **TXT** for `resend._domainkey`.
3. Add them in Cloudflare: Resend offers **Sign in to Cloudflare** to add
   them for you; take it. If you add them by hand instead: Cloudflare
   dashboard, getmekno.com, **DNS**, **Records**, **Add record**, each one
   exactly as Resend shows it, **Proxy status: DNS only** (the grey cloud).
   Do not touch the existing `MX` records for `getmekno.com` itself: they
   carry support@getmekno.com to Gmail.
4. Run step 1b on the Mac. Then in Resend press **Verify** until the domain
   says **Verified** (minutes, sometimes longer).
5. **API Keys**, **Create API key**: name `mekno-server`, permission
   **Sending access**, domain `getmekno.com`. Copy the key. It goes only
   into step 4's prompt on the home desktop, never into a chat, a note or
   an email. If it is lost, delete it in Resend and make a new one.

## Step 5b, in the browser (no block)

1. The Cloudflare dashboard, **Workers & Pages**, the project **getmekno**.
2. **Create deployment**, left on **Production**.
3. Drag `getmekno-site-329.zip` from Downloads into the upload box, then
   **Save and Deploy**.

The way back: the project's **Deployments** list, the previous
deployment's menu, **Rollback**.

## Step 6, on the phone

Wi-Fi off (mobile data only), Safari.
1. `https://getmekno.com`, **Prices**, **Start your own account**.
2. Fill the form with an email address you can read on the phone, a new
   username and a password; tick the box; **Continue**. The page says to
   check your email.
3. Open the email "Confirm your email for Mekno" and its link; press
   **Confirm and go to payment**.
4. Stripe's page asks for $19 a month. Pay with a real card. Stripe sends
   you back to "You're all set".
5. Within a minute, "Your Mekno account is ready" arrives.
6. Run 6b on the home desktop and 6c on the Mac.

## Step 6d, in the browser (no block)

The Stripe dashboard, live mode.
1. **Payments**, the $19.00 payment, **Refund**, the full amount.
2. **Customers**, the new customer, its subscription, **Cancel
   subscription**, **Immediately**.

The account stays, with its plan cancelled.

## How the blocks were tested

- `bash -n` on each block's body: clean.
- `standin/cases.py`: blocks 4, 7 and 6b against this branch's real server
  code, served by uvicorn on 127.0.0.1:8000 from a scratch database in a
  scratch home, with `sudo` and `systemctl` as stand-ins that restart it on
  the settings file; each refusal broken on purpose (a key that is not
  Resend's, a key with odd characters, no Individual price, the database
  not at 93, code without the sign-up, the payments feed not coming back).
  15 of 15. Run with
  `.venv/bin/python docs/phases/in_progress/329_blocks/standin/cases.py`
  from the repository root.
- The migration's scope (`../329_deploy_scope.json`) was checked by
  `deploy.py dryrun 329` against a scratch database built at master's
  schema 92: scope problems none, census 0, two tables and three indexes
  added. The scratch diff was deleted; the record is the advisor's dry run
  on live (2a).
- Not run anywhere real: 1b, 2a, 2b, 3, 5a, 5c and 6c read DNS, the
  desktop, GitHub or Cloudflare, which the cloud cannot reach.
