> Committed by the advisor on 2026-11-21 from the operator's paste of the
> marketing thread's draft, version 8, with one kind of change and no other:
> the operator's name is replaced by "the operator" throughout, with "he",
> "his" and "him" to match, because the brief's rule 8 and K110 keep the
> name to the site's pages in `site/`. One sentence, quoting the operator on
> social media and a trademark filing (item 7), was left out of the first
> commit because it was not in `docs/decisions.md` and differed from K108;
> it is back since the operator recorded it the same day as K115. The
> operator answered the four open questions at its end in K114.

# Phase request for the advisor: site basics and trust (K109)

Draft by the Mekno marketing thread, version 8, 2026-11-20, for the operator's edit. The
advisor writes the row and the prompt. Measurements are from job 1 (live site read
2026-11-20 evening). Repository facts were checked at master 30dc540 (405 merged as
PR 80). The knowledge base is unchanged since edf9f04: 1057 rows in 110 files.

It rests on the operator's decisions K100 to K106 and K109 (docs/decisions.md at 30dc540):
no tracking and no external scripts (K100); prices now, exactly PR 62 (K102); the founder
block (K103); shops first (K105); the source into `site/` (K106); and the order (K109).
It also rests on two later decisions, which the advisor is recording tonight as K111
(the privacy text's sentence about the website) and K112 (the operator: "Yes, fold the terms
and privacy publishing into the site phase", item 14). Neither is on master at 30dc540
yet.
Early-access signups are not in this phase (K101, K109). They are kept apart in
`2026-11-20_later_early_access_signups.md`.

---

## Site basics and trust (collects nothing)

### What

1. **The source in git.** The Pages project `getmekno` is a Direct Upload with no git
   repository. It has had one deployment ever, 592d738e on 2026-11-09, which holds 9
   files: index.html, 404.html, robots.txt, styles.css, favicon.svg, and
   support/, terms/, privacy/ and thanks/ each with an index.html. There is no build
   command, no Functions, no environment variables and no bindings. (Read in the operator's
   dashboard on 2026-11-20.) **The source is on the Mac**, in the zip `~/Downloads/getmekno-site.zip`: the 9
   files plus `_headers`. A plain search missed it because the files are packed inside
   the zip. The advisor compared the zip with getmekno.com on 2026-11-20 and found every
   file identical, byte for byte. The phase repeats that comparison before it saves
   anything into `site/`, and keeps the zip until then. If the zip and the live site
   differ by then, the fallback is the deployment itself: the 9 files from its Assets
   page and `_headers` from its Headers tab. The first commit changes
   nothing and is checked byte for byte against the live site.
   **The headers come from a `_headers` file** uploaded with the site. It does not
   appear in the Assets list, but it does appear on the deployment's Headers tab, for
   `/*`: the CSP, X-Content-Type-Options nosniff, Referrer-Policy
   strict-origin-when-cross-origin, Permissions-Policy camera=(), microphone=(),
   geolocation=(), and X-Frame-Options DENY. The zone has no `_redirects`, no Transform
   Rules, no Snippets and no Worker routes. (Read in the operator's dashboard on 2026-11-20;
   nothing was changed.) So `site/` holds 10 files: the 9 plus `_headers`, copied from
   the Headers tab exactly. Then make the changes below as separate commits.
2. **HSTS** in `_headers`: `Strict-Transport-Security: max-age=31536000`. No
   `includeSubDomains` and no `preload` until the operator says so. A short max-age first
   (for example 300 for a week), then the year, is the safer order. That choice is the
   advisor's to put to the operator.
3. **A self-referencing canonical** on every indexable page, using the apex https
   address with a trailing slash (`https://getmekno.com/`, `/support/`, `/terms/`,
   `/privacy/`). This is needed because www.getmekno.com and getmekno.pages.dev both
   serve the same pages with no redirect. /thanks/ and the 404 page stay `noindex` and
   get no canonical.
4. **sitemap.xml** listing the four indexable pages with a lastmod element set to the date each
   page's file last changed in git. Add `Sitemap: https://getmekno.com/sitemap.xml` to
   robots.txt. Keep `Disallow: /thanks/`. /thanks/ is never listed in the sitemap.
5. **Titles of 30 to 60 characters and descriptions of 110 to 160.** Today only the home
   title fits. The home description is 174 characters and the other pages' are 19 to
   55. Proposed text (character counts in brackets):
   - Home: title unchanged "Mekno · Know what's wrong before you wrench" [43].
     Description "Mekno is a diagnostic assistant for motorcycle shops. Enter the
     symptoms and codes, and it lists likely causes for that bike and what your tech
     checks first." [157]
   - Support: "Support · Mekno, diagnostics for motorcycle shops" [49]. "How to reach
     Mekno: email support@getmekno.com, and a person reads every message. Help with
     your plan, a payment to a shop, or the data we keep about you." [154]
   - Terms: "Terms of Service · Mekno, for motorcycle shops" [46]. "The terms for using
     the Mekno app and getmekno.com: your account, the diagnostic suggestions,
     subscriptions, payments to shops and the limits on our part." [154]
   - Privacy: "Privacy policy · Mekno, for motorcycle shops" [44]. "What Mekno keeps,
     why, which services it goes to, how long it is kept, and how a shop takes its data
     out or has it deleted. The shop's data is the shop's." [154]
   The terms and privacy descriptions must match the 1.0 texts once they are published
   (334's step 2), so check them again then.
6. **Open Graph tags** on the four pages: og:title, og:description, og:url (the same as
   the canonical), og:type website, og:site_name Mekno. For og:image, use a plain
   1200×630 PNG of the logo and the name, with no product claim. Real app screens can
   replace it later.
7. **Organization JSON-LD** on the home page: name Mekno, url, logo, email
   support@getmekno.com. No `sameAs` until real profiles exist. (the operator, 2026-11-20: free social media only, with no trademark filing for now. Once a profile exists, and the operator OKs it, its address goes in `sameAs`.) Add `founder` only if
   item 9 goes ahead.
8. **The FAQ** (on the home page or at /faq/): accuracy, who stays in charge,
   shop-software fit and data ownership. The text comes from the marketing thread's job
   4 draft, as the operator edits it. The data answers quote privacy 1.0, so the FAQ goes
   live together with 1.0 or after it.
9. **The founder block** (K103): the operator's full name, a real photo, one line, no phone
   number, no address. Contact stays support@getmekno.com. Text from job 4; the operator fills
   in the name and photo. The operator's own name and photo are the one exception to rule 8 (the
   operator's words, 2026-11-20).
10. **An honest early-access line** in place of the current "Want to try it in your shop
    first?" line. Something like: "Mekno is in early access. We set up each early-access
    shop by hand. Paying in the app comes later, with the app's payment screens. Email
    support@getmekno.com to try it in your shop." The two "Coming soon" store badges
    stay as they are.
11. **Prices** (K102), on the home page, under the three names from 404's handoff,
    with the figures from PR 62's report:
    - **Individual: for your own bikes**, $19 a month.
    - **Shop**, $99 a month.
    - **Company**: "More than one shop? Talk to us", with no price and no checkout (F282:
      locations are not built). This follows the operator's brief. If the operator wants $299 shown
      beside it, the operator should say so.
    Monthly only, no yearly prices (PR 62). K102: people and location limits are shown
    as the plan's terms, not as limits the app enforces (F282: no code keeps them). Per
    the report's table, the limits the code does keep are diagnoses a month (50 / 500,
    in session_repo.py) and video and voice-note uploads (0 / 200, in the upload
    routes). The phase measures each limit again at its own commit before printing it.
    The early-access line in item 10 is K102's "one honest line".
12. **Product schema** for the two priced plans only: SoftwareApplication or Product, with
    offers in USD, a monthly unit, and the price. Never aggregateRating, review or
    ratingCount. Without a rating, Google will probably not show it as a rich result.
    That is acceptable, and is no reason to add a rating.
13. **The "Hears the problem" card.** It says "Mekno compares it with how that engine
    should sound". At edf9f04, a `git grep` finds no API route that calls the engine
    sound library (src/motodiag/media/sound_signatures.py, spectrogram.py,
    anomaly_detection.py). What the app reaches is voice notes, turned into text
    (transcripts.py, OpenAI Whisper per privacy 1.0), and video frames sent to the AI
    (videos.py, analysis_worker.py). The phase should either confirm a live path that
    does the comparison or rewrite the card to what the app does: "Record the bike on
    your phone. Mekno reads the symptoms out of your voice note and looks at the video
    with you." No accuracy claim.
14. **Terms and privacy 1.0 published** (334's step 2, folded into this phase by
    the operator on 2026-11-20: "Yes, fold the terms and privacy publishing into the site
    phase"). This is the order K109 sets: the 1.0 pages go live no later than anything
    else in this phase. They are never published after the FAQ or the prices.
    - **First, the website sentence in docs/legal/privacy.md** (K111): "The website
      sets no cookies and runs no scripts. Cloudflare, which serves it, keeps standard
      request logs." It goes in as its own short section, "The website", in the
      advisor's record for tonight. It is not on master at 30dc540 yet. "The services
      it goes to" does not change: that list is where the shop's data goes, and the
      website sends none of it to Cloudflare. (One thing for the advisor to weigh:
      mail to support@getmekno.com passes through Cloudflare's mail routing, per the
      domain's SPF record, and a shop may write its data into an email. Only the operator
      can say whether that belongs in the list.)
    - **The version stays 1.0** unless the operator says otherwise; the question is with the operator.
      1.0 was never published, and no code carries a privacy version: the server knows
      only the terms version. The terms text does not change, so `TERMS_VERSION` and
      `TERMS_DATE` in src/motodiag/auth/terms_acceptance.py stay as they are.
    - **Then** `site/terms/index.html` and `site/privacy/index.html` are rebuilt from
      docs/legal/terms.md and privacy.md at a named commit, in the site's own markup and
      style. Each keeps its last line naming Basecamp and the CC BY 4.0 licence. The
      "Last updated: November 9, 2026" lines go, and each page shows its version line.
    - **The operator's own step** from 334's handoff, done before the deploy: open
      https://github.com/basecamp/policies once and confirm that the licence says
      CC BY 4.0. If it says something else, the phase stops.
    - **The addresses stay** `https://getmekno.com/terms/` and `/privacy/`, so the
      server's `terms_url` and `privacy_url` defaults stay right (config.py at master
      30dc540), and no setting changes.
    - **docs/legal/README.md, "Publishing"** says the site lies outside the repository.
      After K106 it doesn't, so that sentence is updated to name `site/`.

### What it must not do

- Add no script tag that runs, no form tag, no cookie, no external font, image, style or
  script, no analytics and no tracking pixel. The JSON-LD blocks
  (`type="application/ld+json"`) are the only script tags allowed. They are data,
  and the browser does not run them under `script-src 'none'`.
- Change no header except adding HSTS. The CSP stays exactly as today, byte for byte,
  `form-action 'none'` included. X-Frame-Options, nosniff, Referrer-Policy and
  Permissions-Policy stay too.
- Leave /thanks/ unchanged byte for byte. It is the Stripe return page for the six
  return settings (K74, Phase 402: `MOTODIAG_STRIPE_RETURN_PAGE_URL`). Nothing new links
  to it or reuses it.
- No "MotoDiag" anywhere in `site/` (K77). The only email address is
  support@getmekno.com. No phone number. No name of a shop, a prospect or a person,
  except the founder's own (the operator's exception to rule 8).
- No count, accuracy figure, rating, review, quote or comparison with another product.
  If a count is wanted later, it comes from the knowledge base at a named commit with
  its command (for example: 1057 known-issue rows in 110 files at edf9f04).
- Nothing against home riders (K105). "Built for working shops" stays.
- Nothing goes live before the operator's word. Terms and privacy 1.0 go live first, or in
  the same deploy (item 14, K109).

### How it is checked

- **Byte for byte first.** After the first commit, every file in `site/` equals what the
  live site serves (`curl` each path and compare). `_headers` reproduces today's
  response headers, apart from Cloudflare's own (cf-ray, NEL, Report-To, alt-svc).
- **Headers read back** after the deploy: on every page, robots.txt, sitemap.xml and the
  404 page, the CSP equals today's string exactly, HSTS is present with the agreed
  max-age, and no Set-Cookie header appears.
- **The no-script test** (a test in moto-diag over `site/`): no script tag except
  `type="application/ld+json"`, no form tag, no `on*=` attributes, no javascript-scheme
  URLs, no `src` or `href` to another host except mailto:support@getmekno.com, the
  canonical and OG addresses on getmekno.com, and the Stripe Connected Account
  Agreement link already in the terms. Every JSON-LD block parses as JSON and has no
  rating or review keys.
- **Words:** no "motodiag" in any case; no email except support@getmekno.com; nothing
  that looks like a phone number; titles 30 to 60 and descriptions 110 to 160 on the
  four pages; each price equals PR 62's report; "not for home garages" absent.
- **Links:** every internal link resolves in `site/` and answers 200 live. Every
  sitemap URL answers 200 and equals its page's canonical. robots.txt has the Sitemap
  line and still disallows /thanks/. /thanks/ is in neither the sitemap nor any link.
- **/thanks/ unchanged:** its bytes equal today's.
- **Terms and privacy:** the visible text of the live /terms/ and /privacy/ pages,
  stripped of markup, equals docs/legal/terms.md and privacy.md at the named commit,
  word for word. Each page shows its version line and the Basecamp / CC BY 4.0 line.
  "November 9, 2026" appears on neither. tests/test_phase334_legal_texts.py still
  passes. `GET /v1/terms` on the server still gives the two addresses, and both answer
  200.
- **Order:** the 1.0 pages are live before, or in the same deploy as, the FAQ, the
  prices and the founder block.
- **One HeyCatch re-audit** (40 credits) after it is live, if the operator asks, to measure the
  change. This thread does not run it.

### Settled, and still open

- **Settled: the founder's name in the repository.** The operator's own name and photo are the
  one exception to rule 8 (2026-11-20).
- **Settled: deploying as today, by Direct Upload.** Each deploy uploads `site/` at a
  named commit, on the operator's word: drag and drop in the dashboard, or `wrangler pages
  deploy site --project-name getmekno` from a computer the operator signs in on. The project is
  not connected to GitHub. After each deploy, the headers are read back and the live
  files are compared with `site/` at that commit.
- **Settled: HSTS goes in `site/_headers`,** under `/*`, beside the other five, not in the
  dashboard's SSL/TLS settings, so the file stays the one record of what the site sends.
- **Settled: the website sentence in privacy 1.0** (K111, item 14).
- **Open: privacy 1.0 or 1.1.** With the operator; the recommendation is 1.0.
- **Open: HSTS max-age.** Start short (300 seconds for a week) or go straight to a year.
  The advisor puts this to the operator.
- **Open: $299 beside Company.** The operator's brief says "talk to us" with no price, and the
  draft follows it unless the operator says otherwise.
- **Open: www and pages.dev.** Redirecting www.getmekno.com to the apex is a Cloudflare
  redirect rule that the operator sets in the dashboard, not in `site/`. The canonical covers
  it for now.
