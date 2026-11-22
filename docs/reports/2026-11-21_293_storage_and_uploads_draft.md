# Phase 293: manual storage per plan, the upload wording, and the review step

Written 2026-11-21 by the research thread that wrote the manuals brief,
at the operator's request: "shouldnt you look up how much manual storage
each plan needs and create a draft and review your own proposed wording
for uploads ... all submissions have to be super verified, like if
anything they can submit it and someone on the dev team would check and
verify, or maybe we could create another fleet to handle those requests".

This answers the two questions K94 left for before 293 starts. It is a
draft for the operator's decision. Nothing in the code, the terms, the
privacy policy or Stripe was changed. No legal advice: the wording goes
to the lawyer read already pending on 334's terms.

## The short answer

| Plan | Manual storage | About how many manuals | Largest file |
|---|---|---|---|
| **Individual** $19 | **2 GB** | about 10 | 300 MB |
| **Shop** $99 | **20 GB** | about 100 | 300 MB |
| **Company** $299 | **50 GB**, shared by its shops | about 250 | 300 MB |

**Every upload is checked before anyone can open it**: first by the
server automatically, then by a person at Mekno who approves or rejects
it. Until approved, it shows as "Waiting for review" to the shop that
sent it and to no one else.

Storage is cheap; the limits are about the home desktop's disk and the
nightly backup, not about money.

## 1. How much storage

**How big a manual is.** No source we read lists file sizes, so these are
estimates to measure in 293's Step 0 with real files:

- A factory service manual or a Clymer/Haynes manual is about 300 to 900
  pages. As a PDF it is about 20 MB when it is the publisher's text, and
  50 to 150 MB when it is a scan.
- A parts catalog (exploded views) is about 100 to 400 pages, about 10 to
  60 MB.
- The library also keeps each page as an image for the zoom viewer, and a
  thumbnail. At about 200 to 400 KB a page, that adds about 100 to 300 MB
  for a 700-page manual.

So **one manual takes about 100 to 300 MB on our side**, and a 300 MB cap
per file covers almost every real manual.

**What it costs.** Backblaze B2, where the nightly backup already goes,
charges "$6.95 / TB / mo", with the "First 10GB storage is always free"
[1]. A full Company library of 50 GB costs about 35 cents a month to back
up. A full Shop library, about 14 cents. Money is not the limit.

**What is the limit.** Live runs on the home desktop
(`~/motodiag/live/`). 100 full shops would be 2 TB on that disk and in
every backup. Before 293 starts:

- **Step 1.** Measure the free space on the home desktop's disk.
- **Step 2.** Decide whether manual files go in the nightly backup (they
  are large and the shop still has its own copy) or in their own weekly
  backup. Recommended: their own weekly backup, so the database's nightly
  backup stays small and fast.

**Why these numbers.**

- **Individual, 2 GB:** a rider with up to 5 bikes needs a service manual
  and a parts catalog for each: 10 files. Enough, and cheap to hold.
- **Shop, 20 GB:** a shop working on many makes keeps manuals for the
  bikes it sees often. 100 manuals is a full shelf. Raise it when a real
  shop hits it, not before.
- **Company, 50 GB:** shared across its shops (up to 3 locations, from the
  pricing brief), so the same manual is not stored three times.
- **Over the limit:** the upload is refused with how much is used and how
  to free space. No automatic charge. An extra-storage add-on can come
  later if shops ask for it.

These sit beside the plan limits already in `cli/subscription.py`
`TIER_LIMITS` (users, locations, AI spend), as one new limit,
`manual_storage_bytes`, read from that one place.

## 2. The upload wording for the terms

The current terms (`docs/legal/terms.md`, version 1.0) say what the shop
puts in is the shop's, and that we may suspend an account that breaks the
terms. They say nothing about files a shop uploads that someone else
wrote. Proposed new section, after "The shop's data is the shop's", in
the terms' own plain style:

> ## Manuals and files you upload
>
> - **Only what you have the right to use.** Upload a manual, parts book
>   or other file only if you bought it, were given it by its publisher,
>   or otherwise have the right to use it in your shop. By uploading it you
>   tell us you do.
> - **It stays with your shop.** A file you upload is shown only to your
>   own shop's people (for a company, its own shops). We never show it to
>   another customer and never use it to build Mekno's own content.
> - **We check it first.** Every upload is checked before anyone can open
>   it, by our software and then by a person at Mekno, who sees the file
>   to do so. We may refuse or remove a file that is not a repair or parts
>   document, that does not match the bike it is tagged to, that is
>   damaged or unsafe, or that we have reason to think you may not use.
> - **If someone says it is theirs.** If a publisher or anyone else tells
>   us a file is theirs and you may not use it, we may take it down while
>   we look into it, and we tell you.
> - **It is a reference, not a promise.** A manual's figures are its
>   publisher's. Check torque values and procedures against the manual for
>   the exact bike; the mechanic decides and answers for the repair, as
>   these terms already say.

**My own review of this wording** (the operator asked for it):

- **"We check it first" must be true from day one.** If 293 ships without
  the review step, this sentence is wrong. The terms change and the
  review step ship together, or neither does.
- **It tells shops a person sees their files.** That is the price of
  "super verified", and the privacy policy must say it too (below).
  Shops' manuals are not customer data, but a shop may not expect a person
  to look.
- **"Reason to think you may not use" is deliberately loose.** We cannot
  prove a shop bought a manual. The real protections are: the shop's
  promise, private-to-the-shop storage (so we never redistribute), and
  taking a file down on a complaint. The lawyer should confirm this is
  enough, and whether a formal takedown address (a US DMCA agent) is
  worth registering.
- **The last bullet repeats the existing "the mechanic decides"** clause
  on purpose, next to torque values, where it matters most.
- **A terms change is a new version.** It goes in the next version of the
  terms (1.1 or 2.0) with the lawyer's read, and shops accept it before
  using manuals. 293 can require acceptance of the new version only for
  the manuals screens.

**Privacy policy, one sentence to add** (`docs/legal/privacy.md`, in the
next version):

> When you upload a manual or other file, a person at Mekno looks at it
> once to check it before your shop can open it.

## 3. The review step: "super verified"

Every upload goes through three gates. Nothing is visible to anyone but
the uploader until all three pass.

**Gate 1. The server checks it automatically, in seconds.**

- It is a real PDF (read from the file itself, not its name), under the
  size cap and within the plan's storage.
- It is not password-locked, and carries no embedded scripts, attachments
  or launch actions (PDFs can carry all three). Any of those: refused.
- A virus scan (ClamAV, free) finds nothing.
- Its pages render and its text extracts. A file that fails is refused
  with the reason.
- The same file (by fingerprint) already approved for this shop: not
  stored twice.

**Gate 2. A person at Mekno reviews it, before the shop can use it.**

The reviewer sees the first pages, the title page, the shop's tag (make,
model, years) and the shop's name, and answers four questions:

1. Is it a repair manual, parts book or wiring document?
2. Does it match the bike it is tagged to?
3. Is it readable (a usable scan, not blank or cut off)?
4. Anything that says it may not be the shop's to use? For example, a
   piracy site's watermark, or a "not for distribution" dealer document.

Then **Approve**, **Fix the tag** (and approve), or **Reject with a
reason** the shop sees. Every decision is recorded with who made it and
when. Target: reviewed within one working day. While shops are few, the
reviewer is the operator, from a simple list in the admin side.

**Gate 3. After approval, anyone in the shop can flag a page.**

A "Something wrong with this page" button sends it back to the review
list. A complaint from a publisher does the same, and takes the file down
until it is decided.

**Later: a review fleet.** The operator asked whether a fleet could
handle these. Yes, once volume needs it, shaped like the existing fleet:

- A **first-pass reviewer** (a model) reads each upload and fills in the
  four answers with its reasons, and flags anything doubtful.
- **A person still approves.** Like the fleet's rule that an agent never
  approves its own work, the model recommends and a person decides. Clear
  cases can be approved in a batch; doubtful ones are looked at one by
  one.
- **Only when the numbers show it is safe**, for example after a few
  hundred reviews where the model and the person agreed, could the
  operator decide to let clear cases through without a person. That would
  be its own decision, with the terms' "a person at Mekno" sentence
  changed first.

Not needed for 293. 293 builds gates 1 to 3 with a person reviewing.
The fleet is a later phase, when reviews take more than a few minutes a
day.

## What changes in 293's plan

Added to the plan outline in the 2026-11-20 brief:

- `manual_references.status` takes `pending_review`, `approved`,
  `rejected`, `taken_down` (a `Literal` at every contract boundary), plus
  `reviewed_by`, `reviewed_at`, `review_reason`.
- Every read route returns only `approved` files, except the uploader's
  own list, which shows its pending and rejected files with the reason.
- An admin-only review list and its approve, fix-tag and reject actions.
- Gate 1's checks, each with a test that a bad file is refused (a renamed
  .exe, a PDF with JavaScript, a locked PDF, an oversize file, a file over
  the plan's storage).
- The main test stays: another shop can never list, open or search a
  shop's file, approved or not.
- The plan's storage limit, read from `TIER_LIMITS`.

## Decisions for the operator

1. **Storage: 2 GB, 20 GB, 50 GB, and 300 MB a file?** Recommended: yes.
2. **Upload wording and the privacy sentence as drafted, to the lawyer's
   read?** Recommended: yes, shipped together with 293.
3. **Review: every upload approved by a person before use, you reviewing
   while shops are few, a review fleet later?** Recommended: yes.
4. **Manual files in their own weekly backup, not the nightly one?**
   Recommended: yes, after measuring the desktop's free disk.

## Sources

1. [Backblaze B2 pricing](https://www.backblaze.com/cloud-storage/pricing), read 2026-11-21.
2. [Honda Motorcycle Publications](https://www.hondamotopub.com/AHM): Honda sells service publications "for download in .pdf format"; sizes not stated.

File sizes in section 1 are estimates, not measured; 293's Step 0
measures them on real manuals before the caps are written into code.
