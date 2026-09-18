# Phase 244W — The gate can see a module that only talks to itself — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-17

---

## 2026-09-17 — Step 0

Opened off the audit that 244V's close-out set up: eight unwired engine
modules, read by eight agents and challenged by twenty-four, and none scored
above 4.3/10 as worth wiring. The completeness critic then found the thing
that mattered more than any of the eight — two modules the gate had never
reported, because a class that names itself counts as used and a dead module
importing another dead module launders both.

I reproduced the mechanism before believing it, and then got the scale wrong
twice. First run: 55 modules, 15,669 lines. False — FastAPI routers are
reached by registration, not by name, and the fixpoint had swallowed
everything only a route handler calls. Second run: 25 modules, 5,278 lines.
Also false, differently — the allowlist has two tables and I had checked one;
sixteen of the twenty-five were already recorded in `UNREACHABLE_MODULES`.
What neither table holds is **nine modules, 1,398 lines**, each verified by
hand: a grep for every public name, excluding the module's own file and every
package init, returns nothing.

The nine have a shape. They are repository and model layers inside packages
whose *other* modules are live — so the package is not an island, the import
edge from `__init__` is real, and the module sits in the gap between the two
checks. Three are superseded (`history.py` by `session_repo`;
`hardware/protocols/models.py` by the plain-typed adapter interface the
adapters were actually built against, an unfulfilled contract; `roles_repo`
by `shop/rbac.py` walking the same tables with its own SQL). Five are
substrate for named roadmap rows. One, `retrieval.py`, reads only from a
superseded module and cannot run against real data as written.

The operator chose to fix the instrument before acting on any of the audit's
delete or content findings: the gate's output is a decision the tree can
hold; an agent's recommendation is a conversation.

Four designs are being prototyped and judged on this tree — a module-level
fixpoint, a use-graph rewrite of the import walk, AST-scoped orphan
detection, and a def-level call graph — with false positives as the deciding
criterion, because a gate that cries wolf turns its allowlist into a rubber
stamp within a week.

## 2026-09-17 — Step 0, continued: the design pass found a hole in 244U

Three of four design prototypes are back. The island fixpoint and the
use-graph agree with each other and with my hand count on 18 modules; the
use-graph, which rebuilt the walk on real name uses rather than imports,
also found a 19th that identifier counting cannot see:
`feedback/learning_hook.py`, whose only reference outside its init is a
string literal inside a migration description. Mention-vs-use, in a string.

The third one back, which tried to fix `find_orphans` in place, found
something about 244U instead: its regex for blanking a package-init import
stops at a newline, so a parenthesised multi-line `from … import (…)` is
never blanked at all. Verified on this tree — `auth`, `inventory`, `billing`
and `feedback` inits all use that form, and the names 244U was meant to stop
counting still count. The fixture I wrote for 244U used single-line imports.
It passed, and it was pinning the wrong shape. Fixing it costs 99 new
orphans, 43 of them inside the 19 dead modules; the 56 that remain are in
live code and are exactly what 244U was written to find.

All 19 modules are now classified from evidence in a compaction-safe note:
three superseded (one an unfulfilled contract, one reimplemented inline with
its own SQL), eight substrate for named roadmap rows, eight engine modules
the audit already scored. The delete phase inherits that, not a list.

## 2026-09-17 — Built

The judges split three ways and the adversary settled it: the use-graph led
on false positives, the fixpoint on maintainability, the def-level call
graph on coverage — and the adversary, attacking the use-graph, found two
false-positive classes specific to resolving names through re-export chains,
one of which this repo already uses at `auth/__init__.py:78`. The fixpoint
counts identifier tokens per module and is immune to both. The maintenance
judge's ablation decided it: strip all nine seed rules and the fixpoint's
answer does not move. Forty lines, one seed, a reason you can grep.

The build's only real defect was one the real tree could not have shown.
Every synthetic test failed on first run because the entry-point module was
flagged as an island: nothing in a three-file tree names `cli`, so the root
was dead, and once the root is dead its references stop counting and
everything it calls follows. On the real tree `cli` is named in dozens of
files — the same accident of naming that keeps route modules alive through
`router`. Roots are now excluded from candidacy, structurally.

The six that remained were the fixture's, and the diagnosis is worth a
line: 209B's real-tree entry points include the package root, mine did not,
so the init was unreachable and the check correctly declined to report what
the import walk already had.

Prose strings are blanked in the shared loader now, and the two extra
orphans it surfaced were exactly the predicted two. The 244U regex fix is
244X, with its measurement attached.

61 tests, 180 across the three gate suites, 11/11 mutations.

## 2026-09-17 — Complete

Regression **7,011 passed, 0 failed, 20:21**. No schema change, no source change under `src/`.

Next: 244X, the 244U regex and its 56 residual names.
