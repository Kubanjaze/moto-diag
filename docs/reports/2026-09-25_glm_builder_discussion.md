# Discussion guide: the GLM builder experiment and what it says about the process

**Companion to** `2026-09-25_glm_builder_findings.md`. The findings say what happened. This guide lists what is worth arguing about, in an order that builds. For each question it gives what we know, where the evidence is, and the options on the table. Nothing here is decided.

---

## Quick reference

| | |
|---|---|
| GLM build time per phase | 38–44 min to "ready to merge" |
| GLM defects per phase that reached review | 1–3, almost all integration, not content |
| Opus to land a GLM phase | 15–56M tokens read; about half an Opus-built phase in a *fresh* session |
| Subconscious Base plan | 60M daily tokens; one phase is about 50%, so about 2 phases a day; resets at 00:00 UTC |
| Full test suite | about 50 min serial, 13.5 min parallel (Phase 355); the machine's afternoon runs took 24–27 min |
| Work left in the ROADMAP | 93 phases when this was written; Track N has 12 (now in 3 batches plus gate 272) |

---

## 1. Is cheap-model building worth continuing?

**We know:** it roughly halved Opus usage when the review ran fresh (260), and saved nothing when it ran in the long advisor session (259). GLM content was accurate; integration was not.

**Look at:** the findings §2–§5, and the three GLM run directories.

**Questions:**
- What does an Opus-built phase cost against a GLM phase, in money and in plan limits? The Subconscious subscription is a fixed cost, and Anthropic usage is metered against the plan.
- Is "half the Opus tokens for twice the orchestration" a good trade when the operator's attention is the scarce resource?
- Which kinds of phase suit GLM? Content and checklists yes, gates maybe, and substrate or refactor work probably not.
- Is a cheaper Subconscious tier or model worth testing? The rate-limit table showed other models, such as deepseek-v4.1-flash-marathon.

**Options:**
- (a) Stop, and use Opus builders only.
- (b) GLM for content phases only, under the four conditions in the findings' verdict.
- (c) GLM for bulk reading only, which is the original CLAUDE.md rule 2.

## 2. Why were GLM's defects integration defects, and can they be moved earlier?

**We know:** every defect broke a convention enforced by some test GLM had not run: F124 head pins, allowlist sizes, live-database reads, migration tail edits. Four of them were caught one full regression at a time.

**Questions:**
- Would "GLM runs the full suite before handing over" have caught all of them? The parallel suite makes that about 15 minutes, even in the sandbox.
- Should the repo's conventions be discoverable, for example as a one-page "conventions the tests enforce" document, rather than learned by failing?
- Is a hand-kept trap list in the prompt sustainable, or does it rot like the whole-tree check list did?

**Options:**
- The full suite in the sandbox, which needs a separate venv (no `uv` today) or the known 7 packaging failures accepted.
- A conventions document generated from the guard tests.
- Keep the prompt's trap list.

## 3. What should an Opus review of a GLM phase consist of?

**We know:**
- The 260 landing (fresh session) cost 23M tokens read and took 3.3 h. The review itself introduced defects twice: my 259 test was not migration-proof, and a fix wrote a head literal.
- Refuting every document claim is where Opus earns its place: C7's evidence was wrong even though its conclusion held.

**Questions:**
- What is the minimum review that still catches what this one caught?
- Should the reviewer be a separate fresh session every time, with a fixed checklist?
- Who reviews the reviewer? Two of the ten defects came from the Opus side.

## 4. Throughput: where the hours go now

**We know:**
- Since 355 the suite runs in 13.5 min, and 24–27 min on a throttled afternoon.
- Close-out ceremony is fixed per phase: 7 artefacts, 13 checks, the handoff, backup and deploy.
- Batching Track N cut 11 phases to 3.

**Questions:**
- Would turning Low Power Mode off on AC, or putting test databases on a RAM disk, make 13 minutes the norm? (Both are on the kinks list.)
- Which other stretches of the ROADMAP are "same shape, many rows" and could be batched?
- At current pace, what is the realistic date for finishing the 93 remaining phases, and what would the order look like if launch-critical work (Stripe, launch readiness) went first?

## 5. Safety and control

**We know:**
- The sandbox held against planted writes and pushes.
- Rule 1 now says only the operator grants a stop's approval, in scoped words. The advisor session nearly phrased an approval as a formality.
- One heredoc slip ran backticked text as shell commands. Nothing harmful ran.

**Questions:**
- Is `sandbox-exec` (deprecated by Apple, still working) a durable boundary, or should the GLM builder move to a VM or container?
- Should scoped pre-approvals have a standard form that the builder quotes back verbatim in its report?
- Heredocs with backticks: a lint, or just the rule?

## 6. The parked kinks, one question each

Every item below is from the findings §10. Take each only once the pipeline has run end to end.

1. **Whole-tree gates.** Derive the list mechanically, for example with a pytest marker, or simply always run the full parallel suite before commit?
2. **Duplicated allowlist pins in 3 files.** Keep one pin and delete the other two?
3. **F158.** Land the guard test as a shrinking ratchet now, or with the repair phase?
4. **R6 and batches.** Does batch 1's "folded into" convention hold, and should R6 encode it?
5. **Review in a long session.** Make "fresh reviewer" a rule?
6. **Sandbox venv.** Is it worth installing `uv`?
7. **verify_phase check 12.** Should it read a refute written as prose, or should every refute use the `/refute` checklist?
8. **A5.** Should it require the regression command? That changes an artefact's definition, so it is a rule-1 decision.
9. **Machine limits.** Low Power Mode, RAM disk, fsync.
10. **Subconscious plan.** It cancels on 2026-10-23: renew, change tier, or let it lapse?

## 7. If the experiment is repeated: what to measure

- Record Subconscious allowance **% before and after, on the same UTC day** (it resets at 00:00 UTC). 258's total was lost to the rollover.
- Record wall-clock per stage: GLM build, review, each regression, deploy.
- Run the per-session token card on both sides.
- Count defects by class, introducer and catcher, as in the findings' §4 table.
- Use a matched pair: one content phase built by Opus and one by GLM, reviewed the same way.

## 8. Posting the findings

**Audience:**
- a short thread, for people running agentic coding setups; or
- a longer write-up, for people choosing between frontier and cheaper models in a builder/reviewer split.

**Redact or generalise before posting:**
- account identifiers and API key fragments (none are in these two documents);
- home-directory paths;
- the session ids, which are harmless but meaningless outside;
- the repo name, if the project is private.

**Keep:**
- the numbers;
- the defect table;
- the verdict's four conditions;
- the honest part, that the reviewer introduced defects too.

**Formats:**
- this markdown as-is;
- a private web page to share by link;
- a thread of 6–8 posts cut from the Summary and the verdict.

**Before posting:**
- decide whether 355's speed-up belongs in the same story. It was prompted by the experiment, but it is a separate result;
- re-check every number against §11's sources.
