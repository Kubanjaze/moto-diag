# Stripe for 371: how news of a payment reaches the server

Written 2026-11-05 by the advisor session, as the options page for the
fork on row 371. **Decided the same day: option A with the three
additions below (K65).** Kept here so nobody has to work this out again.

## The question

When a customer pays, Stripe has to tell the server so the invoice gets
marked paid. Stripe normally does that by calling the server over the
internet, which is called a webhook. This server can't be called from the
internet. It sits on the private tailnet, by the operator's decision of
2026-09-28. So the news needs another way in.

Taking the money isn't affected. Customers pay on Stripe's own page or on
the card reader either way. This decision is only about how the server
finds out.

## The options

- **A. The server asks Stripe.** Every 20 seconds or so, the server asks
  Stripe what's new. The desktop only calls out.
- **B. An Amazon queue.** Stripe sends to an Amazon queue, and the desktop
  collects from it.
- **C. A small cloud relay of our own.** Stripe sends to a relay that
  accepts only signed messages, and the desktop collects from it.
- **D. Tailscale Funnel on one separate port.** Stripe calls a public
  Tailscale address, which comes in to the desktop.
- **E. Cloudflare Tunnel, Stripe's addresses only.** Stripe calls a public
  Cloudflare address, which comes in to the desktop.

D and E are the only ones where a request from the internet reaches the
desktop.

| | A. Server asks | B. Amazon queue | C. Cloud relay | D. Funnel | E. Cloudflare |
|---|---|---|---|---|---|
| The tailnet rule | Stands | Stands | Stands | Needs an exception | Needs an exception |
| New accounts | None | Amazon | A cloud host | None | Cloudflare, and a domain |
| New secrets to look after | None | An Amazon key on the desktop | Stripe's signing secret on the relay, and a key to collect | Stripe's signing secret | Stripe's signing secret, and a tunnel credential |
| Invoice shows paid in | Up to about 20 seconds | Seconds | Seconds | Seconds | Seconds |
| If the desktop is off | Catches up, for up to 30 days | Queue holds it for up to 14 days | Relay holds it, as long as it's built to | Stripe retries for up to 3 days | Stripe retries for up to 3 days |
| Disk dies, restored from last night's backup | Heals itself | That day's news lost, without extra setup | Lost unless resent by hand | Lost unless resent by hand | Lost unless resent by hand |
| Server moves off the desktop | Nothing to do | Give the new server the key | Give the new server the key | Has to be replaced | Reinstall the tunnel |
| Around 100 shops | Time to add a push route | No change | No change | No change here | No change here |
| New company seeing payment details | None | Amazon | The cloud host | None | Cloudflare |
| Size of the build | Small: one job, and an alarm if it stops | Small to medium | Medium: a second program outside the repository's tests | Smallest: limits on one route first | Small, with more setup |
| The operator's own work | None beyond Stripe | Amazon account and console setup | Cloud account and deployments | A tailnet policy change and one command | A domain, a new service on the desktop, and Stripe's 15 addresses kept current |

Not on the list: `stripe listen`, the test tool, which is meant for
development and doesn't retry; and putting the whole server on the
internet, which is a far bigger change than this needs.

## Why A lasts longest

Every route that pushes news (B to E) can lose some: Stripe stops retrying
after 3 days, and once a message has been accepted it isn't sent again.
Stripe's own pages point to the events list for recovering what was
missed. So any setup built to last needs A's job running, however the news
normally arrives. B to E are things to add on top of it later. Both can run
at once, because the server ignores repeats.

The hardest test is a restore. Say the desktop's disk dies at 4 pm and
that morning's 3 am backup is restored. Stripe counts every payment since
3 am as delivered, so a push route never sends it again. Those invoices
stay unpaid in the records, with nothing to warn anyone. With A, the
server's place in the news is restored with the database, so it asks again
from 3 am and the day comes back by itself. That only holds if the place
is stored in the database.

What ends A as the main feed is shop count, at around 100 shops. The
server has probably left the home desktop before then. At that point the
webhook route that's already built gets switched on, and A stays on as the
safety net. Nothing gets thrown away.

## The three additions

The operator, on the options: "i just want to be notified when its time to
upgrade, i dont want it to break and i have to refigure this out all over
again". So A ships with three things.

1. **If it stops, an email.** Every 5 minutes the job tells Sentry it's
   still running. If Sentry hears nothing for about 15 minutes, it emails
   the operator. The watcher sits outside the desktop, so it also catches
   the desktop being off or the internet being down. It uses Sentry's one
   free job monitor, through the address the DSN already gives, so there's
   no new account. The operator turns on the email rule once.
2. **Before it gets close, a warning.** Once a day the job checks how near
   it is to its limits and sends one notice when it crosses a line: 50
   connected shops (start planning), 100 connected shops (time to upgrade),
   news running more than 2 minutes late, or Stripe refusing asks. Stripe's
   ceiling would be around 500 shops, so the first warning leaves plenty of
   room. The numbers are the operator's to change.
3. **The upgrade is already written down.** The steps go in the guide while
   371 is built, and the warning names the page. A paused phase goes into
   the ledger with its prompt ready, so the operator says go and the fleet
   builds it.

The alarm is tested on purpose before the phase closes: the job is stopped,
and the operator watches the email arrive. A change at Stripe won't set off
the early warning, though the alarm goes off if it stops the job.

## What A gives up

- **A short wait at the counter.** The card reader says approved straight
  away. The invoice in the app catches up within about 20 seconds. The
  interval is one setting and can be shortened.
- **The usual route.** Stripe's pages present the events list as the way to
  recover missed news, and webhooks as the main feed. That's the advisor's
  reading. No rule was found against using the list as the main feed.
- **Simple growth.** Each round asks once for the platform's own account
  and once for each connected shop. 100 shops would be 5 asks a second,
  against Stripe's usual limit of 25 a second for one endpoint.
- **Silence on failure.** If the job stops, no news arrives and nothing
  complains. That is what the first addition is for.
- **A fixed message format.** Each event comes in the format Stripe used
  when it happened, and the list can't pin a format the way a webhook
  endpoint can. The server already re-reads subscriptions from Stripe
  rather than trusting the message. Payments would need to do the same.
- **A possible change at Stripe.** Stripe has a newer style of event for
  its newest products, with its own list. Payment news doesn't use it
  today. If it moved there, the job would need a second ask.

## Why not D, the easy one

D is the least code, and it would be the first time the internet could
reach the machine that holds the live database. The route it exposes has
no rate limit and no size limit today, because it was only ever reachable
from the tailnet. Funnel makes a whole port public, so it would need its
own port (8443 or 10000) and a size limit first. It can't filter who
connects, and Tailscale still calls it beta. E fixes the filtering, at the
cost of a new company, a domain and a list to keep current.

## What would change this

- If about 20 seconds turns out to be a real problem at the counter, B
  gives seconds with still no door. It costs an Amazon account and a key on
  the desktop.
- When customers themselves need to reach the server, for self-booking or
  share links, the question of a public door comes back for all of those at
  once.

## Whichever option: still open

- **A public thank-you page.** After paying online or finishing Stripe's
  shop sign-up, the person's browser is sent to an address of ours. In live
  mode Stripe requires HTTPS, and customers aren't on the tailnet, so a
  tailnet address won't open for them. All five of these settings point at
  `localhost:3000` today. One plain public page that holds no data solves
  it, on a free static host or the business's own website.
- **The live switch has side effects.** Live keys only work with
  `MOTODIAG_ENV=prod`. In that mode the server won't start unless billing is
  real Stripe and `MOTODIAG_PUBLIC_BASE_URL` is set. That address goes into
  the share links sent to customers. A tailnet address passes the check, and
  customers still couldn't open those links. So while the server stays on
  the tailnet, share links don't reach customers.
- **The operator's Stripe work.** The live account (business details, bank
  account, identity check), Connect switched on for live, and real tier
  prices, since today's are placeholders.

## What wasn't confirmed

- Stripe's pages don't say outright whether a shop's events need their own
  ask, or whether those events name the shop's account. They point to
  asking each account separately, and the server can add the name itself.
  The build's first step tests this on the test account.
- Tailscale's pages say a Funnel port is "completely public", and don't
  spell out what happens to paths already served on it.
- The 20 seconds is a suggestion, not a measurement. The 14 days for
  Amazon's queue comes from the advisor's own knowledge. Sentry's one free
  monitor comes from its help pages, and the build confirms it on the
  operator's account.

## Sources

- Stripe: [list events, going back up to 30 days](https://docs.stripe.com/api/events/list)
- Stripe: [how events work, retries, and asking each account](https://docs.stripe.com/event-destinations)
- Stripe: [sending events to Amazon EventBridge](https://docs.stripe.com/event-destinations/eventbridge)
- Stripe: [the addresses webhooks come from](https://docs.stripe.com/ips)
- Stripe: [HTTPS return addresses in live mode](https://docs.stripe.com/connect/oauth)
- Stripe: [rate limits](https://docs.stripe.com/rate-limits)
- Stripe: [the newer style of event](https://docs.stripe.com/api-v2-overview)
- Sentry: [job monitors without an SDK](https://docs.sentry.io/product/crons/getting-started/http/)
- Tailscale: [Funnel](https://tailscale.com/kb/1223/funnel)
