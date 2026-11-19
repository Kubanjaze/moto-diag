# Mekno's legal texts

Phase 334 (K84, the operator's words: "yes go with templates, and approve
both drafts"). Two texts a shop accepts, cut from a public template now; a
lawyer's review comes later, as a new version.

| file | what it is | published as |
|---|---|---|
| `terms.md` | the Terms of Service | `https://getmekno.com/terms/` |
| `privacy.md` | the privacy policy | `https://getmekno.com/privacy/` |

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

## A new version

1. Change the text, and the version line at the top of the file
   (`Version 1.1 — YYYY-MM-DD`; the privacy policy keeps its own number).
2. For the terms, set `TERMS_VERSION` and `TERMS_DATE` in
   `src/motodiag/auth/terms_acceptance.py` to the same version and date.
   `tests/test_phase334_legal_texts.py` fails until they agree.
3. Publish the file on getmekno.com in place of the old one.
4. Every user accepts again: an acceptance counts only for its own version.

## Publishing

The operator's site, getmekno.com, lies outside this repository. Each file
is published as a page at the address above; the server gives the two
addresses in `GET /v1/terms` (`MOTODIAG_TERMS_URL` and
`MOTODIAG_PRIVACY_URL` override the defaults). Nothing here publishes
anything.
