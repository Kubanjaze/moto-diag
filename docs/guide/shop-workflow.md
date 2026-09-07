# Shop workflow — intake to invoice

One job, end to end: a bike arrives, you diagnose it, order a part, do
the work, bill it, and send the customer something they can read.

Every command below was run in this order against a fresh database, and
the output is what it printed.

## 0. Register the shop

Once, ever:

```bash
motodiag shop profile init --name "Bandit Hero Cycles" --city Austin --state TX
```

```
Registered shop id=1.
╭────────────────────────────── Shop Profile ──────────────────────────────╮
│ Bandit Hero Cycles  (id=1)                                               │
│ Address: Austin, TX                                                      │
╰──────────────────────────────────────────────────────────────────────────╯
```

Mechanics get added as members with roles — `owner`, `tech`,
`service_writer`, `apprentice` — which is what the permission checks
key on:

```bash
motodiag shop member add --shop 1 --user 2 --role tech
```

## 1. The customer

```bash
motodiag shop customer add --name "Marcus Webb" --phone "512-555-0188"
```

```
Added customer id=3.
╭──────────────────────────────── Customer ────────────────────────────────╮
│ Marcus Webb  (id=3)                                                      │
│ Phone: 512-555-0188                                                      │
╰──────────────────────────────────────────────────────────────────────────╯
```

> Customers belong to a shop. With one shop registered, the CLI fills
> that in for you; once there are two, `--shop-id` becomes required
> rather than guessed. A customer filed under the wrong business is
> worse than a command that stops and asks.

Link the bike they rode in on (add it to the garage first — see the
[quickstart](quickstart.md#3-add-the-bike)):

```bash
motodiag shop customer link-bike 3 --bike 1 --relationship owner
```

```
Linked bike id=1 to customer id=3 as 'owner'.
```

`previous_owner` and `interested` also exist, which matters when a bike
changes hands and you still want its history.

## 2. Intake

What the customer actually said, before anyone has looked at it:

```bash
motodiag shop intake create --customer 3 --bike 1 --mileage 31450 \
  --notes "Runs hot in traffic, temp light flickers"
```

```
│ Intake id=1  OPEN                                                        │
│ Shop:     Bandit Hero Cycles  (id=1)                                     │
│ Customer: Marcus Webb  (id=3)                                            │
│ Bike:     2003 Honda CBR600F4i  (id=1)                                   │
│ Intake at: 2026-09-07 18:21:41                                           │
│ Mileage:  31450                                                          │
│                                                                          │
│ Reported problems:                                                       │
│   Runs hot in traffic, temp light flickers                               │
```

Keep the customer's own words here. The diagnosis goes elsewhere; this
is the complaint, and it's what you'll want when the same bike comes
back in four months.

`motodiag shop intake list` is your open queue.

## 3. Work order

The intake carries shop, customer and bike across, so you don't retype
them:

```bash
motodiag shop work-order create --intake 1 \
  --title "Cooling system diagnosis" \
  --description "Temp light flickers under load; suspect ECT sensor or fan circuit" \
  --priority 2 --estimated-hours 1.5
```

```
Created work order id=1.
╭─────────────────────────────── Work Order ───────────────────────────────╮
│ WO id=1: Cooling system diagnosis  DRAFT  P2                             │
│ Shop:     Bandit Hero Cycles  (id=1)                                     │
│ Customer: Marcus Webb  (id=3)                                            │
│ Bike:     2003 Honda CBR600F4i  (id=1)                                   │
│ Intake:   id=1                                                           │
│ Est hrs:  1.5                                                            │
╰──────────────────────────────────────────────────────────────────────────╯
```

Work orders move `draft → open → in_progress → completed`, with
`on_hold` and `cancelled` off to the side:

```bash
motodiag shop work-order start 1        # → in_progress
motodiag shop work-order pause 1        # → on_hold
motodiag shop work-order assign 1 --mechanic 2
```

Priority 1–5 feeds the triage queue: `motodiag shop triage queue` ranks
every open job, `triage next` gives you the single top one, and
`triage flag-urgent` forces something to the front when a customer is
standing at the counter.

## 4. Parts

Find the part:

```bash
motodiag advanced parts search "coolant"
```

```
                        Parts matching 'coolant' (1)
┏━━━━━━━━━━━━━┳━━━━━━━┳━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ OEM#        ┃ Brand ┃  ┃ Category     ┃ Make/Model   ┃   Cost ┃ Verified ┃
┡━━━━━━━━━━━━━╇━━━━━━━╇━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ 11537726068 │ BMW   │  │ coolant-hose │ bmw / R1200% │ $59.99 │ manual   │
└─────────────┴───────┴──┴──────────────┴──────────────┴────────┴──────────┘
```

Empty results mean no match, not a broken catalogue — run
`motodiag advanced parts seed --yes` once if you've never populated it.
`motodiag advanced parts xref <oem#>` ranks aftermarket alternatives.

Add it to the job:

```bash
motodiag shop parts-needs add 1 -p 4 -q 1
```

```
Added work_order_part id=1 (wo=1, part=4, qty=1).
```

Then walk it through its states as it actually arrives:

```bash
motodiag shop parts-needs mark-ordered 1
motodiag shop parts-needs mark-received 1
```

> **This matters for billing.** An invoice bills only parts marked
> `received` or `installed` — you don't charge a customer for something
> still on a truck. A part left at `open` silently will not appear on
> the invoice, and the total will look right while being wrong. If a
> part is missing from an invoice, this is why.

Waiting on several jobs at once?
`motodiag shop parts-needs consolidate --shop 1` aggregates every open
line into one shopping list across work orders, and
`parts-needs requisition create` freezes that into a record.

## 5. Do the work

Log labour as it happens, from the CLI or the iOS app:

```bash
motodiag shop work-order complete 1 --actual-hours 1.75
```

```
Completed work order id=1.
```

Other things that hang off a work order while it's open: photos
(`/v1/shop/{shop_id}/work-orders/{wo_id}/photos`), voice notes that get
transcribed, per-issue tracking (`motodiag shop issue add`), and AI
labour estimates (`motodiag shop labor estimate`) you can later compare
against reality with `motodiag shop labor reconcile`.

## 6. Invoice

```bash
motodiag shop invoice generate 1 --tax-rate 0.0825 --hourly-rate 12500
```

```
Generated invoice id=2 (INV-1-1-20260907-R1).
╭──────────────────────────────── Invoice ─────────────────────────────────╮
│ Invoice INV-1-1-20260907-R1  SENT                                        │
│ ID:        2                                                             │
│ WO:        1                                                             │
│ Customer:  Marcus Webb (id=3)                                            │
│                                                                          │
│ Line items                                                               │
│   labor      qty=1.75 @ $125.00 → $218.75   Labor — 1.75h × $125.00/h    │
│   parts      qty=1 @ $15.99 → $15.99   Harley-Davidson Chrome oil        │
│ filter, Twin Cam 88/96/103/114 (OEM)                                     │
│                                                                          │
│ Subtotal:  $234.74                                                       │
│ Tax:       $19.37                                                        │
│ Total:     $254.11                                                       │
╰──────────────────────────────────────────────────────────────────────────╯
```

Rates are in **cents** — `--hourly-rate 12500` is $125.00/hr. Tax is a
fraction: `0.0825` is 8.25%. `--supplies-pct`, `--supplies-flat` and
`--diagnostic-fee` add the other lines shops actually charge.

Got it wrong? Void and regenerate — the number gets an `-R1` suffix so
the revision is visible rather than silently overwritten:

```bash
motodiag shop invoice void 1
motodiag shop invoice mark-paid 2
motodiag shop invoice revenue --shop 1
```

## 7. Send the customer something

The customer gets a link, not an account. Mint one against the
diagnostic session:

```bash
curl -X POST http://127.0.0.1:8000/v1/reports/session/1/share \
  -H "X-API-Key: $MOTODIAG_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"preset": "customer", "expires_in_days": 14}'
```

The returned URL opens a clean HTML page with no login — the capability
*is* the URL. It carries a 256-bit token, expires, and can be revoked:

```bash
curl -X DELETE http://127.0.0.1:8000/v1/reports/shares/1 \
  -H "X-API-Key: $MOTODIAG_API_KEY"
```

The `customer` preset hides internal notes and cost breakdowns;
`full` is everything. Pick deliberately — the preset is fixed server-side
when the link is minted, so whoever opens it cannot widen it.

PDFs, if they want one for their records:

```
GET /v1/reports/session/{session_id}/pdf
GET /v1/reports/invoice/{invoice_id}/pdf
```

> **Before sending links to real customers**, set
> `MOTODIAG_PUBLIC_BASE_URL` to a host the customer's phone can actually
> reach. Default is localhost, and a link to localhost works perfectly
> on your machine and nowhere else — you'd find out from the customer.

## The shape of it

```
customer ──┐
           ├── intake ── work order ── invoice ── share link
bike ──────┘                │
                            ├── parts (open → ordered → received)
                            ├── labour (estimated vs actual)
                            ├── issues, photos, voice notes
                            └── diagnostic sessions
```

## Seeing how the shop is doing

```bash
motodiag shop analytics snapshot --shop 1    # everything at once
motodiag shop analytics throughput --shop 1  # jobs closed per period
motodiag shop analytics turnaround --shop 1  # how long they take
motodiag shop analytics labor-accuracy --shop 1  # estimate vs actual
motodiag shop analytics top-issues --shop 1  # what keeps coming in
```

`labor-accuracy` is the one that pays for itself: it compares what you
quoted against what the job actually took, which is the difference
between a shop that makes money and one that's busy.

## From the app

The iOS app covers the shop-floor half of this — work orders, parts,
clock in and out, photos, voice notes — over the same HTTP API. See the
[API guide](api.md) and the mobile repo's README.
