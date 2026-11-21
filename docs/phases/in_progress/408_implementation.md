# Phase 408 — The site's basics and trust, with the terms and privacy published

**Version 1.1, 2026-11-21.** Built in the operator's project thread (the
operator, 2026-11-21: "do this as a thread or in this project so we keep it
altogether"; K118), on the local branch `phase-408-the-sites-basics-and-trust`
from master `4b71dac`, pushed as `phase-408-thread-build` (Deviations, 3).
Classification: **extension** (`408_step0.md`). v1.0 was committed
(`be1ebf0`) before any file under `site/`, `scripts/` or `tests/`; its push
waited for the operator's word (Deviations, 4).

## Goal

getmekno.com's source is in the repository, in `site/`, held by tests that
read only `site/` and `docs/legal/`. The site gains what the request's 14
items ask (HSTS, canonicals, a sitemap, titles and descriptions, Open
Graph, Organization and Product data, the FAQ, the founder block, the
early-access line, the prices, the "Hears the problem" card rewritten, and
the terms and privacy 1.0 pages built from `docs/legal/`), and nothing the
request forbids. The phase ends with a pull request the operator merges,
and a handoff whose steps the operator follows to upload `site/` from
master by hand. Nothing goes live in this phase.

## The plan of record

408 runs beside the 'Next, in order' list (row 408, K109): the fleet does
not wait for it, and it does not wait for the fleet. The fleet cannot build
it: the upload and the redirect are the operator's, in Cloudflare's
dashboard. The prompt and `docs/decisions.md` win where the request
differs (K113, K114): privacy stays 1.0 with no Cloudflare in its list of
services; HSTS is `max-age=31536000`, no `includeSubDomains`, no `preload`;
Company has no price on the page or in the Product data; www is the
operator's dashboard redirect.

## Logic

### 1. The source, unchanged (first commit under `site/`)

The 10 files of `~/Downloads/getmekno-site.zip`, copied as they are into
`site/` (Step 0 S0-2: all nine served files equal the live site by sha256,
and `_headers` equals the live response headers). The commit changes
nothing else, and its test pins the ten sha256 values of S0-2 at that
commit; later commits move the pins only for the files they change, and
`thanks/index.html` never moves.

### 2. `site/` holds only what is served

The served set after the phase: `_headers`, `index.html`, `404.html`,
`robots.txt`, `sitemap.xml`, `styles.css`, `favicon.svg`, `og.png`,
`logo.png`, `support/index.html`, `terms/index.html`, `privacy/index.html`,
`thanks/index.html`, and the founder's photo (`founder.jpg`) if the
operator gives one. A test fixes the set: any other file fails. The
scripts that build pages and images live in `scripts/`, the tests in
`tests/`.

### 3. HSTS (item 2)

One line added under `/*` in `site/_headers`:
`Strict-Transport-Security: max-age=31536000`. The other five lines stay
byte for byte; a test holds the file to exactly those six lines.

### 4. Each indexable page's head (items 3, 5, 6)

On `/`, `/support/`, `/terms/` and `/privacy/`: a self-referencing
`<link rel="canonical" href="https://getmekno.com/…/">`; a title of 30 to
60 characters and a description of 110 to 160, the request's text unless
the operator changes it; `og:title`, `og:description`, `og:url` (equal to
the canonical), `og:type` website, `og:site_name` Mekno, `og:image`
`https://getmekno.com/og.png`. `/thanks/` is unchanged and `404.html` keeps
its `noindex`; neither has a canonical.

### 5. The sitemap and robots.txt (item 4)

`site/sitemap.xml` lists the four canonicals, each with `<lastmod>`, the
date its page file last changed in git, written by
`scripts/site_build.py sitemap`. `robots.txt` keeps `Disallow: /thanks/`
and gains `Sitemap: https://getmekno.com/sitemap.xml`.

### 6. The images

`site/og.png` (1200×630) and `site/logo.png` (512×512): the logo mark from
`favicon.svg` and the name, drawn by `scripts/site_images.py` with Pillow,
which is not a project dependency (the script is run once, by hand, from
its own environment, and says so). No product claim. Every image in
`site/` carries no metadata: a PNG holds only `IHDR`, `PLTE`, `tRNS`,
`IDAT` and `IEND` chunks, a JPEG no `APP1`–`APP15` segment (no Exif, no
XMP, no location, no camera) and no comment. The founder's photo goes
through the same script's `photo` command, which re-encodes the pixels
only.

### 7. JSON-LD on the home page (items 7, 12)

Two `<script type="application/ld+json">` blocks, the only script tags in
`site/`: an Organization (name, url, logo, email support@getmekno.com, no
`sameAs`, `founder` only once the founder block is in), and a
SoftwareApplication whose `offers` are the two priced plans, Individual at
19.00 USD and Shop at 99.00 USD, each with a monthly
`UnitPriceSpecification`. No rating or review key.

### 8. The home page's words (items 8–11, 13)

- **Prices** (item 11): Individual: for your own bikes, $19 a month; Shop,
  $99 a month; Company, "More than one shop? Talk to us" with a mailto
  link and no price. Each plan lists the limits of S0-3; people and
  locations are said as plan terms, never as something the app counts.
- **The early-access line** (item 10, K102), in place of "Want to try it
  in your shop first?".
- **The "Hears the problem" card** (item 13) says what the app does with a
  voice note and a video, with no accuracy claim.
- **The FAQ** (item 8): the four answers of the marketing thread's job 4
  draft, as the operator edits them, on the home page under `id="faq"`. The
  data answer quotes privacy and terms 1.0 word for word; the accuracy
  answer says only what the phone app shows (a confidence and a severity
  for each diagnosis, `SessionDetailScreen.tsx`'s `DiagnosisCard`).
- **The founder block** (item 9, K103, K110): the operator's full name, one
  line and a photo, from the operator (2026-11-21, "yes yes yes", the third
  to the name and the line), above the FAQ under `id="founder"`, and
  `founder` in the Organization data. The photo is the operator's own file
  from the Mac's Downloads, re-encoded by `site_images.py photo` (400×400,
  no Exif).
- **The top paragraph** says "add a voice note or a video" in place of
  "record how it sounds", for the reason the card changes (S0-3); the
  operator approved it with the rest.

Every sentence a visitor will read that is new or changed is shown to the
operator in plain words, before and after, and nothing goes up without the
operator's yes.

### 9. The terms and privacy pages (item 14)

`scripts/site_build.py legal` renders `docs/legal/terms.md` and
`docs/legal/privacy.md` into `site/terms/index.html` and
`site/privacy/index.html`, in the site's own header, footer and styles:
`#` becomes the `h1`, the version line a `p.updated`, `##` an `h2`, a `- `
list a `ul`, `**…**` a `strong`, a paragraph a `p`, the `---` rule an `hr`.
A getmekno.com address becomes a link to itself; any other address stays
plain text, so no new outside host is linked (the Basecamp and licence
addresses are read, not clicked). The "Last updated: November 9, 2026"
lines go. A test proves the committed pages equal the script's output, and
that each page's visible text, stripped of markup, equals its Markdown's
words. `docs/legal/README.md`'s "Publishing" names `site/`.

## Rule-1 stops anticipated

- **A login:** the upload, the www redirect and any `wrangler` use are the
  operator's, by hand, on the operator's own Cloudflare login.
- **The licence:** the operator opens https://github.com/basecamp/policies
  once before the upload; if it does not say CC BY 4.0, the phase stops.
- **A header change** beyond the HSTS line is a stop.
- **Copy:** words the operator has not approved are not uploaded.

## Tests

`tests/test_phase408_site.py`, reading `site/` and `docs/legal/` only, never
the network, in every suite:

1. the served set (Logic 2);
2. `_headers` is the five lines of S0-2 plus HSTS, the CSP byte for byte;
3. `thanks/index.html` keeps its sha256;
4. no script tag but `application/ld+json`, no form, no `on*=` attribute, no
   `javascript:` URL, no `src` or `href` to another host than getmekno.com
   except `mailto:support@getmekno.com`;
5. each JSON-LD block parses, holds no rating or review key, and its offers
   are 19.00 and 99.00 USD only;
6. the words: no "motodiag" in any case, no email but support@getmekno.com,
   nothing like a phone number, no "not for home garages", no 299, titles
   30–60 and descriptions 110–160 on the four pages;
7. the canonicals and the Open Graph tags; `/thanks/` and the 404 page have
   `noindex` and no canonical;
8. the sitemap: its four addresses equal the canonicals, each `lastmod` a
   date; in a full clone, the date the page last changed in git; robots.txt
   has the Sitemap line and the `/thanks/` disallow; no page links
   `/thanks/`;
9. every internal link and asset resolves to a file in `site/`;
10. the terms and privacy pages equal `site_build.py`'s output, their text
    equals the Markdown's, each shows its version line and the attribution,
    and neither says "November 9, 2026";
11. every image has no metadata, and the two images have their sizes;
12. the card's old sentence is gone; `docs/legal/README.md` names `site/`.

13. the founder block is whole (photo, name, line, `founder` in the data) or
    absent.

69 tests in all (68, and one more image check for the photo).
`docs/phases/in_progress/408_mutate.py` plants one break per check and
requires each to go red: 32/32. `COLLECTED_TEST_FLOOR` 13031 → 13100 by a
diff of collected ids (+69 −0).

## Non-goals

- No upload, no dashboard change, no redirect: the handoff hands the
  operator those steps.
- No change to `docs/legal/`'s texts (K113), to `TERMS_VERSION` or to any
  server setting.
- No signup form (K101), no analytics, no `sameAs` (K108 stands).
- No HeyCatch re-audit unless the operator asks (K104).

## Deviations

1. **Built as a project thread, in a cloud checkout,** not a session on the
   Mac (the operator's words above). The container cannot reach
   getmekno.com, so Step 0 read the live site through the Mac's built-in
   browser pane and the zip through a read-only grant of the Mac's
   Downloads. The www, http and pages.dev measurements were not repeated
   in Step 0; the handoff's read-back measures them after the upload.
2. **The checkout's test environment** needed master's whole history, the
   extras, a sibling clone of the mobile repository and FastAPI 0.135.0
   (`408_phase_log.md`). The unbounded `fastapi>=0.110` is F287.
3. **A second builder.** The advisor recorded K117 ("build 408 on the
   Mac") at 12:36 EST and pushed its own Step 0, v1.0 and a build to
   `phase-408-the-sites-basics-and-trust`. This thread found it when its
   first push was refused, pushed nothing to that branch, and pushed its
   own work as `phase-408-thread-build`. The operator chose this thread on a
   decision card at 13:17 EST; the advisor stopped and recorded K118,
   undoing K117. This branch takes nothing from the advisor's.
4. **Pushes waited for the operator's word** (the coordinator's brief: any
   push needs it). v1.0 was committed first and pushed with the build,
   after "yes yes yes" at 13:10 EST.
5. **Commits.** The terms and privacy pages went in before HSTS (item 14
   first, K109's order); the heads, sitemap, images and home page are one
   commit, not one each, because their tests share one file.
6. **Words beyond the request,** each shown to the operator before and
   after and approved: the top paragraph; the accuracy answer cut to what
   the app shows; the data answer's "below" left out of its quote (the
   support page is not below it on the home page), its two sentences
   quoted apart; the terms description, because terms 1.0 has no
   "payments to shops" section; Company's line "Email
   support@getmekno.com and we will work out a plan with you"; the
   prices' footnote.
7. **The www redirect** is one Redirect Rule in the zone, not Bulk
   Redirects: one rule, on the domain the operator already opens; the
   prompt allows either. The dashboard's labels were not read by this
   thread; the handoff says to stop if a screen differs, and the read-back
   checks the outcome.
8. **The guards.** This thread's session did not start at the repository
   root, so the edit and push guards may not have fired. `wholetree.sh` ran
   by hand before every commit and passed each time.
9. **The regression of record** ran on the Mac (Results): the cloud run
   cannot pass the tests that need macOS or the fleet's fence (bwrap,
   osacompile, the Subconscious login).
10. **Bug fix #1** is a test on master that the date 2026-11-21 broke; it
    is fixed here because the regression of record must be green.

## Results

- `site/`: 14 files: the deployment's 10, of which `thanks/index.html`,
  `404.html` and `favicon.svg` are unchanged, and `sitemap.xml`, `og.png`,
  `logo.png` and `founder.jpg`.
- `scripts/site_build.py` (legal, sitemap, check) and
  `scripts/site_images.py` (brand, photo).
- `tests/test_phase408_site.py`: 69 tests; mutations 32/32 red
  (`408_mutate.out`).
- `wholetree.sh --full` at `2164c64`: 5425 passed, 37 skipped, exit 0, in
  the cloud checkout. A full run there at the same commit: 13006 passed,
  5 failed, 38 errors, all in tests that need macOS or the fleet's fence,
  and bug fix #1's test.
- REGRESSION_RESULT
- F287 filed. No migration, no live change: the upload is the operator's.

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-11-21 | the plan, before any code |
| 1.1 | 2026-11-21 | as built: the founder block, the top paragraph, Deviations and Results |
