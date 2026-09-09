# Adversarial research lenses — the canonical prompts

**Status:** canonical from Phase 242B (2026-09-09). Any phase running a
research sweep uses these lenses verbatim rather than re-deriving them.

Track K established that findings need verification — roughly 60% of its
closure audit's findings did not survive a second agent. Phase 242 established
the layer below that: **a verifier applying the wrong standard fails silently
and looks rigorous while doing it.**

## The failure this document exists to prevent

Phase 242's research swept 75 unique claims about Zero Motorcycles across five
finders and judged each on three lenses. Twenty-nine survived. Every single one
was `manufacturer-document`. Zero recall claims, zero owner-community claims.

That was not a clean corpus. It was a broken filter. The figure lens had been
written as:

> every number must trace to a named Zero Motorcycles document

which is the correct standard for a manufacturer claim and the wrong one for
every other evidence class. A recall record's model years, build windows and
unit counts come from the **regulator**, not from the manufacturer. The lens
therefore could not pass any regulator or community claim that contained a
number, and it refuted all thirty-five of them.

**The only visible symptom was the shape of the result** — one source class at
100%. The individual verdicts all read as careful work, because they were: the
verifiers opened sources, quoted them, and applied the standard they were
given. The standard was wrong.

A repair run under a source-class-aware standard recovered eleven claims,
eight of them recalls, including two stop-riding campaigns. Every one came back
with a substantive correction the first pass would have shipped wrong.

**Diagnostic to run on any sweep result before using it:** group the survivors
by `source_class`. If one class is at or near 100%, suspect the lens before
believing the corpus.

## Lens 1 — source

> REFUTE this claim on the SOURCE lens. Claim: "{claim}". Stated source_class:
> {source_class}. Document: {document_name}. URL: {source_url}. Evidence
> excerpt: "{evidence_excerpt}".
>
> Load WebFetch via ToolSearch and OPEN the source. Refute if: the document or
> page does not exist; it exists but does not say this; or the source_class is
> overstated — a forum post or aggregator labelled `manufacturer-document`, a
> dealer page labelled `regulator-record`. If you cannot open it,
> `refuted=true`. If the claim is nearly right, supply `corrected_claim`.

## Lens 2 — figure attribution (the corrected lens)

Apply **the standard that matches the claim's `source_class`**. Applying one
standard to all classes is the Phase 242 bug.

> REFUTE this claim on the FIGURE-ATTRIBUTION lens. Claim: "{claim}".
> source_class: {source_class}. Document: {document_name}. URL: {source_url}.
> Figures: {figures}.
>
> - `manufacturer-document`: every figure must trace to the named manufacturer
>   document. A number from a spec roundup, a review, an aggregator or a forum
>   is NOT attributed.
> - `regulator-record`: figures come from the REGULATOR, not from the
>   manufacturer. Build-date windows, affected-unit counts, campaign filing
>   dates and model years are attributed if the regulator record states them
>   and you can open it. **Do NOT refute because the manufacturer did not
>   publish the figure** — that is the bug this standard fixes.
> - `community-report`: figures are OWNER-REPORTED observations, not
>   specifications. They are attributable as "owners report X" and are not
>   refuted for lacking a manufacturer document. Refute only if the figure is
>   presented as though it were a manufacturer specification, or if no owner
>   source actually reports it.
>
> SEPARATELY AND ABSOLUTELY, for every class: refute if the claim text contains
> a recall or campaign REFERENCE NUMBER of any format (NHTSA-style `25V-123` or
> `25V123456`, `RM/2018/049`, `R/2024/123`, "Recall 1234567", a Part 573 report
> identifier, or a manufacturer campaign code). Campaigns are described by
> MECHANISM only — the Phase 231 decision, which holds across every track. Set
> `campaign_number_present`. A bare model year, a build-date window or a unit
> count is NOT a reference number.
>
> Split every figure into `figures_safe_to_print` and `figures_to_withhold`, so
> the entry knows which numbers it may state and which it must withhold with
> the absence stated. **When in doubt about a figure, withhold it.**

### Why the split matters

The `figures_safe_to_print` / `figures_to_withhold` split was added in the
repair run and earned its place immediately. It catches the figure that is
*honestly sourced but dangerous to print*: an owner-reported "600 miles" is a
true observation and also the archetypal first-service interval, so a mechanic
reading it beside a firmware warning may act on it as a threshold. A verifier
that only says refuted/not-refuted cannot express that. Withheld figures become
a stated absence in the entry, per the Phase 224/234 rule.

## Lens 3 — scope

> REFUTE this claim on the SCOPE lens. Claim: "{claim}". Topic: {topic}.
>
> Is this specific to the subject of this phase — its parts, procedures,
> failure patterns, generation changes, recalls, tooling? Or is it a generic
> explanation that would be true of any machine of this type, and therefore
> belongs to the phase that owns that system? Generic content is refuted here.
> Also refute if the claim is so vague a mechanic could not act on it. Default
> to refuted if uncertain.

## Rules that apply to every lens

- **Refuted by default.** Uncertainty resolves to refuted, never to survived.
- **A claim survives only if no lens refutes it.** Majority voting is for
  redundant refuters on one question; these three ask different questions and
  each is independently disqualifying.
- **Open the source.** A claim the verifier did not open is not verified.
- **`corrected_claim` is the valuable output.** In Phase 242 every one of the
  eleven recovered claims came back corrected on substance — a remedy that was
  a module return rather than a sealing operation, a consequence the original
  had missed. Wire the corrected text into the entry, not the original.
- **Infrastructure failure is not refutation.** If a refuter dies, its claim is
  UNVERIFIED and must be recorded as debt, not silently filed with the
  genuinely refuted. Phase 242's script mapped a dead refuter to
  `refuted: true`, which is fail-safe and correct for shipping, but the phase
  docs must separate the two populations.

## Guard-side corollary

The same wrong assumption reached a test guard in Phase 242: a check requiring
any printed figure to name a *manufacturer* document would have failed every
recall entry for citing a regulator. **When a phase ships regulator-sourced
content, its document-naming guard must accept a regulator record as a
document.** Check the guard against the evidence classes the phase actually
ships, not against the class you had in mind when you wrote it.
