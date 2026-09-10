# Phase 244M research — per-client memory and cross-shop repository

Three research agents, adapted from the Track K cadence. The lenses in
`RESEARCH_LENSES.md` are written for verifying factual claims about machines
against sources; these questions are architectural, so the *discipline* carried
over — refuted by default, primary sources, unverified kept separate from
refuted — while the questions did not.

Every finding below was labelled by its agent as one of: legal-requirement,
regulator-guidance, industry-practice, evidence, or inference. Those labels are
preserved. **Inference is not evidence** and is marked as such.

---

## Strand A — when is a locally-answered question safe?

**A1. Semantic-cache error rates rise as the cache grows.** Measured on the
vCache benchmark: GPTCache at static threshold 0.99 gives 2.5% error / 37% hit;
0.98 → 4.1% / 53%; 0.97 → 5.2% / 67%, and the paper reports error increasing
with sample size. *A cache tuned safe at 200 stored answers is not safe at
20,000.* — arxiv 2502.03771

**A2. The cause is distributional, not a tuning failure.** Correct and incorrect
cache hits occupy overlapping similarity ranges; optimal per-entry thresholds
vary substantially, so no single threshold suffices. — same source

**A3. Context-dependent queries are the worst case, by 18×.** GPTCache produced
**54** false hits on contextual queries where MeanCache produced **3**; 233 false
hits out of 700 unique queries at the recommended 0.7 threshold. — arxiv
2403.02694

> This is the finding that most constrains the design. Every question this
> product answers is context-dependent: "why is it running lean" means nothing
> without the bike, the mileage and the last repair. The product's dominant
> query shape is the shape semantic caches measure worst on.

**A4. Embeddings are insensitive to negation** — the exact distinction between
two opposite diagnostic answers. — arxiv 2306.05083 (HEROS, ACL 2023)

**A5. Provenance labels raise trust whether or not they are accurate.** N=303,
between-subjects: citations significantly increased trust *even when random*,
and only **42.1%** of participants checked even one. — arxiv 2501.01303

> Directly aimed at this product's `Grounding` labels. A `machine_specific`
> badge on a stale cached answer buys unearned trust from the ~58% who never
> look. The honesty contract becomes a liability the moment the thing it
> describes goes stale.

**A6. Clinical decision support degrades silently and is caught late.** Of 68
malfunction cases across 14 US sites, **31 initially worked and later failed**,
often with substantial delay before detection; the most common discovery mode
was **user reporting** (37 of 68). — JAMIA 2018, PMC6019061

**A7. Regulators do not ban precomputed guidance — they require its vintage be
displayed.** ONC/ASTP § 170.315(b)(11) requires source attributes for decision
support interventions including *release and revision dates*, and for predictive
interventions a description of update frequency. — healthit.gov test method

**A8. FDA's CDS criteria are nearly a specification for what this product
already does.** A *list of options* is non-device; a *specific directive* is not.
Users must be able to independently review the basis. FDA names automation bias
explicitly and treats time pressure as disqualifying for Criterion 4. — FDA CDS
final guidance

**A9. Only 34.3% of detected knowledge changes actually altered answer
correctness** — so "corpus changed, flush everything" over-invalidates roughly
3×. The useful signal is answer-affecting change. — arxiv 2607.04281 (preprint;
ordering more trustworthy than absolute values)

**A10. The one published taxonomy that transfers is rate-of-change**, not topic:
never-changing / slow-changing / fast-changing / false-premise, with measured
accuracy degrading along that axis. — FreshQA, arxiv 2310.03214

### Strand A — could not be established

- **No study compares trust in cached vs freshly-generated answers**, in either
  direction. A clean gap.
- **No measured false-hit rate exists for a small per-client cache.** Every
  number above comes from large multi-tenant or open-domain corpora. The regime
  this phase proposes is unmeasured.
- **No caching literature exists in any high-stakes advisory setting.** The
  clinical analogue is about precomputed *rules* with named owners and displayed
  vintage — not cached generated text. That substitution is the agent's, not the
  literature's.
- **Content-addressed / version-keyed invalidation is universally recommended
  and never measured** in anything opened.

---

## Strand B — retention, deletion, and what may be kept

**B1. The mandated retention set is narrow, and the memory is not in it.**
California BAR, 16 CCR § 3358, requires keeping invoices, estimates, and work
orders for three years (Bus. & Prof. Code § 9884.11; motorcycles expressly in
scope per § 9880.1). Transcripts, video, technician notes and AI-generated
guidance are **not** listed.

> So "we are legally required to keep it" defends the transactional layer only.
> The compiled memory — the feature itself — has no retention justification and
> must be deletable on request.

**B2. A US retention statute cannot ground a GDPR Art. 17(3)(b) refusal.** That
exemption counts only *Union or Member State* law. A US shop facing an EU
erasure request must argue 17(3)(e) — legal claims — which reaches only what is
plausibly relevant to a claim.

**B3. Blanket retention is expressly forbidden.** ICO: *"you could still delete
information that could not possibly be relevant to such a claim… personal data
should be deleted when such a claim could no longer arise."*

**B4. A compiled per-customer memory is deletable personal information under
CCPA** — Civ. Code § 1798.140(v)(1)(K) covers *inferences drawn… to create a
profile*. That is precisely what this feature builds.

**B5. Keep it as rows, never as weights.** EDPB Opinion 28/2024: personal data
may remain *"absorbed"* in model parameters, models are not presumptively
anonymous, and a supervisory authority may order erasure of the model itself.
ICO: output filters do not discharge the obligation, and machine unlearning
arguments point to *"theoretical application and not any current practical
usage."*

> Deleting a row is a solved problem. Unlearning a fine-tune is not. Choosing
> weights converts a routine deletion request into an existential one.

**B6. Algorithmic disgorgement is real and has been ordered.** FTC *Everalbum*:
delete the photos, the face-recognition data, **and the models and algorithms
developed using them**. FTC *WW/Kurbo*: destroy affected work product, plus a
**forward-looking retention cap**.

> "Compiles every interaction, forever" is the posture that attracts one.

**B7. BIPA is a hard blocker if voiceprints ever exist.** 740 ILCS 14/15(a)
compels destruction *"within 3 years of the individual's last interaction"*.
Private right of action. Nothing overrides it. Recording a voice is probably not
a voiceprint; **identifying who is speaking** likely is.

**B8. The CJEU en-bloc rule threatens the whole transcript corpus.** Where
sensitive and non-sensitive data are collected together and cannot be separated
at collection, processing the whole set is prohibited absent an Art. 9(2)
derogation. Open-ended shop transcripts will eventually capture health data.
*Argues for redaction at ingest, not after.*

**B9. Plain workshop video is not Art. 9 data** — the trigger is purpose, not
content. Filming bikes is fine; adding face recognition or speaker
identification flips the entire corpus.

**B10. No competitor has solved this.** Seven policies opened — Shopmonkey,
Mitchell 1/Snap-on, ALLDATA, Tekmetric, AutoLeap, Shop-Ware, CARFAX. **None**
distinguishes vendor-as-processor data from shop-as-controller records, or
addresses the erasure-versus-retention conflict. CARFAX's privacy statement does
not contain the word "retention".

**B11. The compliance burden lands on the vendor, not the shops.** Most
independent shops fall under all three CCPA thresholds; a platform aggregating
across shops is far likelier to cross the 100,000-consumer line than any of its
customers.

### Strand B — could not be established

Michigan and Pennsylvania statute text (secondary sources only); Member State
VAT retention periods; whether Florida ch. 559 imposes a period outside
§ 559.905; a primary judicial opinion on voiceprint vs voice recording; Texas
CUBI and Washington biometric statutes; **technician monitoring law** — recording
staff raises consent, works-council and two-party-consent wiretap issues wholly
separate from customer privacy, and nobody has looked at it.

---

## Strand C — cross-tenant boundary

**C1. The constraint is a STATUS CHANGE, not a privacy technique.** GDPR
Art. 28(10): a processor that determines its own purposes *"shall be considered
to be a controller in respect of that processing"*, and the EDPB's worked example
— a processor using one customer's database *"for developing their own business
activity"* — says that processing *"would constitute an infringement"*.
CCPA is even more direct: 11 CCR § 7050(a)(3) lets a service provider use
customer PI to *"build or improve the quality of its services"* — *"provided that
the service provider does not use the personal information to perform services on
behalf of another person."*

> A cross-shop repository is, definitionally, using shop A's data to serve
> shop B. No amount of hashing or noise changes that: it is about who decides
> the purpose. **The macro layer must be something the vendor is openly the
> controller of, with its own lawful basis and its own notice — not an incident
> of providing the shop's service.**

**C2. The EDPB has already drawn the line between the two layers.** Opinion
28/2024 ¶95 asks whether processing *"would only impact the service provided to
the data subjects… or whether it would be used to modify the service provided to
all customers."* Per-client memory sits on the defensible side of that sentence.
The hive mind sits on the other.

**C3. Wear-and-tear data is personal data.** EDPB Guidelines 01/2020 ¶3 names
*"data relating to the wear and tear on vehicle parts"* explicitly. The instinct
that diagnostic data is not personal data is wrong in the EU.

**C4. Pseudonymisation is not anonymisation, and DP does not save you if you keep
the raw data.** WP216 lists *"believing that a pseudonymised dataset is
anonymised"* under common mistakes, and states that where the original data
remains, *"results [of differential privacy queries] have also to be considered
as personal data."* Its anonymous-aggregate example depends on the controller
deleting the raw data — which this product cannot do and still function.

**C5. The US position is the opposite, and the asymmetry cannot be engineered
away.** CCPA § 1798.140(v)(3) carves deidentified and aggregate data out of
"personal information" entirely, subject to three conditions including a
**public commitment** not to re-identify.

**C6. FTC: appropriating business customers' competitively significant
information is an unfair method of competition** — the closest any US authority
comes to naming "pool one shop's know-how to serve its competitors". And the
rights must be taken **up front**: retroactively widening terms is the specific
move the FTC flags, with *Gateway Learning* as precedent and *Everalbum* showing
the remedy is model destruction.

**C7. Differential privacy has lost its credibility anchor.** Commerce order
DAO 216-26 (June 2026) bars the US Census Bureau from noise infusion; permitted
methods are now **coarsening** (preferred) and **suppression**. DP is deployed
nowhere in SMB vertical SaaS. Federated learning solves a problem this product
does not have — *FL exists to avoid centralising data you do not already hold.*

**C8. A cross-tenant index must be a separately built, separately governed
artifact** — never the per-shop index with its filters relaxed. Tenant isolation
and cross-tenant retrieval cannot come from the same index.

**C9. Almost nobody de-identifies the business entity.** Of ~15 vendors
surveyed, one. **Shops will care far more about shop-level identifiability than
about VIN-level**, and every peer leaves practice-level data poolable.

**C10. Not one surveyed vendor offers a per-customer opt-out from aggregation.**
Every opt-out found was marketing email, cookies, GPC or arbitration.

**C11. Aggregation rights and AI-training rights are orthogonal.** ServiceTitan
forbids shared-model training while freely building cross-customer benchmarks
through a separate Aggregate Data pathway. Draft both or leave a gap.

**C12. The sleeper risk is the Feedback clause.** A mechanic correcting a fault
tree — *"on this model that code actually means X"* — is simultaneously the
crown-jewel asset and textually *"a correction or other feedback relating to the
operation of the service"*, which standard clauses assign to the vendor
outright. **Carve diagnostic corrections out of Feedback and handle them under a
named data clause.**

**C13. There is no case law.** Extensive searching surfaced only data-*breach*
litigation. No implied limit will be read into a broad aggregate clause; the
contract text is the entire defence.

**C14 — THE FINDING THAT SHAPES THE DESIGN. The control point already exists in
this codebase.** `known_issues.source` is a CHECK-constrained provenance field
whose values map almost exactly onto shareability:

| value | cross-tenant status |
|---|---|
| `regulation` | public-domain — freely shareable |
| `model-generated` | vendor-authored — vendor's own |
| `service-manual`, `forum` | third-party — constraint is **copyright**, not privacy |
| `mechanic-verified` | **the shop's own labour — the competitively significant asset** |
| `unverified` | legacy, no recorded origin |

> Gate cross-tenant sharing on this existing field rather than inventing a
> mechanism. Fourth time this session that reading for what exists beat
> building something.

**C15. Layer (a) needs no exfiltration at all; layer (b) moves shop data
off-premises for the first time.** The product is single-tenant on-premise today
— `shop_id` is a tenant key *inside one local install*. That is a change in data
*flow*, not features, and per C6 it must be disclosed up front.

### Strand C — could not be established

Texas TDPSA primary text (secondary only); HHS de-identification guidance (403 on
both HTML and PDF — the claim that OCR names no universal k reached us only
through search renderings); CPPA Honda/Ford orders (law-firm summaries only);
Identifix's actual shop subscription agreement (not public — only the website
ToU); CDK, Bosch, Tekion, current Covetrus terms; whether powersports has any
pooled-fix equivalent (**Cyclepedia returned 403 — finding #73 is a hypothesis,
not a finding**). Enterprise contracts are non-public throughout, so every
public-terms finding may be superseded by negotiated terms.

---

## Verification — five load-bearing claims, adversarially refuted

Every source was opened. Nothing was fabricated. **Three of five are materially
overstated in ways that change the design**, and the corrections matter more
than the originals.

**V1 — cache error growth: SURVIVED, scope corrected.** The growth claim is
data-backed (Figure 4, three benchmarks), not bare prose. But Table 3's
0.99/0.98/0.97 figures are an ablation on *one* benchmark, one embedding, one
LLM, and are end-of-run aggregates rather than the growth curve — splicing them
onto the growth claim conflates two results. **The paper's stated mechanism is
prompt DIVERSITY, not cache size.** For this product that distinction is
decisive: a store that grows with near-duplicate questions behaves differently
from one that grows in diversity.

**V2 — the 18× contextual result: REFUTED as stated.** Both numbers are real
and quoted correctly in isolation, but they come from **two unrelated
experiments** welded together: the 54-vs-3 figure is a synthetic contextual-query
benchmark; the 233/700 figure is a *separate standalone-query* deployment.
Presenting them together implies contextual queries drove the 233. They did not.
Worse, MeanCache tuned its own threshold per embedding while pinning GPTCache at
a default the paper itself calls *"suboptimal"* — **this is the proposing paper
grading its own rival.** It does not establish a ceiling on semantic caching.

**V3 — random citations raise trust: SURVIVED on the letter, misleading as
summarised.** A real between-subjects experiment (N=303, Prolific, hover-tracked
checking). But: random citations scored **significantly lower** than valid ones,
and **the effect vanishes for answers whose citations were checked** (M=7.55 vs
7.73). And the 42.1% is of participants *shown* citations, not of all
participants — at the answer level only **9.77%** of cited answers were ever
checked. That last number is worse for us, not better.

**V4 — ONC source attributes: SURVIVED, two corrections.** The revision-date
attribute is verbatim. But it requires *access by a limited set of identified
users*, *not display to end users* — and it belongs to the **evidence-based**
branch. An LLM answering diagnostic questions maps to the **Predictive** branch,
which has no release/revision-date item at all.

**V5 — FDA CDS guidance: SURVIVED, date confirmed.** Issued 29 January 2026, and
it supersedes the 6 January 2026 issuance — not the 2022 one directly. Both
substantive points confirmed verbatim. **But the 2026 revision softens the
list-vs-single rule**: a single option is no longer automatically disqualifying
where it is the only clinically appropriate one.

**V6 — cross-cutting category error.** Claims 4 and 5 are *healthcare*
regulatory instruments — certified health IT and the medical-device definition.
A motorcycle-diagnostic product is neither. They are usable as **design
analogy** and nothing more. Treating them as binding constraints would be a
category error, and the first summary of this research came close to doing so.

**What survives as genuinely load-bearing:** semantic similarity is an unreliable
key for context-dependent questions, and no threshold generalises across
corpora. What does *not* survive is a general claim that semantic caching
degrades as it grows — that requires our own tuning and a domain-specific error
measurement neither paper provides.
