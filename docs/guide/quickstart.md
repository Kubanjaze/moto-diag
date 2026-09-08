# Quickstart — diagnose a bike

About ten minutes, from a fresh install to a saved diagnosis. Everything
here except the final AI step runs offline against local SQLite.

Assumes you've installed per the [README](../../README.md):

```bash
source .venv/bin/activate
motodiag db init
```

## 1. Look up a fault code

If you already have a code off a scanner, start there:

```bash
motodiag code P0115
```

```
╭─────────────────────────────── DTC P0115 ────────────────────────────────╮
│ P0115 — Engine Coolant Temperature Circuit Malfunction                   │
│                                                                          │
│ Category: cooling                                                        │
│ Severity: MEDIUM                                                         │
│ Make: Generic (all makes)                                                │
╰──────────────────────────────────────────────────────────────────────────╯

Common causes:
  1. Faulty coolant temp sensor
  2. Wiring issue in coolant temp circuit
  3. Corroded connector

Fix: Check sensor connector, test sensor resistance vs temp chart, replace
if out of spec.
```

"Generic (all makes)" means this is the standard OBD-II definition. When
MotoDiag has a make-specific entry it uses that instead, because a code
means something narrower on a Harley than it does in general.

## 2. Search when you don't have a code

Most jobs start with a description, not a code:

```bash
motodiag search "overheating"
```

```
Search results for 'overheating' (33 total)

Symptoms (1)
  Overheating — Engine temperature rises above normal, may trigger warning
light
```

`search` spans DTCs, symptoms and known issues at once. To stay inside
the curated known-issue database:

```bash
motodiag kb search "cam chain"
motodiag kb list --make honda
motodiag kb by-code P0562
```

The knowledge base is 824 curated entries — real failures on real
bikes, with the fix. `motodiag kb show <id>` prints the full detail.

## 3. Add the bike

```bash
motodiag garage add --make Honda --model CBR600F4i --year 2003
```

```
Added vehicle #1: 2003 Honda CBR600F4i
```

```bash
motodiag garage list
```

```
                         Your Garage
┏━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━┓
┃ ID ┃ Year ┃ Make  ┃ Model     ┃ Engine ┃ Powertrain ┃ VIN ┃
┡━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━┩
│  1 │ 2003 │ Honda │ CBR600F4i │ -      │ ice        │ -   │
└────┴──────┴───────┴───────────┴────────┴────────────┴─────┘
```

Adding the bike is worth the fifteen seconds: it scopes every later
lookup to that make and model, and it's what service history, wear
prediction and recall checks hang off.

Got a photo instead of a spec? `motodiag garage add-from-photo` will
identify it.

## 4. Read the bike, if you have an adapter

```bash
motodiag hardware scan          # stored DTCs, enriched with the KB
motodiag hardware info          # protocol, VIN, ECU part + software version
motodiag hardware stream        # live Mode 01 PIDs
motodiag hardware dashboard     # live TUI
```

No adapter yet? `motodiag hardware compat recommend --make Honda --model CBR600F4i`
ranks adapters known to work with that bike, and
`motodiag hardware simulate run` exercises the whole path without
hardware. Skip to step 5 — nothing below needs an ECU.

## 5. Run the diagnosis

Two modes. One-shot:

```bash
motodiag quick "runs hot in traffic, temp light flickers"
```

Or interactive, where MotoDiag asks follow-up questions before
committing to an answer:

```bash
motodiag diagnose start
```

> **These two commands call the Anthropic API and cost money.**
> Everything above this point is local and free. Set `ANTHROPIC_API_KEY`
> first. Responses are cached, so repeating a question is free —
> `motodiag cache stats` shows what that has saved you, and
> `motodiag costs report` is the ledger.

## 6. Find it again

Sessions are saved:

```bash
motodiag diagnose list           # every session
motodiag diagnose show 1         # render one
motodiag diagnose annotate 1 "Replaced ECT sensor, cleared code"
motodiag diagnose reopen 1       # continue a closed session
```

Annotations are how a diagnosis becomes a record worth keeping. What you
found, what you did, what it turned out to be.

## Where next

- Running a shop — customers, work orders, parts, invoices, and a link
  you can send the customer: **[Shop workflow](shop-workflow.md)**
- Wiring this to something else, or running the iOS app:
  **[HTTP API](api.md)**
- `motodiag <group> --help` for any of the 24 command groups. There are
  255 commands; you will not need most of them on any given day.
