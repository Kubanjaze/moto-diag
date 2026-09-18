# Phase 244Z — What the shelved modules would say if anyone wired them — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-18

---

## 2026-09-18 — Plan v1.0

The last letter. Six engine modules stayed on the shelf after 244Y because
the audit's word for them was keep shelved — they are the only route to
content the knowledge base does not carry — and the audit also named four
things in them that would put a wrong number or a wrong diagnosis in front
of a technician the day any one is wired. Every one is content, not wiring.

Step 0 verified all four on the tree: a prompt line that instructs the model
to invent torque specs, with an exemplar about twenty percent under the M14
drain plug and no provenance anywhere in the module; a correlation rule
that diagnoses a coolant-jacket leak on an air-cooled twin, and a mechanical
scan showing it is the only rule of eighteen with that shape; three
charging-voltage floors at three RPMs, one of which ships today through
`ref circuit charging`; and a parts field that asks the model for part
equivalences, which fail unsafe because both numbers resolve.

One decision taken in planning: CORR-001 is deleted, not rewritten. Making
it true would mean authoring head-gasket symptoms for air-cooled Harleys,
which is exactly the kind of content this project has learned not to
invent. Nothing here reaches a user; this is fix-before-wiring, said plainly.

## 2026-09-18 — Built

Four content fixes, two things learned. Deleting CORR-001 broke seven
Phase 90 tests, because the rule I called incoherent was also the rule
that suite had been written against; Step 0 named the file and did not
read it. Retargeted at CORR-002, same shape, arithmetic unchanged.

The second is the interpreter's. A mutation that put a nonexistent rule id
back into the docstring survived, and then the real tree failed the very
test the mutant should have. The two ids are the same length, the runs
take a twentieth of a second, and Python's bytecode check is whole-second
mtime plus size — so the mutant ran on the previous run's bytecode and the
real tree on the mutant's. Every earlier mutant in the series changed a
file's size. The script clears bytecode now; 5/5 on a clean cache.

25 tests, 488 across the suites, 5/5 mutations. Nothing made reachable.

244G's meta-guard then fired on this file's own raw-source reads, as it
had on 244Y's. Fixed the same way; the scanner runs over new test files
before a regression now.

## 2026-09-18 — Complete

Regression **6,972 passed, 0 failed, 19:43**. No schema change; nothing made reachable.

The 244 series is complete. The roadmap resumes at 245.
