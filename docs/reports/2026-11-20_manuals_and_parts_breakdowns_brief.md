# Manuals and parts breakdowns in Mekno: brief and phase proposal

Written 2026-11-20 by a research thread, at the operator's request: "I want
to steal this idea and implement it in our app to be able to go through
manuals and part breakdowns .. Super useful." The idea came from a social
video of a car repair manual app ("Mechanic IQ"): exploded brake diagrams
with torque values on each bolt (15 Nm, 250 Nm, "renew bolts/nuts"), a
belt-routing drawing, and the promise of "diagnostics & fault finding,
wiring diagrams, electrical schematics".

Research only. Nothing in the code, the database, Stripe or `server.env`
was changed. No legal advice: licensing is flagged, not decided.

## The short answer

**Build it, but build the viewer and the library first, not the content.**
The pictures in that video are licensed data from a publisher such as
HaynesPro or Autodata. Mekno cannot copy them, and no publisher sells
motorcycle content to embed in an app at a price we know yet.

**Recommended first slice: "Shop manual library".** A shop uploads the PDF
manuals and parts pages it already owns, tags them to a make, model and
year, and every phone in the shop can then open the right page for the bike
on the lift, search it, pinch-zoom the diagram, and keep it offline. That
needs no licence deal, and it is the screen every licensed source would
plug into later.

**In parallel, ask two publishers for a quote** (HaynesPro and Autodata,
both have motorcycle data) so the second slice can be real licensed
diagrams and torque tables.

## What already exists (Step 0 overlap audit)

Checked on master `b741ec1` and moto-diag-mobile `main`, not from notes.

| What | Where | State | For this feature |
|---|---|---|---|
| **Track P, Reference Data Library, rows 293 to 302** | `docs/ROADMAP.md` | All 🔲. 293 manual citations, 294 exploded parts diagrams, 297 per-model torque, 299 wiring, 302 Gate 17. Plan of record puts it in Wave 2. | **This feature is Track P.** Propose it as a reshape of 293 and 294, not a new track. |
| `manual_references` and `parts_diagrams` tables | migration in `src/motodiag/core/migrations.py` (phase 117) | Created, **empty**, CRUD in `src/motodiag/reference/` | Extension. `parts_diagrams.image_ref` and `source_manual_id` already fit. Needs columns for owner shop, file, page, and a page/text table. |
| `motodiag.reference` package | `src/motodiag/reference/` | Listed as "substrate, awaiting Track P" in `tests/support/integration_gaps_allowlist.py` | Wiring it to routes must also remove those allowlist entries (the gate fails if a listed module becomes reachable). |
| Generic torque, valve, interval, wiring data | `src/motodiag/engine/service_data.py`, `engine/wiring.py` (phases 92, 93); CLI `motodiag ref` (244V) | 20 torque specs, 5 circuits. Authored for the project, **not manufacturer data**, and every screen says so. | Keep as is. Not a substitute for per-model specs. No HTTP route yet. |
| Parts catalog and cart | `src/motodiag/api/routes/parts.py` (201), app `PartsBrowseScreen.tsx` | Part numbers, fitment by make/model/year, Shop tier | Extension later: a diagram's callout number can open a catalog part. No diagrams today. |
| Vehicles, VIN decode | `vehicles` table, `src/motodiag/advanced/nhtsa.py` (NHTSA vPIC) | Live | Reuse: the library filters by the bike's make, model, year. |
| File uploads and tier checks | `api/routes/photos.py`, `videos.py`, `require_tier("shop")` | Live | Reuse the upload, storage and tier pattern. |
| PDF in the app | moto-diag-mobile `package.json` | **No PDF viewer and no zoom library.** `react-native-fs` and `op-sqlite` are there for offline. | Greenfield. Avoid a new native module: render pages on the server as images (see below). |

Classification: **extension** of the phase 117 substrate and Track P rows,
**greenfield** for the viewer screen, page rendering and search.

## 1. The biggest issue is content

What the video shows (exploded views with torque per bolt, routing
drawings, wiring schematics) is the core product of a handful of
publishers. Copying their pages, or scraping OEM manuals into Mekno for
everyone, is not an option. Real options:

| Source | Motorcycles? | Price we found | Can it go inside our app? |
|---|---|---|---|
| **HaynesPro WorkshopData (MotoSET)** | Yes: Aprilia, BMW, Ducati, Harley-Davidson, Honda, Kawasaki, KTM, Kymco, Piaggio, Polaris, Suzuki, Triumph, Vespa, Yamaha, more later [1] | Shop licence about R6,400 a year ex VAT (about $350) from a reseller [2]; UK estimates £55 to £95 a month per user [3] | The launch release says data is "available through data exchange services (API) for bespoke solutions" [1]. Price and terms: **ask.** Best fit. |
| **Autodata Motorcycles (Solera)** | Yes: "over 9,000 motorcycle models from 79 manufacturers"; no bulletins for bikes [4] | £30 a month single user, UK, ex VAT [4] | No public API. Solera does license data to partners: **ask.** |
| **ALLDATA Repair** | Cars and light trucks, not bikes | About $199 a month per shop [5] | Shop subscription, no embedding. Not a fit. |
| **Mitchell 1 ProDemand** | Cars, not bikes | "Contact vendor" [6] | No. Not a fit. |
| **MOTOR Information Systems DaaS** | Cars, light and heavy trucks; no bikes mentioned | Not public | Yes, a real API with a sandbox [7]. Not a fit for bikes today. |
| **TecDoc (TecAlliance)** | Parts catalog, mainly cars | "No public fixed price, negotiated annually" [8] | Yes, SOAP/REST licence for parts data, not repair procedures. Later, for parts, if at all. |
| **DataOne Powersports** | US motorcycles and scooters 1996 on, 64 makes [9] | Not public | API and file feed, but vehicle specs, not manuals. Useful for vehicle lookup only. |
| **Cyclepedia** | Yes, online motorcycle manuals and a spec database of "over 203,700 service specifications" [10] | Per manual, not checked | No API found. **Ask**: small US publisher, may license specs. |
| **OEM parts fiche (EPC)** | Yes, per maker | Dealer access only | Exploded parts diagrams with callout numbers are published by each maker for dealers. Licensing per maker; not realistic for slice 1. |
| **NHTSA (vPIC, recalls)** | Yes | Free, public | Already used. VIN decode and recalls only, no diagrams. |
| **Shop's own PDFs** | Whatever the shop owns | $0 to Mekno | The shop uploads manuals it bought, for its own use only. **No licence deal needed to start.** See the flag below. |

**Licensing flags (for the lawyer read already pending on 334's terms):**

- Shop uploads must stay **private to the shop that uploaded them**. Showing
  one shop's Haynes PDF to another shop would be redistributing it.
- The terms need an upload clause: the shop says it has the right to use
  what it uploads, Mekno removes a file on a valid complaint.
- Mekno's own torque values (phase 93) are generic. They must not be shown
  next to a shop's manual page as if they came from it.
- A licensed publisher's contract will set its own rules (offline caching,
  per-seat counts, attribution). Read those before slice 2 is planned.

## 2. User flow and what the server needs

**In the app (one new screen pair, reached from the bike):**

1. **Step 1.** Open a bike (Vehicle detail or a work order). Tap **Manuals**.
2. **Step 2.** See the documents that fit this make, model and year, grouped
   by section (Engine, Brakes, Electrical, Parts diagrams).
3. **Step 3.** Search across them: "caliper bolt torque", "stator". Results
   show the page with the words.
4. **Step 4.** Open a page. Pinch to zoom, drag to pan, swipe to the next
   page. Torque values are readable at full zoom.
5. **Step 5.** Tap **Keep offline** to save that document on the phone for
   a garage with no signal.
6. **Step 6 (shop admin only).** **Add manual**: pick a PDF, set make,
   model, years and section, upload.

**On the server:**

| Need | How |
|---|---|
| Vehicle lookup | Reuse `vehicles` and the make/model/year applicability already used by the parts catalog. Year ranges as in `manual_references` (NULL = all years). |
| Content index | Extend `manual_references` with `shop_id` (owner), file hash, page count; new `manual_pages` table (manual id, page number, image path, extracted text) with an FTS5 search index. One migration. |
| Diagram and page viewer | On upload, the server turns each PDF page into an image (and a thumbnail) and pulls its text. Use a permissively licensed library such as `pypdfium2` (Apache/BSD); **avoid PyMuPDF**, which is AGPL. The app shows page images in a zoomable view, so no native PDF module and no new iOS build dependency beyond what a zoom view needs. |
| Torque spec lookup | Slice 1: search finds torque lines in the shop's own pages. Real per-model torque tables (row 297) only arrive with licensed data. |
| Offline caching | App stores page images with `react-native-fs` and the index in `op-sqlite`, both already installed. Size cap per phone, cleared on sign-out. |
| Access and storage | Shop-scoped routes like `photos.py`: `GET /v1/shop/{shop_id}/manuals?make&model&year`, `GET …/manuals/{id}/pages/{n}`, `GET …/manuals/search?q`, `POST …/manuals` (admin). Storage limit per shop. Files on the server's data directory, included in the nightly B2 backup (watch its size). |

**Tiers (suggestion):**

| Plan | Gets |
|---|---|
| Individual $19 | Read-only Mekno generic reference (torque, circuits) as today; can upload manuals for their own bikes, small storage cap (for example 500 MB). |
| Shop $99 | Shop library, every member reads it, admin uploads, offline, larger cap (for example 10 GB). |
| Company $299 | Same as Shop, shared across its locations, larger cap. |
| Later add-on | Licensed diagrams and torque tables (slice 2) as a paid add-on per seat, priced after the publisher's quote. Do not put a per-seat cost inside $19 without the numbers. |

## 3. Recommended path

**Path: library and viewer now, licensed data next, OEM fiche last.**

Why:

- **No licence needed to start.** The shop uses the manuals it already
  paid for, so Mekno is not redistributing anything.
- **Everything in slice 1 is reused by slice 2.** The viewer, the search,
  the vehicle filter and offline work the same whether the page came from
  a shop's PDF or from HaynesPro's API.
- **It fills Track P's empty tables** that have been waiting since phase
  117, and takes `motodiag.reference` off the "substrate" list.
- **It sells the Shop plan**: a shared shop library is a team feature.

**Cheapest first slice:** one migration, upload plus page rendering plus
text search on the server, two app screens (list and page viewer) with
pinch-zoom and offline. No parts linking, no torque table, no licensed
content.

**In parallel (no code):** email HaynesPro and Autodata for a partner or
API quote covering motorcycles, with the questions: per-seat or per-app
price, mobile display allowed, offline caching allowed, which makes and
years, and whether exploded parts views and torque values are included.

## 4. Draft phase row and plan outline

Plan order today is **334, 405, 330**. This does not touch the payments or
the deploy check, so it goes **after 330**, unless the operator moves it.

Suggested numbering (placeholder only): **reuse row 293**, reshaped, since
Track P already reserves the number and the plan of record already lists
Track P for Wave 2. Row 294 then becomes slice 2 (licensed diagrams) once
a quote exists. If the operator prefers new numbers, use the next free row
after 406.

Draft roadmap row:

| 293 | Shop manual library (reshaped from "Factory service manual references") | 🔲 | **Proposed 2026-11-20.** A shop uploads the PDF manuals and parts pages it owns, tags them by make, model and years, and every member opens the right page for the bike, searches it, zooms the diagram and keeps it offline. Private to the uploading shop. Fills phase 117's `manual_references` and adds pages with text search. No licensed content; licensed diagrams and torque are row 294, after a publisher's quote. Built by the fleet, after 330. App screens follow as 293B, by a mobile session. |

Plan outline (for the fleet's `implementation.md` v1.0, after Step 0):

1. **Step 0.** Re-run this audit on the then-current master: `reference/`,
   migration 117's tables, the allowlist entries, `photos.py` storage.
   Classify: extension.
2. **Migration.** `manual_references` gains `shop_id`, `file_sha256`,
   `uploaded_by`, `status`; new `manual_pages` plus FTS5. Rollback by the
   `rollback_to_version` pattern. A database step, so it goes through the
   fleet's dry run (option B until 405 lands).
3. **Server.** Upload route (shop admin, size and type checks, PDF only),
   page rendering and text extraction in a background job, list, page and
   search routes, all shop-scoped with `Literal` enums for section and
   status at the contract boundary.
4. **Wiring guard.** A test that each new route is reachable, and the
   `motodiag.reference` allowlist entries removed.
5. **Tests.** Another shop cannot list, open or search a shop's manual
   (the main risk); search finds a torque line; an over-limit upload is
   refused; a non-PDF is refused.
6. **Mobile (293B).** Manuals list from Vehicle detail and Work order,
   page viewer with pinch-zoom and swipe, offline save, admin upload.
   Regenerate API types.
7. **Terms.** Add the upload clause to the next terms version (with the
   lawyer read already pending).
8. **Docs.** v1.1, phase log, ROADMAP, CHANGELOG as usual.

## Decisions for the operator

1. **Start with the shop library (slice 1), or wait for a publisher deal?**
   Recommended: start with the library.
2. **Row 293 reshaped, or a new number?** Recommended: reuse 293.
3. **Send the two quote emails (HaynesPro, Autodata)?** Recommended: yes.
   The thread can draft them; the operator sends.

## Sources

1. [HaynesPro WorkshopData Motorcycles launch release, republished by IAAF (2021)](https://iaaf.co.uk/news/introducing-haynespro-workshopdata-motorcycles)
2. [HaynesPro WorkshopData MotoSET 1-year licence, reseller listing (South Africa)](https://autosupply.co.za/product/haynespro-workshopdata-motoset-motorcycle-technical-data-1-year-licence-atd-hynmoto/)
3. [HaynesPro pricing estimates 2026, third-party blog](https://workshopdata.us/en/blog/haynespro-pricing-ai-premium-2026)
4. [Autodata Motorcycles, vendor page (UK)](https://www.autodata-group.com/uk/motorcycles/)
5. [ALLDATA pricing on Capterra](https://www.capterra.com/p/10010667/Alldata/pricing/)
6. [ProDemand on Capterra](https://capterra.com/p/10021584/ProDemand/)
7. [MOTOR Developer Hub (DaaS API)](https://www.motor.com/developer-hub/)
8. [What is TecDoc, third-party guide (2026)](https://dev-opla.com/resources/what-is-tecdoc-auto-parts-ecommerce-guide)
9. [DataOne Powersports Data Suite brochure](https://www.dataonesoftware.com/hubfs/eBrochures/Powersports-Data-Suite-eBrochure.pdf)
10. [Cyclepedia](https://www.cyclepedia.com)

Prices are as published or reported on 2026-11-20. Third-party and reseller
figures are estimates; only a quote from the publisher is a real number.
