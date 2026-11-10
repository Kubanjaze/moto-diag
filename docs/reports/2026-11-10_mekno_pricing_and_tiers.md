# Mekno pricing and what each plan gets

Written 2026-11-10 by a research thread, at the operator's request ("from
here we need to do market research", and: "its all about how much vehicles
you can have in your garage, thats like whats unclear, whats different with
the price tiers"). The live Stripe prices are on hold until this is read.

Research only. Nothing in Stripe, `server.env` or the code was changed.

## The short answer

**Keep the three prices: $19, $99 and $299 a month. Create them in Stripe
as monthly prices only, with no yearly prices for now.**

**But fix what the plans include before the first shop pays.** The prices
are fine. The limits behind them have three problems, and the biggest is
the vehicle limit on the Shop plan.

| Plan | Price | Who it is for | Bikes | People | Locations | Diagnoses a month |
|---|---|---|---|---|---|---|
| **Individual** | $19/mo | A rider working on their own bikes at home | 5 bikes in your garage | 1 | 1 | 50 |
| **Shop** | $99/mo | One repair shop | **No limit** on customer bikes | Up to 10 | 1 | 500 |
| **Company** | $299/mo | A business with a few shops | No limit | No limit | **Up to 3** | No limit |

What else separates them, unchanged from today's code:

- **Individual:** AI diagnosis on the faster, cheaper model; no PDF
  reports, no sharing with customers, no video or voice-note uploads.
- **Shop:** adds the stronger AI model, PDF reports, sharing reports with
  customers, your shop's name on reports, work orders and the team, and up
  to 200 video and 200 voice-note uploads a month.
- **Company:** everything in Shop, plus API access, priority support, and
  no upload limits.

The three bolded cells are the changes. Each is explained below.

## What the app enforces today

Checked in the code on master (`94e713d`), not taken from older notes:

| Limit | Individual | Shop | Company | Where |
|---|---|---|---|---|
| Vehicles | 5 | 50 | unlimited | `src/motodiag/vehicles/registry.py` `TIER_VEHICLE_LIMITS` |
| Diagnoses a month | 50 | 500 | unlimited | `src/motodiag/core/session_repo.py` |
| Video uploads a month | 0 | 200 | unlimited | `src/motodiag/api/routes/videos.py` |
| Voice-note transcripts a month | 0 | 200 | unlimited | `src/motodiag/api/routes/transcripts.py` |
| Users | 1 | 10 | unlimited | `src/motodiag/cli/subscription.py` `TIER_LIMITS` |
| Locations | 1 | 1 | unlimited | same |
| AI spend cap a month | $5 | $50 | $500 | same |
| Name shown in the app | "Solo Mechanic" | "Shop (per location)" | "Multi-Location / Enterprise" | same |

How the vehicle limit works: the server counts every vehicle saved under
your account (`count_vehicles_for_owner`). When the count reaches your
plan's limit, adding one more is refused with an "upgrade" message.
Deleting a vehicle frees a slot.

## The three problems

### 1. The Shop plan runs out of bikes in a few weeks

This is the one that matters. In the code, a vehicle is a vehicle: a shop's
customer bikes are counted the same way as a home rider's own bikes. A
small shop sees well over 50 different bikes a year, often in the first
month of spring. At 50, the shop is told to upgrade or start deleting
customer history, which is the record it is paying to keep.

No shop software we looked at limits vehicles or repair orders. Tekmetric
says "Unlimited Users, Unlimited RO's" on every plan, and AutoLeap says
"Unlimited Repair Orders & Invoices" on every plan. What they charge more
for is features, people and extra locations.

**Fix:** the Shop plan has no bike limit. What it limits instead is people
(10), locations (1) and diagnoses a month (500). The diagnosis limit is
what actually protects the AI bill, so the bike limit adds no protection.

### 2. The Company plan can cost more than it brings in

Company is $299 a month, but its AI spend cap is $500 a month and it allows
unlimited locations. A busy customer with several shops could cost more in
AI than they pay, before Stripe's fee. The other two plans don't have this
problem: Individual's cap is $5 on $19, Shop's is $50 on $99.

The big auto shop tools charge per location. Tekmetric adds $70 a month for
each extra shop, and each location needs its own plan.

**Fix:** Company covers up to 3 locations, and its AI cap comes down to
$150 a month. A business with more than 3 shops is a conversation, not a
checkout button. Three Shop plans cost $297, so Company at $299 is fair for
three shops with unlimited diagnoses, API access and priority support.

### 3. The Individual plan is labelled for a mechanic, not a home garage

The app calls the $19 plan "Solo Mechanic" and describes it as "single
mechanic, personal use". The plan is meant for someone working on their
own bikes at home. A mobile mechanic working on other people's bikes should
be on Shop, and the 5-bike limit already steers them there.

**Fix:** show it as "Individual: for your own bikes" in the app and on the
website. Five bikes stays. It covers nearly every rider: the home-garage
apps that sell a 5-vehicle plan (Drivvo, AUTOsist) chose the same number.

## Why the prices themselves are right

**$19 for Individual.** Home riders already pay for tools like this:

- Drivvo, a vehicle log app: free for 2 vehicles; $24.90 a year for 5;
  $49.90 a year for 10.
- Older log apps (Fuelly, aCar, AUTOsist): $5 to $50 a year. These only
  record what you did. They don't tell you what's wrong.
- Repair manuals: ALLDATA DIY and Mitchell 1 DIY (AutoUpkeep) are both
  $19.99 for one month, or $40 to $60 for a year, for one vehicle. Cyclepedia
  motorcycle manuals are sold one bike at a time.
- Motorcycle diagnostic hardware: the HealTech OBD Tool is about $230, one
  time, with PC software.

Mekno at $19 a month sits at the price of a month of a repair manual, and
does more than a manual: it diagnoses. It is well above the log apps, and
it should be, because they don't diagnose. The risk at $19 is that home
riders use it for one problem and cancel. Monthly billing makes that easy,
and that is acceptable at launch. It shows whether people come back.

**$99 for Shop.** Shop software for car repair shops costs two to five
times as much:

| Product | Cheapest plan | Top plan | Notes |
|---|---|---|---|
| Tekmetric | $199/mo | $439/mo | unlimited users and repair orders; +$70/mo per extra shop |
| AutoLeap | $199/mo | $449/mo | unlimited repair orders |
| Shopmonkey | $239/mo | $499/mo | multi-shop by quote |
| Shop-Ware | $279/mo | $999/mo | figures from a price-comparison site |
| RepairShopr | $70/mo | $150/mo | general repair shops; figures from a price-comparison site |

Motorcycle and small-shop tools are cheaper, starting around $30 to $75 a
month (ARI $39.99, Digital Wrench $39.95, MaxxTraxx $59 per user, RepairQ
$75), going by the starting prices the vendors list on SourceForge.

Mekno is not trying to be a full Tekmetric. It is a diagnostic tool with
shop features added. $99 puts it above the basic motorcycle shop tools,
because it diagnoses, and at half the price of the car-shop systems, which
it doesn't try to replace. A shop that bills $85 to $125 an hour (the
labour rates in `docs/phases/completed/_research/track_g_pricing_brief.md`)
covers $99 if Mekno saves one hour of diagnosis a month.

**$299 for Company.** With the 3-location limit above, it is the same price
as three Shop plans, with no limits on top. That is simple to explain and
it can't lose money.

## Yearly prices

The code has yearly prices at ten times the monthly price ($190, $990,
$2,990: two months free). **Don't create them in Stripe yet.** Monthly-only
keeps the first months simple: no refunds on a year someone stops using
after two weeks, and the cancel numbers tell you whether the prices are
right. Add yearly prices once the first customers have stayed three months.
They can be added in Stripe at any time without touching the monthly ones.

## What happens next

1. **Stripe, now:** create three monthly prices, $19, $99 and $299. The
   prices don't depend on the fixes below. The limits live in the app, not
   in Stripe.
2. **A small code phase, before the first shop pays:** take away the Shop
   plan's bike limit, put Company at 3 locations and a $150 AI cap, and
   rename the Individual plan in the app. This is a change to the code and
   its tests, so it goes through the fleet like any phase. It is not done
   here.
3. **Website:** the plan names and the table above go on getmekno.com's
   pricing section when the app is out of "coming soon".

## Where the figures came from

Read on 2026-11-10. Prices change; check the vendor's own page before
quoting one to a customer.

- Tekmetric: https://tekmetric.com/pricing
- AutoLeap: https://autoleap.com/?p=101187
- Shopmonkey (Capterra's listing): https://www.capterra.com/p/169022/Shopmonkey/pricing/
- Shop-Ware (CostBench, a comparison site; marked unverified since
  2026-06-14): https://costbench.com/software/automotive-shop-software/shop-ware/
- RepairShopr (CostBench): https://costbench.com/software/automotive-shop-software/repairshopr/
- Motorcycle and small-shop starting prices (SourceForge, vendor-entered):
  https://www.sourceforge.net/software/motorcycle-repair-shop
- Drivvo: https://www.drivvo.com/en/pricing/ and https://drivvo.com/en/personal-use/
- Older log apps (a 2023 round-up, so possibly out of date):
  https://www.vikingbags.com/blog/6-best-motorcycle-maintenance-apps/
- ALLDATA DIY: https://www.alldata.com/diy-us/en
- Mitchell 1 DIY (AutoUpkeep): https://autoupkeep.com/online-manuals
- Cyclepedia: https://cyclepedia.com/?p=42
- HealTech OBD Tool: https://www.healtech-electronics.com/products/obd/

Not found: a current price for FIXD Premium (its page refused the request)
and for Cyclepedia (no price on its current pages).
