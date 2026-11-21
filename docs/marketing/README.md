# Mekno marketing

The record of Mekno's marketing, kept in the repository so it does not live
only in chats (K107, 2026-11-20). The operator's decisions are K-numbers in
`docs/decisions.md`, word for word; the standing marketing thread's brief is
`docs/prompts/marketing_thread.txt`.

## What lives here

- Each tool's audit, summarised and dated. The first, HeyCatch's of
  2026-11-20, is in the brief's "HeyCatch" section.
- Positioning, and copy once the operator approves it for the site or the
  app.
- Phase requests for the site or the app. The advisor turns each into a
  ROADMAP row and a prompt in `docs/prompts/`.

An approved draft reaches this folder through a pull request that adds only
that file, which the operator merges.

## What never lives here

This repository is public. So, never here:
- call lists, call notes and shop contacts: they go in a separate private
  repository, not `workspace-docs` (K107);
- any prospect's or customer's name;
- a personal phone number, address or email address (the public contact is
  support@getmekno.com);
- anything the operator said privately.

The founder's name and photo appear on the site's own pages, by K103, and
nowhere else here: K110 makes the operator's own full name and photo the
one exception to the brief's rule 8, on the site's pages in `site/` only.

## The standing rules (2026-11-20)

| | rule |
|---|---|
| K100 | **No tracking, no external scripts.** No script, no cookie and no SDK on the site; never in the app. Cloudflare's own counts are enough for now. The site's headers enforce it (`script-src 'none'`, and `form-action 'none'` until a form is decided). |
| K101 | **Signups.** The support email link stays for the first 10 shops. A form later: Cloudflare holds the signups and emails them to the operator, a privacy line goes into the texts first, and the form-action header changes on purpose. Never the Mekno server (K74), never the live database. |
| K102 | **Prices on the site now,** exactly pull request 62, under Individual, Shop and Company. Company reads "More than one shop? Talk to us" until locations exist (F282). The people and location limits are plan terms, not enforced. One honest line: early-access shops are set up by hand, and paying in the app comes with the payment screens (372B). |
| K103 | **The founder block:** full name, a real photo, one line. No phone number, no address; contact stays support@getmekno.com. |
| K104 | **HeyCatch:** nothing spent until the site fixes are live, then one 40-credit re-audit to measure the change. It lapses unless it books a real shop call before its intro period ends. |
| K105 | **Shops first, not shops only.** "Built for working shops" stays; "not for home garages" is never printed. |
| K106 | **The site's source moves into `site/` in this repository.** |
| K107 | **The record:** this folder for the brief, the HeyCatch summary, positioning, approved copy and phase requests; decisions as K-numbers; call lists, call notes and shop contacts in a new private repository. |
| K108 | **The name:** a free USPTO search on Mekno first, then the operator's own filing, before any paid ad or social account under the name. |
| K109 | **The order:** 334's step 2 (publishing the terms and privacy 1.0) before any public push; the "site basics and trust" phase on the Mac beside the fleet, after the marketing thread reports where the site's source lives and hands over its phase request (the thread drafts it, the advisor writes the row and the prompt); "early-access signups" waits until a form is worth having. |
| K110 | **The founder's name:** the operator's own full name and photo are the one exception to the brief's rule 8, on the site's pages in `site/` only. |
| K111 | **The privacy text:** version 1.0 gains, before it is published, its section "The website": "The website sets no cookies and runs no scripts. Cloudflare, which serves it, keeps standard request logs." |
| K112 | **The terms and privacy pages are published by the site phase.** A Cloudflare upload replaces the whole site, so 334's step 2 moves into the site phase: both pages built from `docs/legal/`, in its one upload. Stripe's links (334's step 3) follow that upload. |
| K113 | **Privacy stays 1.0,** and Cloudflare is not added to its list of services: the website section (K111) is enough. |
| K114 | **The site phase's four answers:** privacy stays 1.0; HSTS is the advisor's call, a year from the first upload, without `includeSubDomains` or `preload`; no price beside Company; www.getmekno.com redirects to getmekno.com. |

## Where it stands, 2026-11-21

- The standing thread is open in the home desktop's Ubuntu project, from
  the brief. Its first two jobs are done: the site measured, and the phase
  request for "site basics and trust" drafted. The request is here as
  `2026-11-20_site_basics_and_trust_request.md`, with the operator's name
  replaced (the brief's rule 8).
- The site's source is in no repository. It is on the Mac as one zip,
  getmekno-site.zip in the operator's Downloads folder: nine files and
  `_headers`, saved 2026-11-09, 48 minutes before the deployment. On
  2026-11-20 the advisor compared each file's sha256 with what
  getmekno.com served: all nine equal, and its `_headers` gives the five
  headers the site sends. The site is a Cloudflare Pages Direct Upload
  project, "getmekno": an upload replaces the whole site.
- The terms and privacy texts, version 1.0, are not yet published. The
  site phase publishes them (K112); Stripe's links follow
  (`docs/handoffs/2026-11-20_334_closed.md`, step 3).
- "Site basics and trust" is row 408, 🔲, built from
  `docs/prompts/408_the_sites_basics_and_trust.txt` by the advisor session
  on the Mac when the operator starts it. The operator answered the
  request's four questions in K114.
- "Early-access signups" waits until a form is worth having.
