# Phase 375 — the sources, quoted

Read on **2026-10-07**, at Step 0, the way 373 and 376 read theirs: each
page rendered with headless Chrome (`--dump-dom`, under `perl -e 'alarm
60; exec @ARGV'`), its text extracted (scripts and tags removed,
whitespace collapsed), and the first 16 hex digits of the extracted text's
sha256 recorded. The page chrome changes by day, so a hash differs from
373's for the same ruling. Nothing inside quotation marks is paraphrased.

The question: in Massachusetts, when a warranty plan charges the customer
a deductible for a covered repair, is the deductible taxed, and on what?

Read directly in this session, not through Subconscious: six pages, and
the passages had to be exact (rule 2 covers bulk reading; recorded in the
log).

---

## D1. LR 79-19, Motor Vehicle Buyer Protection Plan (re-read in full)

<https://www.mass.gov/letter-ruling/letter-ruling-79-19-motor-vehicle-buyer-protection-plan>.
"Date: 07/11/1979". Text sha256 `7c4bd2d3b5e0fe05`. One hit for
"deductible".

The facts:

> In most instances the customer will pay a $25.00 deductible amount for
> any single covered repair. The balance of the repair bill, including the
> dealer's charge for both parts and labor, is paid by [your company].

Rulings 2 and 3:

> 2. The entire repair charge by the dealer is taxable under the
> Massachusetts sales tax, if the charge for parts is not separately
> stated, and whether or not the charges are partially or fully covered by
> the Plan. 3. If the charges for parts and labor are separately stated,
> the entire amount charged by the dealer for parts is taxable under the
> Massachusetts sales tax whether or not the charges are partially or
> fully covered by the Plan.

**What it settles:** on its own facts a covered repair carries a
deductible, so it is "partially covered", and the **entire** parts charge
is taxable. A deductible changes who pays part of the bill, not the
amount of the bill that is taxable.
**What it does not say:** whether the customer's deductible or the plan's
balance carries that tax, or whether the $25.00 includes tax.

## D2. LR 03-8, an even exchange (re-read)

<https://www.mass.gov/letter-ruling/letter-ruling-03-8-sales-tax-consequences-of-certain-merchandise-exchanges>.
"Date: 08/15/2003". Text sha256 `e15cc4f65c98138f`. No "deductible".
Four hits for "consideration".

> Subsequent repair, replacement or exchange of the item for an identical
> or similar item with no additional consideration from the retail
> customer, an "even exchange," is neither a rescission of the retail sale
> nor an additional sale as there is no additional consideration paid by
> the retail customer in money or otherwise.

The ruling:

> When a retail vendor exchanges or replaces taxable merchandise with
> identical or similar merchandise for no additional consideration because
> of a defect or because the item is otherwise unsatisfactory to the retail
> customer, an "even exchange," no additional sales tax is due from the
> retail customer

**What it settles:** the no-tax treatment of a maker's warranty (373's
`maker_with_bike`) is stated for a repair "with no additional
consideration from the retail customer". **What it does not say:** what a
repair is when the customer does pay something. A deductible is
consideration "in money", so the ruling's own condition is not met. It
does not rule on that case.

## D3. 830 CMR 64H.1.1, Service Enterprises (re-read)

<https://www.mass.gov/regulations/830-CMR-64h11-service-enterprises>.
"Date: 12/19/2003". Text sha256 `575e5d66c76a6d1a`. No "deductible".

(5)(g):

> A service enterprise does not collect the sales tax from its customer on
> property which the service enterprise provides under a service contract.
> A service enterprise shall collect the sales tax on any tangible personal
> property which the original contract price does not include and for which
> the service enterprise makes a separate charge. This is true even though
> the service enterprise pays the sales tax when it purchases the property.

**Not settled:** whether a deductible is a "separate charge" for property
"the original contract price does not include" (taxed), or part of what
the contract provides (not collected). The regulation does not use the
word.

## D4. LR 80-17, optional maintenance and consulting contracts

<https://www.mass.gov/letter-ruling/letter-ruling-80-17-optional-maintenance-and-consulting-contracts-name>.
"Date: 05/05/1980". Text sha256 `02387b408ecc11ea`. No "deductible".

> Moreover, it must collect the sales tax on any tangible personal
> property which the maintenance and consultation contracts do not include
> and for which it makes a separate charge. This is true even if the
> Company pays the sales tax when it purchases the property; in this case,
> it may deduct the cost of the property to it from gross sales as an
> adjustment on its next sales tax return.

The same rule as D3, with the adjustment that avoids paying tax twice on
one part. It is the shop's accountant's adjustment, not an export row.

## D5. LR 85-8, Auto Repairs

<https://www.mass.gov/letter-ruling/letter-ruling-85-8-auto-repairs>.
"Date: 01/22/1985". Text sha256 `7330ab1c7641dd86`. No "deductible".

> 1. When the repairer separately states the amount charged for parts and
> labor, only that amount charged for parts, whether or not
> inconsequential, is subject to the sales tax. 2. When the repairer does
> not separately state amounts charged for parts and labor, the entire
> value of the charge is subject to the sales tax, but only if the parts
> comprise a consequential (ten percent or greater) amount of the total
> charge.

**What it settles for this phase:** a deductible charged as one line,
without its parts share stated, is taxable whole whenever parts are 10 %
or more of it. Stating the deductible's labour and parts shares
separately keeps the tax to the parts share.

## D6. "Service Contracts" (Division of Insurance, consumer page)

<https://www.mass.gov/info-details/service-contracts>. Text sha256
`3e0b8345bd9852d7`. Four hits for "deductible". It names no tax.

> A service contract may require a deductible. If there is a deductible,
> verify whether it is for each service call or for each repair.

A plan's own terms decide whether a deductible is charged per repair or
per visit. 79-19's plan charged it "for any single covered repair".

## Blocked

- **G.L. c. 64H, § 1** (the definition of sales price), at
  malegislature.gov: Chrome returned an empty page (sha256 of nothing,
  `e3b0c44298fc1c14`); WebFetch, "Socket is closed". This is the same
  block 376 met on § 33. Not relied on.

## The searches

Restricted to mass.gov, 2026-10-07:
1. "Massachusetts sales tax deductible warranty service contract repair
   letter ruling";
2. "Massachusetts DOR \"deductible\" sales tax repair parts extended
   service contract customer pays";
3. "Massachusetts sales tax insurance deductible auto repair parts taxable
   letter ruling".

They returned LR 17-2, 16-3, 85-8, 83-67, 85-1, 79-19, 85-19, 03-8, 80-17,
00-10, 82-22, 98-2, 83-35, 96-4 and 79-39, Directives 97-4 and 04-3, the
consumer page D6 and the DOR's guide. 373 and 376 already read 17-2, 16-3,
83-67, 85-1, 85-19, 00-10, 98-2 and both directives, and found no
deductible. The titles of 82-22 (auto parts and paint), 83-35 (supplies
sold to body shops), 96-4 (re-painting) and 79-39 (contractor materials)
name no warranty or contract, and they were not opened.

**No Massachusetts source read rules on the tax on a warranty deductible
by name.** The positive control: "deductible" is found in 79-19 (1 hit)
and D6 (4), so the extraction does find the word when a page uses it.

## What the sources say together

- **`other`, someone else's plan (79-19, 85-1):** the entire covered
  parts charge is taxable whether the plan covers it "partially or
  fully", so a deductible does not change the tax: 6.25 % of all
  covered parts. Only its split between the customer and the claim is
  open.
- **`maker_with_bike` (03-8):** no tax is stated only for a repair "with
  no additional consideration from the retail customer". A deductible is
  consideration, so the sources give no basis for leaving the
  deductible's parts share untaxed.
- **`shop_contract` ((5)(g), 80-17):** tax is collected on a "separate
  charge" for property the contract price does not include. Whether a
  deductible is one is not settled. Collecting is the reading that does
  not lower tax. 80-17's adjustment keeps the shop from paying twice.
- **Every payer (85-8):** state the deductible's parts share separately,
  or the whole deductible is taxable.
