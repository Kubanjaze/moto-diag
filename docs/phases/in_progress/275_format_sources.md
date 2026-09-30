# Phase 275 — the vendors' published import formats

Read 2026-09-29. Each passage is quoted from the vendor's own page, as it
read that day. Where a page did not say something, this file says so.

## Xero: "Import customer invoices" (Xero Central, US)

**URL:** https://central.xero.com/s/article/Import-customer-invoices-US
**Read:** 2026-09-29. The page renders only in a browser, so it was
rendered with headless Chrome (`--dump-dom`) and its text extracted. It
shows no updated date.

Quoted:
- "Once you've downloaded the template file, enter the invoice details.
  Don't delete any columns or change any column headings, as these are
  needed for the file to import."
- "We recommend importing no more than 500 items in a single file."
- "The only required columns are ContactName and InvoiceNumber. Any other
  fields can be left blank and completed in Xero afterwards. If your
  organization doesn't use a particular feature, eg tracking, foreign
  currency or inventory, you can ignore those columns."
- "Some columns, such as AccountCode, TaxType, TrackingName,
  TrackingOption, Currency and BrandingTheme, require you to enter values
  exactly as they appear in Xero, otherwise the information won't be
  imported."
- "ContactName – If an invoice in the file is for an existing contact,
  ensure this exactly matches the contact name in Xero, to avoid creating
  a duplicate contact record."
- "InvoiceNumber – Each invoice in the file must have a unique invoice
  number. If an invoice number in the file already exists in Xero, that
  invoice won't be imported."
- "Each row in the file represents one invoice line. If a single invoice
  contains multiple lines, use the same invoice number for each row to
  tell Xero that they belong to the same invoice."
- "UnitAmount – Amounts can either include or exclude tax, but the file
  can't have a mixture of both. When you import the file, confirm which
  option you've used."
- "InvoiceDate and DueDate – Use the format MM/DD/YYYY."
- "AccountCode – Enter the relevant account code as it displays in the
  chart of accounts."
- "TaxType – Enter the tax rate display name as it displays in tax
  settings. If the name contains words and a percentage, enter it in full,
  eg Tax on Sales (8.25%)."
- "Xero automatically calculates the amount of tax for each invoice using
  the tax rate and amount. If you need to enter specific tax amounts, add
  a new column to the file with the heading TaxAmount, and enter the
  required amounts there. After you import the file, the invoices will
  include a tax adjustment for the difference between the entered tax and
  calculated tax. If you use this option, enter prices as tax exclusive."
- "Currency – Enter the 3-letter abbreviation of the currency of the
  invoice, eg EUR."
- "The invoices are imported as drafts, which you can approve immediately
  or edit first."

**What the page does not give:** the template's full header row. It is
in the file Xero offers under Sales › Invoices › Import › "Download
template file", which needs a Xero login. Third-party pages reproduce
different column sets (one lists an export's columns, not the import
template's). No third-party list is used as the vendor's.

## QuickBooks Online: "Import multiple invoices at once" (Intuit, US)

**URL:** https://quickbooks.intuit.com/learn-support/en-us/help-article/import-export-data-files/import-multiple-invoices/L7E9Xrd8l_US_en_US
**Read:** 2026-09-29. The page reads "Updated 8/5/2026".

Quoted:
- Plans: "QuickBooks Online Advanced, QuickBooks Online Plus, QuickBooks
  Online Essentials, Intuit Enterprise Suite".
- Required columns: "Invoice number, Customer, Invoice date, Due date,
  Item amount".
- "If you have set up sales tax in your account, you can't import
  invoices this way."
- "Each imported spreadsheet can contain up to 1,000 rows"; "You can
  import a maximum of 100 invoices at a time".
- "You can't add negative charges, such as discounts or credit memos".
- "Each line item needs its own invoice number, customer, invoice date,
  due date, and item amount".
- "QuickBooks populates with a generic item called 'sales' for missing
  products and services."

## QuickBooks Online: "Import journal entries" (Intuit, US)

**URL:** https://quickbooks.intuit.com/learn-support/en-us/help-article/import-export-data-files/import-journal-entries-quickbooks-online/L4tQBwbs7_US_en_US
**Read:** 2026-09-29. The page reads "Updated 8/4/2026".

Quoted or read:
- Plans: Advanced, Plus, Simple Start, Essentials, Free, Lite and
  Solopreneur Plus.
- Required columns: "Journal No.", "Journal Date", "Account Name",
  "Journal/Description", "Debits", "Credits". A Name column is asked for
  when an Accounts Receivable or Accounts Payable account is used.
- Account numbers are to be turned off before the import; a sub-account is
  written "Parent account: Sub Account"; the chart of accounts must hold
  every account first.
- The page states no date format and no row limit.
- It says nothing about sales tax. (An Intuit community answer, not a
  help article, says a sales-tax column is not available and suggests a
  liability-account line for the tax.)

## QuickBooks Desktop: IIF (Intuit, US)

**URL:** https://quickbooks.intuit.com/learn-support/en-us/help-article/list-management/iif-overview-import-kit-sample-files-headers/L5CZIpJne_US_en_US
**Read:** 2026-09-29. The page reads "Updated 8/4/2026".
- "Intuit Interchange Format (.IIF) files are ASCII text, TSV
  (Tab-Separated Value) files that QuickBooks Desktop uses to import or
  export lists or transactions." Desktop only.
- Sample files come with sales tax (`iif1.zip`) and without (`iif2.zip`).
- "Intuit does not offer assisted technical support for creating or
  importing .IIF files"; import has "only limited error checking".

**QuickBooks Desktop's availability:**
https://quickbooks.intuit.com/learn-support/en-us/help-article/new-subscriptions/us-quickbooks-desktop-sold-july-2024/L5lkQNq7L_US_en_US
(read 2026-09-29, through search results): after 2024-09-30 Intuit no
longer sells new subscriptions of QuickBooks Desktop Pro Plus, Premier
Plus and Mac Plus in the United States. Existing subscribers can renew,
and Enterprise is still sold.
