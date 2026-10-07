# Phase 373 — the sources, quoted

Every page below was read on **2026-10-06** with headless Chrome
(`--dump-dom`, under `perl -e 'alarm 60; exec @ARGV'`), because mass.gov
returns 403 to curl (281's finding). The quotes are copied from the page's
text as extracted (tags removed, whitespace collapsed); nothing is
paraphrased inside quotation marks. The first 16 hex digits of each
extracted text's sha256 are given so a re-read can be compared.

The question: in Massachusetts, who owes sales tax on parts a repair shop
furnishes under a warranty, when the customer pays nothing for them?

---

## W1. 830 CMR 64H.1.1(5)(g), service contracts

**Page:** DOR, "830 CMR 64H.1.1: Sales and Use Tax on Services
Enterprises", <https://www.mass.gov/regulations/830-CMR-64h11-service-enterprises>
(281's S3). "Amended: 12/21/01 - section (5)(g)"; "Amended: 12/19/03 -
sections (4) and (5)(g)". Text sha256 `06e2cf08afef2002`.

The regulation's text contains no form of "warrant". Its one passage on
repairs paid for by someone other than the bill's customer is (5)(g):

> (g) Service Contracts . The term "service contract" means, in 830 CMR
> 64H.1.1(5)(g), a contract for a specified period of time to repair,
> service or otherwise maintain tangible personal property which another
> person owns. Under the terms of a "service contract", the service
> enterprise also agrees to supply the necessary parts and material, as
> well as labor, for a specified contract price. The sale of a service
> contract is not subject to the sales or use tax. A service enterprise is
> the consumer of parts, material and other tangible personal property
> which it purchases for use primarily under a service contract and such
> enterprise shall pay the sales tax upon its purchase of such property. A
> service enterprise does not collect the sales tax from its customer on
> property which the service enterprise provides under a service contract.
> A service enterprise shall collect the sales tax on any tangible personal
> property which the original contract price does not include and for which
> the service enterprise makes a separate charge.

## W2. Letter Ruling 03-8, an even exchange under a warranty

**Page:** DOR, "Letter Ruling 03-8: Sales Tax Consequences of Certain
Merchandise Exchanges",
<https://www.mass.gov/letter-ruling/letter-ruling-03-8-sales-tax-consequences-of-certain-merchandise-exchanges>.
Dated August 15, 2003. Text sha256 `60253d32769b251a`.

> When an item of tangible personal property is sold with either an
> explicit or implicit warranty or "customer satisfaction policy," the cost
> of that warranty or satisfaction policy is included in the retail sales
> price paid at the time of purchase. Subsequent repair, replacement or
> exchange of the item for an identical or similar item with no additional
> consideration from the retail customer, an "even exchange," is neither a
> rescission of the retail sale nor an additional sale as there is no
> additional consideration paid by the retail customer in money or
> otherwise. See generally Sales Tax Information Letter #3 [2], which
> provided, " Q. An automobile dealer replaces a defective part in a new
> automobile during the warranty period. No charge is made to the customer.
> However, the dealer bills the manufacturer for the cost of the part. Is
> sales tax due? A. No sales tax is to be collected. The sales price of the
> new automobile included the warranty." [3]

Its note [2]:

> The first guidance published by the Department following enactment of
> the sales tax was in the form of "Sales Tax Information Letters." Each
> letter covered a variety of topics in question and answer format. They
> are no longer published, and many are obsolete, having been superseded by
> subsequent law changes and current DOR regulations, rulings, directives
> and TIRs.

Its note [3]:

> Note that a different result occurs when an optional service contract is
> sold independently of tangible personal property. In that situation, the
> service contract itself is not subject to tax. Sales or use tax generally
> must be paid by the service enterprise on any replacement parts or other
> taxable property transferred in connection with such a contract in
> accordance with 830 CMR 64H.1.1(5)(g). Also see LR 79-19.

## W3. Letter Ruling 79-19, a buyer protection plan

**Page:** DOR, "Letter Ruling 79-19: Motor Vehicle Buyer Protection Plan",
<https://www.mass.gov/letter-ruling/letter-ruling-79-19-motor-vehicle-buyer-protection-plan>.
Dated July 11, 1979. Text sha256 `ec30bb4c0140a9d2`.

The facts: a maker's plan, bought through the dealer, covering repairs
"not covered by your warranty":

> In most instances the customer will pay a $25.00 deductible amount for
> any single covered repair. The balance of the repair bill, including the
> dealer's charge for both parts and labor, is paid by [your company].

The ruling:

> 1. The purchase price of the ********** Plan is not subject to the
> Massachusetts sales tax. 2. The entire repair charge by the dealer is
> taxable under the Massachusetts sales tax, if the charge for parts is not
> separately stated, and whether or not the charges are partially or fully
> covered by the Plan. 3. If the charges for parts and labor are separately
> stated, the entire amount charged by the dealer for parts is taxable
> under the Massachusetts sales tax whether or not the charges are
> partially or fully covered by the Plan.

## What the three say together, and what they do not

- **A maker's warranty included in the bike's price** (W2, quoting a
  letter the DOR calls no longer published and in many cases obsolete):
  no sales tax is collected on the replaced part.
- **A service contract sold separately** (W1, W2 note [3]): the shop is
  the consumer of the parts and pays the tax when it buys them; it
  collects none from its customer.
- **A plan paid by the maker for repairs its warranty does not cover**
  (W3, 1979): the parts charge is taxable whether or not the plan pays,
  which reads as tax charged on the parts and paid by whoever pays the
  bill.
- **Not settled by any of them:** which applies when the plan was sold by
  someone other than the repairing shop (the Gate 16 job: a "Honda
  Protection Plan", coverage type `extended`), since W1 speaks of the
  enterprise that sold the contract and W3 predates W1's 2001 and 2003
  amendments; whether a shop that does not collect from the customer adds
  the tax to its claim against the provider; and how the four recorded
  coverage types (`powertrain`, `comprehensive`, `extended`,
  `aftermarket`) map onto "included in the price" and "sold
  independently". No source names a coverage type.
- **The search, and what it did not cover.** One web search restricted
  to mass.gov, "Massachusetts sales tax manufacturer warranty repair parts
  dealer reimbursed letter ruling", returned ten letter rulings: 03-8,
  79-19, 17-2, 80-52, 85-8, 85-19, 98-2, 85-1, 00-10, 83-67. Five were read
  in full: W1's regulation, 03-8, 79-19, and:
  - 85-8 and 85-19 ("Auto Repairs"): no form of "warrant" in either;
  - 17-2 (May 4, 2017, text sha256 `5459fce98add80f8`): rules on the sale
    of an extended warranty contract for a phone ("not subject to the
    Massachusetts sales/use tax" when optional and separately stated), not
    on parts furnished under one.
  The other five were not read; their titles name no repair or warranty.
  DOR directives (DD) and TIRs were not searched.

---

## The operator's further reading (2026-10-06, after choosing T2)

The operator: "read the five unread rulings and search DOR directives and
TIRs for warranty or service contracts; if any contradicts T2, stop and
show me what it says." Read the same way, the same day. Hits are counts of
"warrant" or "service contract" in the extracted text.

| source | date | sha256 (16) | hits | bears on T2? |
|---|---|---|---|---|
| LR 80-52, situs of sale, manufacturing machinery | 1980-07-17 | `48f9d14d65764a1c` | 0 | no |
| LR 98-2, the exemption under c. 64H § 6(f) | 1998-02-13 | `cdc3cda5e3113d0e` | 0 | no |
| LR 00-10, property used inconsistently with a resale or exempt-use certificate | 2000-07-31 | `3c7748587c40b59a` | 0 | no |
| LR 83-67, telephone equipment and service | 1983-07-25 | `ed04a3d1fefd5b6b` | 1 | agrees with (5)(g): W5 |
| **LR 85-1, vinyl repair service** | 1985-01-02 | `a68c3d5afbe25fab` | 3 | **contradicts on its face: W4** |
| LR 80-17, optional maintenance and consulting contracts | 1980-05-05 | `c4439bc108fea9fa` | 0 | no |
| LR 16-3, optional service contracts with computer hardware | 2016-03-24 | `0992c5dbf591d76a` | 46 | no: the tax on selling a contract, not on parts under one |
| Directive 97-4, motor vehicle leases | 1997-06-16 | `0a2d1cd81c91d11b` | 8 | no: a contract's charge inside lease payments |
| Directive 04-3, motor vehicle leases | 2004-05-03 | `8c59276a14df7da3` | 8 | no: the same question as 97-4 |
| "Service Contracts", a Division of Insurance consumer guide (PDF) | — | `60a8d4727a48296f` (file) | — | not a tax text; defines the two kinds: W6 |

The searches (restricted to mass.gov): "Massachusetts DOR directive service
contract warranty parts sales tax repair"; "Massachusetts technical
information release TIR warranty service contract sales tax parts";
"\"Directive\" Massachusetts sales tax \"service contract\" OR \"warranty\"
repair parts motor vehicle dealer"; "Massachusetts TIR motor vehicle
warranty reimbursement manufacturer dealer sales use tax parts". **No TIR
returned addresses warranty or service-contract parts**: the TIRs returned
are on aircraft parts (02-2), computer services (13-10), asphalt (98-10,
02-12), the repeal of the services tax (91-5), contractors (01-7), low-speed
vehicles (09-20), tax paid in another state (81-2, 91-7) and a motor
vehicle's sales price (92-1). Their titles name neither warranties nor
service contracts, and they were not opened. "A Dealer's Guide To: The
Massachusetts Used Vehicle Warranty Law" (a consumer-protection guide) was
returned and not read; its title names no tax.

## W4. Letter Ruling 85-1, vinyl repair service

**Page:** <https://www.mass.gov/letter-ruling/letter-ruling-85-1-vinyl-repair-service>,
dated 01/02/1985.

The question asked, item 2:

> 2. To dealerships for work performed on recently purchased cars which
> are still under warranty and for cars not under warranty;

The passage:

> Vinyl repair work does involve a transfer of tangible personal property,
> i.e. vinyl patches, thread and other material. When sold to individuals,
> medical offices, new and used car dealerships, and other businesses, this
> material would be subject to tax depending on its value compared to the
> entire charge, and whether the labor and material charges are separately
> stated on the customer's bill. Whether an automobile upon which work is
> performed is under warranty is irrelevant for sales tax purposes.

The ruling, item 1:

> 1. When a vinyl repairer separately states the amounts charged for labor
> and materials in the customer's bill, only that amount charged for
> materials, whether or not inconsequential, is subject to the sales tax.

## W5. Letter Ruling 83-67, telephone equipment and service

**Page:** <https://www.mass.gov/letter-ruling/letter-ruling-83-67-telephone-equipment-and-service>,
dated 07/25/1983. Rulings 3 and 4:

> 3. The Company's periodic charges under the optional maintenance
> agreements are not subject to the sales or use tax. However, on its sales
> and use tax returns, the Company must include in its gross receipts the
> cost to it of property it uses under such agreements. 4. The Company must
> collect the sales tax when it transfers any tangible personal property
> under the lease and maintenance agreements for a separate charge.

## W6. "Service Contracts" (Division of Insurance)

**Document:** <https://www.mass.gov/doc/service-contracts/download>, a PDF
that mass.gov refuses to curl and WebFetch (403); downloaded by headless
Chrome with PDF viewing turned off. It names no tax.

> Service contracts are a guarantee, negotiated and purchased separately
> from the sale of a product, that provide protection for defective parts,
> mechanical or electrical breakdown, labor, or other remedial measures,
> such as repair or replacement of the property or repetition of services.

> A service contract is not a "warranty" which is defined as a guarantee
> incidental to the sale of a product that is made solely by the
> manufacturer, importer or seller of the property or services
