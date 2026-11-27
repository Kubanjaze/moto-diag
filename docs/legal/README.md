# Mekno's legal texts

Phase 334 (K84, the operator's words: "yes go with templates, and approve
both drafts"). Two texts a shop accepts, cut from a public template now; a
lawyer's review comes later, as a new version.

| file | what it is | published as |
|---|---|---|
| `terms.md` | the Terms of Service | `https://getmekno.com/terms/` |
| `privacy.md` | the privacy policy | `https://getmekno.com/privacy/` |

Both are at version 1.1, of 2026-11-23 (Phase 293; K119, K122): the terms'
"Manuals and files you upload" and the privacy policy's manuals line and
review sentence. Version 1.0 was 2026-11-19 (Phase 334).

The privacy policy is at **version 1.2, of 2026-11-27** (Phase 409, F311):
Cloudflare named in "The services it goes to", for the app's connection
through the tunnel, in the line the operator approved word for word on
2026-11-27. The terms stay at 1.1, so `TERMS_VERSION` is unchanged and no
one accepts again; the policy's line goes live on getmekno.com before the
tunnel does.

## The template

- **Name:** Basecamp's policies (the Terms of Service and the Privacy
  Policy of Basecamp, LLC).
- **Address:** https://github.com/basecamp/policies
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0),
  https://creativecommons.org/licenses/by/4.0/ — reuse and adaptation are
  allowed with attribution, which each file keeps in its last line.
- **Read:** 2026-11-19, from the template as the Chief Engineer knows it.
  The build's sandbox could not reach github.com that day (the request was
  refused at the proxy), so the licence line was not read from the
  repository itself. The handoff asks the operator to open the address
  once and confirm the licence line while reading the two texts.
- **Read from the repository:** 2026-11-21, before the pages went live
  (Phase 408). `LICENSE.md` is the "Creative Commons Attribution 4.0
  International Public License (CC BY 4.0)", and the README says the
  policies may be used under that licence with attribution. GitHub's
  licence label for the repository says "Other", because the file is the
  licence's text in Markdown.

## A new version

1. Change the text, and the version line at the top of the file
   (`Version 1.1 — YYYY-MM-DD`; the privacy policy keeps its own number).
2. For the terms, set `TERMS_VERSION` and `TERMS_DATE` in
   `src/motodiag/auth/terms_acceptance.py` to the same version and date.
   `tests/test_phase334_legal_texts.py` fails until they agree.
3. Publish the file on getmekno.com in place of the old one.
4. Every user accepts again: an acceptance counts only for its own version.

Version 1.1 (2026-11-23, Phase 293) went through these four steps, adding
the clause on uploaded manuals; a lawyer's read becomes a later version.

## Publishing

The operator's site, getmekno.com, is in this repository's `site/` since
Phase 408 (K106). Each file is built into a page at the address above by
`python scripts/site_build.py legal`, which writes `site/terms/index.html`
and `site/privacy/index.html` word for word from the two texts;
`tests/test_phase408_site.py` fails while a committed page is not the
build's output. The site goes live only when the operator uploads `site/`
to Cloudflare Pages by hand. The server gives the two addresses in
`GET /v1/terms` (`MOTODIAG_TERMS_URL` and `MOTODIAG_PRIVACY_URL` override
the defaults). Nothing in the repository publishes anything by itself.

Step 3 of "A new version" is therefore: run the build, commit the two
pages with the text, and upload `site/` from master.
