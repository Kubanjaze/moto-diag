---
name: refute
description: Run an adversarial refuter pass over a phase's claims before they ship, and emit the checklist it must end with. Use when a phase is about to commit content rows, when a claim rests on a document, or when asked to check whether a finding survives the sources.
---

# refute — try to kill the claim before the corpus does

## What a pass is for

Not review. **Refutation.** A refuter is told to find the sentence that
makes the claim false, and the default verdict when nothing is found is
*still uncertain*, not *confirmed*.

This is judgement work and the folder does not pretend otherwise. What it
standardises is scope, the instruction, and the record.

## Scope

* **Every citation is fetched, not remembered.** Including documents already
  on disk. Phase 255B killed a row on a manual it had never opened and kept
  another on a page header it had misread.
* **A hit in a fault table, a contents list or an index is not evidence the
  machine has the part.** 255B kept a Piaggio Fly on one hit in a boilerplate
  fault table while the Fly 125's own specification reads "Start-up
  Electric".
* **A claim about how many documents say something cites distinct
  documents, not file paths.** 263 files were 172 documents; one manual
  existed under five paths.
* **A split separates a claim from its counter-evidence.** Before splitting
  a row, check whether the quote that contradicts one half lives in the
  other.

## What a pass must end with

A `## Refuter pass` block in the phase log:

```markdown
## Refuter pass

| claim | verdict | quote | source |
|---|---|---|---|
| Honda names no transmission in US scooter manuals | killed | "Primary reduction V-matic" | Ruckus owner's manual p. 96 |
```

Every row: a **verdict of kept or killed**, a **verbatim quote**, and a
**document plus page**.

## The ceiling of what this can enforce — stated, not implied

`refute_check.py` asserts C1–C4: the block exists, every row has a verdict,
every row has a quote in quotation marks, every row cites a page.

**That checks the report, not the work.** A complete block is entirely
consistent with a lazy pass. No script can tell whether the PDF was opened.

What the quote and page buy is **cheap falsification**: a reader can take
any row and check it against the source in one step, without re-deriving
which document or which page. A checklist without them moves the work of
verification back onto the reader, which is where it was before this folder
existed. That is the whole of the improvement, and it is worth having
precisely because it is small and honest.
