# Phase 376 — the sources, quoted

Read on **2026-10-07**, at Step 0. Each page was rendered with headless
Chrome (`--dump-dom`, under `perl -e 'alarm N; exec @ARGV'`), its text
extracted (scripts and tags removed, whitespace collapsed), and the first
16 hex digits of the extracted text's sha256 recorded, as in 373. Where
Chrome returned an empty page or mass.gov a 403, the route taken instead
is said, and a page that could not be read at all is **blocked**. Nothing
inside quotation marks is paraphrased, except where a quote came through
WebFetch, which says so.

Two questions: how each vendor imports what a settlement books, and what
the jurisdiction says about the tax on a shortfall the shop absorbs.

---

## Formats

### X1. Xero, "Import customer credit notes" (US)

**URL:** <https://central.xero.com/s/article/Import-a-customer-credit-note-US>.
Text sha256 `c57855486679c851`. No updated date on the page. The UK and
global addresses render the same instructions (`eb0f5874eba3ab0d`,
`707d00e58f709667`; their passages below are identical).

- "Copy customer credit note information into a CSV template, then import
  the file into Xero. Xero imports the credit notes as drafts, so you can
  approve them after the import."
- The template: "In the Sales menu, select Sales overview . Click the
  import icon . Click Download template file ." It is a template of its
  own; the page names no way to put invoices and credit notes in one file.
- "If you're importing more than 500 items, we recommend you split up the
  file."
- "Required columns are marked with an asterisk (*) in the template."
  Required, as the page lists them: `ContactName`, `InvoiceNumber`,
  `InvoiceDate`, `DueDate`, `Description`, `Quantity`, `UnitAmount`,
  `AccountCode`, `TaxType`.
- "InvoiceNumber Enter the credit note number. Numbers must be different
  for each invoice and credit note in this file, and different from any
  credit notes already entered in Xero. If you want to import multiple line
  items on a single credit note, use the same credit note number for each
  line item."
- "InvoiceDate DueDate Enter the date and the due date of the credit note.
  Use the format MM/DD/YYYY."
- "UnitAmount Enter the price of the item, as a negative amount. Enter all
  prices in this file as either tax inclusive or tax exclusive, but not a
  mixture of both. You'll select whether the file contains inclusive or
  exclusive prices when you import this file."
- "TaxType Enter the sales tax rate display name as it appears in Xero.
  … The Total and Tax Amount columns will be calculated automatically
  based on the data entered in the Quantity, Unit Amount and Tax Type
  fields. If an Account Code or Tax Type isn't entered, the import will be
  set to Tax Exempt (0%), and the credit note total will be the tax
  exclusive amount."
- Optional: `EmailAddress`, `POAddressLine1` …, `Reference` ("Enter a
  reference to help you identify and search for the credit note."),
  `InventoryItemCode`, `Discount`, `TrackingName1`, `TrackingOption1`,
  `TrackingName2`, `TrackingOption2`, `Currency`, `BrandingTheme`.
- "TaxAmount Import a different tax amount from the amount that would be
  calculated using the rate entered in the TaxType column. To do this, add
  a new column to the template file, enter the heading TaxAmount, and
  enter the amount of tax. When you import this file, make sure you
  indicate that amounts are tax exclusive."
- "What's next? Approve the draft credit notes you imported from the Draft
  tab in Sales overview ."

**What the page does not give:**
- **No column links a credit note to an invoice,** and the page says
  nothing of allocation. Allocation is by hand in Xero (X3).
- **The sign of `TaxAmount` on a credit note.** `UnitAmount` is negative;
  the page does not say whether `TaxAmount` is negative too. Not guessed
  past: see Step 0's Q5.
- The template's full header row (behind a login, as in 275).

### X2. Xero, "Import customer invoices" (US), re-read

**URL:** <https://central.xero.com/s/article/Import-customer-invoices-US>.
Text sha256 `7596898aef2ff98f`. 275's quotes still hold. The extracted
text holds no "credit note" and no "negative": the invoice import says
nothing of credit notes.

### X3. Xero, "Credit notes explained" and "Create and approve a customer credit note"

**URLs:** <https://central.xero.com/s/article/Credit-notes>
(`ddccda9ef1665c76`);
<https://central.xero.com/s/article/Add-a-credit-note-to-a-customers-invoice>
(`5fa169e60821d9cf`).

- "Allocate a credit note to, or apply a credit note from, an invoice or
  bill to reduce the amount due for that invoice or bill. When you
  allocate or apply a credit note, Xero records a credit allocation on the
  credit note and a payment transaction on the invoice or bill."
- "Approve the credit note so it can be allocated to an invoice."
- "You can only credit an awaiting payment invoice if it's in the same
  currency as the credit note."
- "Credit notes have their own numbering sequence ."
- "If you've approved the credit note and have an awaiting payment invoice
  for the customer, you'll be prompted to apply the credit. You can either
  enter the amount to credit, then click Allocate credit , or click Cancel
  to allocate the credit note later."

### X4. Xero, "Common scenarios for credit notes" (US)

**URL:** <https://central.xero.com/s/article/Common-scenarios-for-credit-notes-US>.
Text sha256 `7c94793a360da2d0`.

- "you raised an invoice for 11,000 against your sales account, but it was
  supposed to be for 10,000. You can raise a credit note for 1,000 against
  your sales account. Xero will immediately prompt you to apply this credit
  note to the invoice, reducing the amount owing on the invoice to 10,000.
  Your Income Statement will now reflect 10,000 of sales and your tax
  liability will be adjusted."
- "you raised an invoice for 10,000 against the sales account and agreed
  to give a 15% discount. The customer will pay you 8,500, leaving 1,500
  outstanding on the invoice. You can raise a credit note for 1,500
  against a discounts account and Xero will prompt you to apply the credit
  note to the invoice, leaving the invoice and the credit note fully paid.
  Your Income Statement will now reflect 10,000 of sales and 1,500 of
  discounts."

### X5. Xero, "Write off a bad debt in Xero" (US)

**URL:** <https://central.xero.com/s/article/Record-a-bad-debt-in-Xero-US>.
Text sha256 `2c6851c4230f2704`.

- "We recommend you ask your accountant or bookkeeper for the best method
  for your organization."
- "If you're on an accrual basis for sales tax, you could apply a credit
  note to the outstanding invoice. Categorize the credit note to a specific
  bad debts account code. If you're on a cash basis for sales tax, you
  might wish to categorize the credit note to the same account code and
  tax rate as the original invoice."
- "Find the invoice that you want to write off. Click the menu icon and
  select Create and apply credit . In the Account field, select the same
  account code as the original invoice or select your bad debts account.
  Ensure the date, tax rate and credited amount are correct."
- "Warning You should consider the tax implications when choosing an
  account. Talk to your accountant or bookkeeper if you need assistance."

### Q1. Intuit, "Import journal entries" (QuickBooks Online, US), re-read

**URL:** as in 275. Headless Chrome returned an empty page twice and curl
failed (HTTP/2 stream error); read through **WebFetch**, whose answer
quotes:
- "Updated 8/4/2026 00:57";
- the required fields as 275 lists them;
- "Depending on Account Name selection (Accounts Payable or Accounts
  Receivable)" "the system will request the Name column to have a vendor
  selected."

The page says nothing about balancing, the date format, or **whether one
journal may carry two Accounts Receivable lines with different names**.

### Q2. Intuit, "Apply a journal entry credit to an invoice" (US)

**URL:** <https://quickbooks.intuit.com/learn-support/en-us/help-article/journal-entries/apply-journal-entry-credit-invoice/L6SrExcv1_US_en_US>.
Through **WebFetch** (as Q1). "Updated 8/5/2026 04:56".
- "Create a journal entry using Accounts Receivable account."
- "Choose your customer's name from the Name column on the journal entry."
- The steps: "Select + Create." "Select Receive payment." "Choose a
  customer." "Under Outstanding Transactions, pick the invoice." "Under
  Credits, select the journal entry you created." "Select Save and close."

So a journal crediting A/R in a name is an open credit in that name until
the shop applies it, by hand, in Receive payment.

---

## The tax on an absorbed shortfall: Massachusetts

The question: when a claim carried tax to its provider (373's payer
`other`) and the provider pays short or denies, and the shop absorbs the
shortfall, does the shop still owe the tax it charged, or does absorbing
reverse the sale; and is tax due on parts given away?

### T1. TIR 00-3, "Claiming the Bad Debt Reimbursement"

**Page:** <https://www.mass.gov/technical-information-release/tir-00-3-claiming-the-bad-debt-reimbursement>.
"Date: 02/10/2000". Text sha256 `a772a9e9fdc90e12`. It "supersedes and
revokes TIR 92-2".

- "The purpose of this Technical Information Release (TIR) is to explain
  the documentation and calculation requirements for claiming the bad debt
  reimbursement under Massachusetts General Laws, Chapter 64H, § 33, as
  amended by St. 1998, c. 485, §§ 20, 23, effective January 1, 1999 and
  G.L. c. 64I, § 34."
- "Under the bad debt reimbursement provisions, vendors may file a claim
  for reimbursement of sales or use tax they have remitted to the
  Department of Revenue on accounts which are later determined to be
  worthless. An account is determined to be worthless when it is written
  off as uncollectible for federal income tax purposes under section 166
  of the Internal Revenue Code."
- "Bad debt reimbursement claims must be filed on form ST-BDR (or
  ST-BDR-Meals for sales tax on meals). Bad debt reimbursements may not be
  claimed on any other return and bad debts may not be subtracted from
  gross receipts on a vendor's sales or use tax return."
- "Reimbursements are paid annually without interest."
- "any vendor who recovers, in whole or in part, a bad debt for which a
  reimbursement has been received must include the recovered amount in its
  gross receipts on the sales or use tax return covering the period in
  which the recovery occurs."
- "vendors must subtract any finance charges and other nontaxable charges
  such as charges for nontaxable services, non-Massachusetts sales and the
  sales tax itself, from the account determined to be worthless. The
  remaining taxable portion of the worthless account is multiplied by the
  sales tax rate to determine the reimbursement amount."

### T2. LR 00-10, property used inconsistently with a resale certificate

**Page:** <https://mass.gov/letter-ruling/letter-ruling-00-10-sales-tax-treatment-of-property-used-inconsistently-with-resale>.
"Date: 07/31/2000". Text sha256 `270116a87987f574` (373 recorded
`3c7748587c40b59a` for its read; the page's chrome differs by day). It
quotes the statute:

> "service or property other than retention, demonstration or display
> while holding it for sale in the regular course of business, the use
> shall be deemed a retail sale by the purchaser as of the time the
> service or property is first used by him, and the cost of the service or
> property to him shall be deemed the gross receipts from such retail
> sale. G.L. c. 64H, § 8(d)"

### Blocked

- **G.L. c. 64H, § 33** at malegislature.gov: Chrome returned an empty
  page; curl failed (TLS `SSL_ERROR_SYSCALL`); WebFetch, "Socket is
  closed". Its content is taken only as T1 states it.
- **830 CMR 64H.1.4, "Discounts, Coupons and Rebates"**
  (<https://www.mass.gov/regulations/830-CMR-64h14-discounts-coupons-and-rebates>):
  403 to Chrome, twice, and to WebFetch. A search engine's summary says it
  treats property given for no consideration as a promotional item the
  vendor consumes, taxed on its cost. **Not read, so not relied on.**
- **Form ST-BDR** itself: not opened; T1 states its role.

### What the sources say together, and what they do not

- **Tax charged and then not collected stays owed on the return:** "bad
  debts may not be subtracted from gross receipts on a vendor's sales or
  use tax return" (T1). Relief, if any, is a separate annual claim on Form
  ST-BDR, after the account is written off for federal income tax
  purposes under IRC § 166, filed with the facts of each account (T1).
  That is the shop's accountant's filing, not an export row.
- **Nothing read says that a provider's denial or short payment reverses
  the sale.** The repair was done and the parts transferred; LR 79-19
  (373's W3) taxes the parts charge "whether or not the charges are
  partially or fully covered by the Plan".
- **Not settled:**
  - whether a **part approval** is a bad debt (T1) or a price reduction
    agreed after the sale (830 CMR 64H.1.4, blocked). Both readings leave
    the tax on the return in the period of the sale; they differ only on
    whether ST-BDR can later recover it;
  - **parts given away under a claim that carried no tax** (payer
    `maker_with_bike`, LR 03-8's even exchange): if the maker denies and
    the shop absorbs, LR 00-10's statute (T2) reads as a use of property
    bought for resale, taxed on its cost to the shop. That would *raise*
    the shop's tax, and the export has no cost basis for it. Not
    settled by a source read in full.
