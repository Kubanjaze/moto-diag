# Payments: how the server hears that a customer has paid

When a customer pays a shop's invoice, by card at the reader or online
through the pay-link, Stripe takes the money. The server then has to be
told, so that the invoice shows as paid. This page says how that news
reaches the server, how to see that it is working, what the warnings mean,
and what to do when it is time to upgrade.

## How the news reaches the server

The server is reachable only over your private network (the tailnet), so
Stripe cannot call it. Instead, **the server asks Stripe**: about every 20
seconds a small job on the home desktop asks Stripe for anything new, for
your own account and for every shop that has connected its Stripe account.
Each piece of news goes through the same checks a webhook would. So an
invoice shows as paid within about half a minute of the reader saying
"approved".

The job is its own service on the home desktop,
`motodiag-payments.service`. It runs beside the API and starts by itself
when the desktop starts.

## From the app

A shop owner connects the shop to Stripe from the phone: the app asks the
server for a link, and Stripe's own page opens to take the shop's details.
The link works once and is for the owner only. Back in the app, the shop's
card payments show as ready once Stripe has finished checking.

A service writer (or the owner) then takes an invoice's payment from the
phone in one of two ways: **send it to the card reader**, or **share a
pay-link** the customer opens to pay online. Neither tap pays the invoice.
The invoice shows as paid only when Stripe's news arrives, through the job
above, so within about half a minute of the card being approved; the app
reads the payment's outcome, approved or declined with the reason, from the
server.

The server routes behind these screens are listed under "The routes" in
`docs/guide/api.md` (`payments`).

## The thank-you page

After a customer pays through Stripe Checkout, leaves the billing portal
or pays an invoice online, and after a shop owner finishes Connect
onboarding, Stripe sends them to a web page. That page is a plain
thank-you page on getmekno.com, the business's own site. It holds no data:
it says thank you, and nothing on it comes from the server. The server
names it in one setting, `MOTODIAG_STRIPE_RETURN_PAGE_URL`, which the six
return addresses all take unless one is set on its own. If the page ever
moves, that is the one setting to change.

## Seeing that it is running

On the home desktop, in the Ubuntu terminal:

```bash
motodiag payments feed status
```

It prints, for each account, when it was last asked and how long ago, the
time of the newest news, and the last error if there was one; then the
warnings sent in the last 30 days, and whether the alarm is on. It ends
with "Not right: …" lines when something is wrong. Its exit code is 0 when
every account was asked within the last two rounds with no error, 1 when
not, and 2 when Stripe is not set up on this machine.

To ask once by hand and see what came back:

```bash
motodiag payments feed run --once
```

And the service itself:

```bash
systemctl status motodiag-payments.service
```

## The alarm

Every 5 minutes the job tells Sentry "still here" (a check-in to a Sentry
"cron monitor" named `motodiag-payments-feed`). If Sentry hears nothing for
about 15 minutes, it marks the monitor missed and emails you. Silence is
the signal, so the email comes whether the job stopped, the desktop is off,
or the house's internet is down.

The monitor creates itself on the first check-in. The one thing you set up
by hand, once, is the email: in Sentry, on the monitor's page, turn on the
alert for a missed check-in to your address. With no Sentry DSN in
`server.env` the alarm is off, and `feed status` says so.

## The notices

Once a day (and when the job starts) it checks four limits and sends a
warning to Sentry when one is crossed. Each warning names this page. The
numbers are yours to change; they are settings in `server.env`.

- **50 shops are connected: time to start planning the upgrade.** Sent
  once. Nothing is wrong yet; read "When it is time to upgrade" below and
  decide the public address.
- **100 shops are connected: time to upgrade.** Sent once. Asking Stripe
  for every shop every 20 seconds is near what it is meant for; follow the
  steps below.
- **News of a payment ran more than 2 minutes late.** At most once a day.
  Look at `feed status`: an account with an error, or Stripe answering
  slowly. If it happens day after day, it is time to upgrade.
- **Stripe refused or rate-limited asks.** At most once a day. "Refused"
  usually means the key in `server.env` is wrong or was rolled; "rate
  limited" means Stripe asked the job to slow down, which it does by
  itself.

The job remembers the day's lateness and refusals only while it runs: a
restart starts the day's count again. The warnings already sent are kept
in the database, so a restart never sends one twice.

## After a restore from a backup

The job keeps its place in Stripe's news in the database. A backup carries
the place it had then, so after a restore the job asks Stripe again from
that older place and catches up on everything since. A payment it had
already applied is recognised and not applied twice. Stripe keeps 30 days
of news: a backup older than that leaves a gap, and `feed status` says so
in that account's last error.

## When it is time to upgrade

The upgrade is to let Stripe call the server (a webhook), with the job
kept running as a safety net. The steps:

1. **Decide the public address.** Stripe can only call an address the
   internet can reach, and today the server has none. This is your
   decision; it was left open when the job was chosen.
2. **Create the webhook endpoint in Stripe's dashboard**, at that address
   plus the server's Stripe webhook path (row 401's prompt names the
   route), at API version `2026-09-30.endive`,
   for these eight events, with "Connect" events turned on:
   `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `invoice.paid`,
   `invoice.payment_failed`, `payment_intent.succeeded`,
   `payment_intent.payment_failed`, `charge.refunded`.
3. **Put its signing secret in `server.env`** as
   `MOTODIAG_STRIPE_WEBHOOK_SECRET=`, by hand, never in a chat.
4. **Keep the payments job running.** News that arrives both ways is
   applied once.
5. **Tell the fleet to start ROADMAP row 401**, "Payments news by webhook,
   at 100 shops"; its prompt is written and waiting.
