# Phase 281 — the sources, quoted

Every page below was read on **2026-09-30**. The quotes are copied from
the page's text as extracted (tags removed, whitespace collapsed); nothing
is paraphrased inside quotation marks. How each page was read is given,
because two sites refuse non-browser clients.

These are documentation pages, not the services' APIs. No API endpoint
was called while writing this file; the build's smoke calls are logged in
`281_phase_log.md`.

---

## S1. Massachusetts: the sales tax rate

**Page:** Massachusetts Department of Revenue, "Sales and Use Tax" (guide),
<https://www.mass.gov/guides/sales-and-use-tax>. The page reads
"Updated: May 7, 2026". mass.gov returns 403 to curl, with and without a
browser User-Agent; read with headless Chrome (`--dump-dom`).

> The Massachusetts sales tax is 6.25% of the sales price or rental charge
> of tangible personal property (including gas, electricity, and steam)
> and telecommunications services 1 sold or rented in Massachusetts. The
> buyer pays the sales tax, as an addition to the purchase price, to the
> vendor at the time of purchase. The vendor then sends the tax to
> Massachusetts.

Under its heading "Tax-Exempt Items & Sales" ("The following categories of
sales or types of transactions are generally exempted from the sales/use
tax:"), the entry "Personal or professional services" lists "Accounting",
"Insurance", "Legal and medical services", "Haircuts" and "Car repairs",
then:

> Items sold along with services (e.g., a bottle of shampoo from a salon,
> parts for a car repair), are taxable and must be itemized separately on
> the bill.

> In general, when determining the charges in a transaction that are
> taxable, the seller cannot exclude the cost of materials used, labor or
> service costs, or other expenses. However, charges for installing
> tangible personal property are not taxed as long as these charges
> separately stated from the charge for the tangible personal property.

> If you're a service provider with questions about the taxability of your
> transactions, refer to the Services Enterprises regulation, 830 CMR
> 64H.1.1 , or contact our Rulings and Regulations Bureau at
> rulesandregs@dor.state.ma.us .

On what the vendor must do:

> Collecting the sales/use tax on taxable sales or rentals of tangible
> personal property or telecommunications services (the tax must be
> separately stated and separately charged on all invoices, bills,
> displays or contracts), and

## S2. Massachusetts: when 6.25% took effect

**Page:** DOR, "TIR 09-11: Change in Rate, Scope, and Computation of
Sales/Use Taxes",
<https://www.mass.gov/technical-information-release/tir-09-11-change-in-rate-scope-and-computation-of-salesuse-taxes>.
Read with headless Chrome. (A first guess at the URL returned mass.gov's
403 page; the address above came from a search restricted to mass.gov.)

> The Legislature has amended c. 64H (sales tax) and c. 64I (use tax),
> changing the rate of tax for sales and use of tangible personal property
> and telecommunications services from 5% to 6.25%. See Stat. 2009, c. 27,
> §§ 53, 55-57, 59. This change is effective on and after August 1, 2009,
> id. § 155, subject to transition rules described in § IV of this TIR.

**Neither page states an end date or a period of validity for the rate.**

## S3. Massachusetts: what a repair shop taxes

**Page:** DOR, "830 CMR 64H.1.1: Sales and Use Tax on Services
Enterprises", <https://www.mass.gov/regulations/830-CMR-64h11-service-enterprises>.
Read with headless Chrome. The page lists "Amended: 12/21/01 - section
(5)(g)" and "Amended: 12/19/03 - sections (4) and (5)(g)".

(2), General Application:

> This regulation, 830 CMR 64H.1.1, applies to a transaction which a
> service enterprise undertakes. Some examples of a service enterprise
> are: repairers of motor vehicles, airplanes, boats, watches, televisions,
> radios, machinery, musical instruments or jewelry; […]

> (a) A service transaction is not subject to the sales tax where :
> 1. The real object of the transaction is the service itself, and no
> transfer of tangible personal property occurs; or
> 2. The real object of the transaction is the service itself, and an
> inconsequential transfer of tangible personal property occurs, and the
> service enterprise does not separately state the purchase price of the
> property on the bill to the customer. […]

> (b) A service transaction is subject to the sales tax where :
> 1. The transfer of tangible personal property occurs, and the charge for
> the property is stated separately from the charge for labor on the bill
> to the customer, whether or not the value of the property is
> inconsequential; or
> 2. The transfer of tangible personal property occurs, and the value of
> the property is not inconsequential in relation to the total charge, and
> the charge for the property is not separately stated on the bill to the
> customer.

> In 830 CMR 64H.1.1(2)(b)1., the service enterprise collects a sales tax
> from its customer based on the amount charged for the property; […]

(5)(a), Repairers:

> (a) Repairers . A repair service shall collect a tax on parts or any
> materials which it furnishes in connection with repair work, where the
> value of the parts or materials is not inconsequential. This applies,
> for example, to the repairer of a motor vehicle, airplane, bicycle,
> machine, musical instrument, radio, television set, boat, or furniture.
> If the repair service does not separate on its customer invoices and in
> its records, the fair retail selling price of the parts or materials from
> the charge for labor, installation or other services, the Commissioner
> presumes that the entire charge represents the sales price of the
> property (See 830 CMR 64H.1.1(2)(b)2.).

**What the pages say about the four invoice line types** (the build's
reading, clause by clause, in `281_step0.md` S0-7):
- parts, separately stated: taxable, (2)(b)1 and (5)(a);
- labour, separately stated: not taxable, (2)(a)1 and (5)(a), and the
  guide's "Car repairs";
- a diagnostic fee: a service with no transfer of property, (2)(a)1;
- **shop supplies: none of the three pages names a shop-supplies charge.**

## S4. NHTSA recalls: the service's behaviour (measured on disk, not read)

`www.nhtsa.gov/nhtsa-datasets-and-apis` returned Akamai's "Access Denied"
to curl (with and without a browser User-Agent) and to headless Chrome on
2026-09-30, so NHTSA's own description of the recall endpoints could not
be read. What is known comes from this project's own measurements in
Phase 251 and 252, recorded in F103 (`moto-diag-mobile/docs/FOLLOWUPS.md`)
and in `~/research/motodiag/` (27,190 recorded responses in
`all_recalls.jsonl`, and per-campaign files such as `15V439000.json`,
fetched 2026-09-20):
- `api.nhtsa.gov` returns 403 to Python's default `urllib` User-Agent;
  curl, and a `Mozilla/5.0` User-Agent, got through;
- `recalls/recallsByVehicle?make=…&model=…&modelYear=…` answers a query
  with no result with **HTTP 400 and a valid body**
  `{"Count":0,"Message":"Results returned successfully","results":[]}`;
- a model name NHTSA does not use returns the same 400 body as a year with
  no campaign: "nothing in the response can validate a model string";
- a block returns an HTML body, not JSON;
- the known-present campaign F103 names: `PIAGGIO`, `MP3 500`, 2020 →
  `20V524000`.

A result's fields, from `15V439000.json`: `Manufacturer`,
`NHTSACampaignNumber`, `parkIt`, `parkOutSide`, `overTheAirUpdate`,
`ReportReceivedDate` (`DD/MM/YYYY`: "14/09/2000" appears), `Component`,
`PotentialNumberofUnitsAffected`, `Summary`, `Consequence`, `Remedy`,
`Notes`, `ModelYear`, `Make`, `Model`. **No severity field exists.**

## S5. NHTSA vPIC

**Page:** <https://vpic.nhtsa.dot.gov/api/>, "Version: 4.06 Last Code
Change 6/13/2026". Read with curl.

> Users/Applications attempting to use vPIC APIs will be controlled by an
> automated traffic rate control mechanism to ensure optimal performance
> of the NHTSA websites and minimize adverse impact to our users.

> Decode VIN (flat format)
> /vehicles/DecodeVinValues/5UXWX7C5*BA?format=xml&modelyear=2011

> The Decode VIN Flat Format API will decode the VIN and the decoded
> output will be made available in a flat file format.
> Model Year in the request allows for the decoding to specifically be
> done in the current, or older (pre-1980), model year ranges. It is
> recommended to always send in the model year.

The page gives no sample response; the smoke call's response is the
fixture.

## S6. ECB euro foreign exchange reference rates

**Page:** <https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html>.
Read with curl. It showed the rates for "30 September 2026", "All
currencies quoted against the euro (base currency)", including USD, CAD
and GBP. Its download links include `/stats/eurofxref/eurofxref-daily.xml`.

> The reference rates are usually updated at around 16:00 CET every
> working day, except on TARGET closing days .

> They are based on the daily concertation procedure between central
> banks across Europe, which normally takes place around 14:10 CET. The
> reference rates are published for information purposes only. Using the
> rates for transaction purposes is strongly discouraged.

**The page states no period of validity** beyond the daily update.
Converting between two non-euro currencies (USD to CAD) through the euro
is a cross rate this build computes; the ECB does not publish it.
