# Phase 214 — BMW K-series touring

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Cover BMW's K-series touring line — the longitudinal K1200RS/GT "flying
brick" era, the transverse K1200S/R/GT and K1300 generation, and the
K1600GT/GTL inline six — including the Duolever front end, which has no
coverage anywhere in the corpus.

The verification risk **inverts** from the last two phases. Phases 212
and 213 policed *misattribution*: Paralever, shaft drive and servo ABS
on an F-series or an S1000 are hardware the bike does not have. The
K-series genuinely **is** shaft-driven with Paralever and genuinely
did carry servo Integral ABS, so those references are correct here.
What replaces that risk is **duplication of the existing R-series
file**, which already covers Paralever pivots, Integral ABS pump
failure, final-drive bearings and input-shaft splines.

CLI: `motodiag kb list --make bmw`; the guard is
`pytest tests/test_phase214_bmw_k_series.py`.

Outputs:
- `src/motodiag/knowledge/seed/knowledge/known_issues_bmw_k_series.json`
- `tests/test_phase214_bmw_k_series.py`
- Any R-series entry genuinely shared with the K widened rather than
  duplicated (the Phase 212 fuel-strip precedent)
- Documented known-issue count updated (690 → 690 + N)

## Existing-code audit (Step 0, per CLAUDE.md)

Run inline. Nouns audited: `k1200`, `k1300`, `k1600`, `k100`, `k75`,
`duolever`, `telelever`, `flying brick`, `inline-six`, plus the
shared-hardware terms.

**1. Completely greenfield.** Not one occurrence of `K1200`, `K1300`,
`K1600`, `Duolever` or `Telelever` anywhere in 690 entries. **Duolever
and Telelever have no coverage at all** — no entry in the corpus
describes either front end, which makes them the most valuable thing
this phase can add.

**2. Five R-series entries cover hardware the K really shares** — this
is the duplication risk, and it is the inverse of the last two phases:

| Existing entry (Phase 211) | Its scope | K-series relationship |
|---|---|---|
| Integral ABS servo pump failure | `R1150/R1200 (Integral ABS)` | Servo Integral ABS was fitted to K1200 models of the same era. **Widen, do not duplicate.** |
| Paralever pivot bearing wear | `R-series (Paralever)` | The K uses Paralever too. **Widen, do not duplicate.** |
| Final drive crown-wheel bearing | `R1200GS` hexhead | A different final-drive unit. A K entry is legitimate only if it is about the K's own unit. |
| Gearbox input-shaft spline wear | `R-series (oilhead/hexhead)` dry clutch | Depends on the K generation's clutch and gearbox layout — a trap, not an automatic port. |
| Fuel-level strip sensor | already widened to `R1200GS / F800GS / F650GS twin` | May extend again if the K shares the part. |

Plus `cross_platform_drivetrain`'s shaft-drive service entry, which
already names "R/K" and covers hypoid oil, seals and universal joints
generically.

**3. Generation traps, and a wrinkle in the roadmap row.** Row 214
lists "K1200RS, K1200GT, K1300S, K1600GT/GTL inline-6, Duolever front".
The **K1200RS (1997–2005) does not have Duolever** — it is the
longitudinal-engine generation with Telelever. Duolever arrives with
the transverse K1200S/R/GT in 2005 and continues through K1300 and
K1600. The row reads as a topic list rather than a claim that all four
share the front end, so it is not wrong the way row 212 was — but an
entry that puts Duolever on a K1200RS would be.

Other traps: longitudinal ("flying brick", K100/K75/K1100/K1200RS/GT)
versus transverse (K1200S onward) are different engines entirely;
K1600 is an inline **six** from 2011 and shares almost nothing with the
fours; "K1200GT" names both a longitudinal 2003–2005 bike and a
transverse 2006–2008 one.

**4. Contract** unchanged from 211–213, including the symptom-format
rule that produced clean output in 213 when moved into the schema with
its reason stated.

## Logic

1. **Draft** — six lenses: longitudinal K1200RS/GT (1997–2005);
   transverse K1200S/R/GT (2005–2008); K1300S/R/GT (2009–2016);
   K1600GT/GTL inline six (2011+); Duolever and Telelever front ends;
   K-series drivetrain and final drive.
2. **Dedup** — plain code against all 30 existing BMW titles.
3. **Verify** — three refuters, briefed for the inverted risk:
   - *attribution*: wrong K generation (Telelever vs Duolever,
     longitudinal vs transverse, four vs six); **explicitly told that
     Paralever, shaft drive and Integral ABS are legitimate on a K**;
     and still policing generic-touring-bike failures relabelled.
   - *duplication* (replacing 213's figures-only framing with a
     broader one): does this restate an existing R-series entry, or a
     cross-platform entry, rather than describing the K's own version?
     Plus the invented-figures check.
   - *safety and procedure*, unchanged.
4. **Synthesize**, then I write the files and run the regression.

## Key Concepts

- **The inversion is the whole design problem.** A refuter briefed as
  in Phase 212 would kill every correct K entry that mentions
  Paralever. The attribution prompt therefore states outright that
  shaft drive, Paralever and Integral ABS *are* K hardware, and moves
  the scepticism to generation and duplication.
- **Widen rather than duplicate**, the precedent set when Phase 212
  found the fuel-strip sensor shared between R1200 and the F800 family.
- Duolever and Telelever are genuinely uncovered, so they carry the
  phase's clearest marginal value — the opposite of Phase 213, where
  everything generic was already present four times over.
- Symptom-format rule stays in the JSON schema with its reason stated.

## Verification Checklist

- [ ] Workflow ran 3 refuters per candidate; drafted / survived / kept
      and every drop reason recorded
- [ ] Zero undecided, or any reported
- [ ] Every entry: `make == "BMW"`, explicit K model with generation,
      `source == "model-generated"`, "general knowledge" in description
- [ ] No entry places Duolever on a longitudinal K1200RS/GT, or
      Telelever on a K1200S/K1300/K1600 — asserted
- [ ] No entry restates the R-series Paralever, Integral ABS or
      final-drive entries; any genuinely shared entry is widened on the
      R-series file instead — asserted
- [ ] `dtc_codes` empty (Phase 215 owns BMW fault codes)
- [ ] Symptoms are short searchable phrases; real queries hit
- [ ] All four BMW files load together without title collision
- [ ] Count guard fires; four docs updated
- [ ] Backend regression green; F9 lint clean

## Risks

- **The inverted briefing could over-correct.** Telling the attribution
  refuter that Paralever is legitimate on a K removes a guardrail that
  worked twice. The duplication lens is what replaces it; if both miss,
  a restated R-series entry ships. The tests assert against the
  existing titles as a backstop.
- **The K1600 is an inline six with little in common with the fours**,
  and it is the least-documented model here. Expect few survivors, and
  record empty generations openly as Phase 213 did rather than padding.
- **Three model-generated refuters are not a service manual.** Every
  entry stays tagged and the CLI warns on each.
