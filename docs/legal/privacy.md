# Mekno Privacy Policy

Version 1.2 — 2026-11-27

This policy says what Mekno keeps, why, which services it goes to, how long
it is kept, and how a shop takes it out or has it deleted. It is part of
Mekno's Terms of Service, at https://getmekno.com/terms/. "Mekno", "we" and
"us" mean the business that runs Mekno; "the shop" means the repair business
an account belongs to.

## What we keep

- **Accounts:** each user's name, username, email address, a scrambled form
  of their password (never the password itself), their logins and API keys
  (kept only as a scrambled form), and the phone's notification token if
  they turn notifications on.
- **Shops:** the shop's name and details, its staff and their roles.
- **The shop's customers:** their names and phone numbers, and anything else
  the shop types in about them.
- **Bikes:** make, model, year, VIN, mileage and notes.
- **The work:** work orders, intakes, parts, time on each job, invoices and
  their payments.
- **Diagnoses:** the symptoms and fault codes entered, the questions asked
  and the answers Mekno gave.
- **Photos, videos and voice notes** the shop uploads, and the text made
  from them.
- **Manuals and parts books** the shop uploads, the page images and the
  text made from them, and who uploaded, reviewed, flagged or removed each
  one.
- **Subscriptions:** which plan, its status and its renewal date. Card
  details stay with Stripe; we never see a full card number.
- **An activity log:** who made each change in the shop, when, and to what.

## Why we keep it

To run the service for the shop and nothing else: to show the shop its own
records, to answer its diagnostic questions, to work out its invoices, to
take its subscription's payment, to send the notifications it asked for, to
keep a copy safe against a failed disk, and to find and fix what breaks. We
do not sell anyone's data, and we do not use it for advertising.

A person at Mekno looks at each manual a shop uploads before the shop can
open it, and again when someone in the shop flags a page or a publisher
complains.

## The services it goes to

Mekno sends data to these services, and only for the reason given:

- **Stripe**, for payments: a subscriber's email address and plan, and a
  shop's card payments from its customers. Stripe takes the card details
  itself.
- **Anthropic**, for the AI's answers: the symptoms, fault codes, bike
  details and questions of a diagnosis, the photos and video frames sent for
  analysis, and the text of a voice note when Mekno reads the symptoms out
  of it.
- **OpenAI**, for voice transcription (its Whisper service): the audio of a
  voice note the shop uploads, to turn it into text.
- **Sentry**, for crash reports: when the server fails, the kind of error,
  its message with every login token, email address and phone number blanked
  out, where in the code it happened, the route's pattern and the response's
  status. The message is the one free-text part, so a name or a VIN in it
  would be sent. Sentry also receives the timing of one request in ten.
- **Backblaze**, for the offsite backup: an encrypted copy of the database
  and of every upload, each night. It is locked with a passphrase before it
  leaves our machine, so Backblaze stores bytes it cannot read.
- **Apple**, for notifications to an iPhone: the phone's notification token
  and the notification's text.
- **NHTSA**, the US road-safety agency, for recall and VIN lookups: a bike's
  VIN, or its make, model and year.
- **Cloudflare**, for the connection between the app and Mekno's server:
  every request the app sends passes through Cloudflare, which opens it to
  deliver it and keeps standard request logs.

## The website

The website sets no cookies and runs no scripts. Cloudflare, which serves
it, keeps standard request logs.

## How long it is kept

- **While the shop uses Mekno,** for as long as its account is open.
- **When a shop asks for deletion,** its data is deleted from the service.
- **The encrypted nightly backups** are kept with no end date, and are
  opened only to restore the service after a failure. A shop's data deleted
  from the service stays in the encrypted copies made before the deletion.
- **Crash reports** are kept by Sentry for the period of its own retention.

## Taking it out, or having it deleted

The shop's data is the shop's. A shop that leaves can take its data out, and
a shop can ask for it to be deleted: ask through the support page, below.
We send a copy in a format other software can read, and we tell the shop
when the deletion is done. Records the law requires the shop to keep, such
as its invoices, are the shop's to keep: take a copy out before asking for
deletion.

## Changes

A new version of this policy has a new number and date at the top. If a
change matters to what we keep or where it goes, we tell users in the app
before it applies.

## Contact

Questions about privacy go through the support page,
https://getmekno.com/support/.

---

Adapted from Basecamp's policies (https://github.com/basecamp/policies), used under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
