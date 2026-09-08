# Phase 235B — a `regulation` provenance value for known_issues

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Give `known_issues.source` a value for primary legal text, and reclassify the
one Phase 235 entry that needed it.

Guard: `pytest tests/test_phase235b_regulation_provenance.py`.
Outputs: migration 052, `SCHEMA_VERSION` 51 → 52, the `IssueSource` Literal,
`VERIFIED_SOURCES`, one reclassified entry, and an F9 parser fix.

## Existing-code audit (Step 0)

**1. The gap is Phase 235's, recorded at the time.** 235 shipped entries quoted
verbatim from Commission Delegated Regulation (EU) No 44/2014 as amended by
(EU) 2018/295 and filed them `service-manual`, because `unverified` sits in
Gate 2's forum-derived allowlist and would have held a legal text to the
forum-tip rule. This is a recurring class — Track K leaned on regulator or
legal sources at 228, 231, 233 and 235 — not a one-off.

**2. The substrate is a table SCHEMA_SQL creates, not a migration.** Dumped
live rather than read off the DDL: 17 columns, `id INTEGER PRIMARY KEY
AUTOINCREMENT`, two indexes (`idx_known_issues_make_model`,
`idx_known_issues_sort`), no triggers, no views, and exactly one foreign key
child — `repair_plan_items.source_issue_id`.

**3. The foreign key pragma is required, not defensive.** `get_connection`
sets `foreign_keys=ON`, so `DROP TABLE known_issues` is refused outright while
a child row references it. Probed rather than assumed: `PRAGMA
foreign_keys=OFF` does take effect inside `conn.executescript`, and the child's
FK re-points to the rebuilt table after the rename.

**4. `api/routes/kb.py`'s `IssueSource` is not a trust list.** It is a Literal
mirroring the CHECK so OpenAPI emits a strict enum. Omitting `regulation`
would raise a validation error on a legitimate row — mandatory, not a
judgment call. The API's actual trust judgment is prose beneath it.

**5. Two Phase 211 tests encode the five-value vocabulary by hand** — a
parametrized acceptance test and an exact `set ==` on the OpenAPI enum. Both
break by design and were updated rather than worked around.

## The `VERIFIED_SOURCES` decision

`regulation` is included. The stake is concrete: the reclassified entry renders
warning-free today, and excluding it would have made a pure relabelling start
printing "Origin not recorded" over a verbatim regulation — false, and a
silent behavioural regression.

It does not fall through to silence either. A regulation is authoritative
about a different object than a manual is — what is *required*, not what a
given machine *does* — which is the same distinction Phase 235's own entry
draws between a type-approval obligation and a bench-verified response. So it
gets its own branch: an informational scope note, not a yellow warning.

## Results

| Metric | Value |
|--------|-------|
| Migration | 052 — `known_issues` rebuilt to widen the `source` CHECK |
| SCHEMA_VERSION | 51 → 52 |
| Vocabulary | 5 → 6 values |
| Entries reclassified | 1 of 8 |
| Phase tests | 24 |
| Anti-regression pins bumped | 3 |
| F9 rules fixed | 1 |
| Backend regression | 5760 passed / 0 failed |

**Every risk in the rebuild was probed rather than reasoned about.** SQLite
cannot alter a CHECK in place, so this is CREATE-COPY-DROP-RENAME, and a
rebuild silently loses things. Confirmed on a populated v51 database carrying
a live `repair_plan_items` child row: `PRAGMA foreign_keys=OFF` **does** take
effect inside `conn.executescript`, so `DROP TABLE` succeeds where it would
otherwise be refused outright; rows survive; the **autoincrement sequence**
survives, which matters because repair plans reference `known_issues.id` and a
reset sequence would reissue ids already in use; both indexes are recreated;
the child's foreign key re-points at the rebuilt table with
`PRAGMA foreign_key_check` clean; the pragma is left ON; and the CHECK still
rejects a typo, so widening it did not weaken it. Each of those is now a test.

**The rollback maps `regulation` to `service-manual`.** Without the mapping the
restored five-value CHECK would reject those rows and the rollback would fail
on exactly the data that motivated the phase. `service-manual` is not an
arbitrary choice — it is the stand-in Phase 235 used, so rolling back restores
the pre-052 state rather than inventing one.

**`regulation` is treated as reviewed, and the stake was concrete.** The
reclassified entry renders warning-free today. Excluding `regulation` from
`VERIFIED_SOURCES` would have made a pure relabelling start printing "Origin
not recorded" over a verbatim EU regulation — false, and a silent behavioural
regression caused by nothing but a change of label. It does not fall through
to silence either: a regulation is authoritative about a different object than
a manual is, so it prints a scope note rather than a warning —
*authoritative on what is required, not on how a particular machine behaves*.
That is the same distinction Phase 235's own entry draws between a
type-approval obligation and a bench-verified response.

**Exactly one entry reclassified, established by evidence.** Of the eight
Phase 235 entries, four were `model-generated` and four `service-manual`;
of those four, three cite Aprilia's Service Station Manual and one cites
Regulation (EU) No 44/2014 and 2018/295. A test pins that the three siblings
were **not** swept along, because a relabelling can be wrong in both
directions.

**F9 was blind to the one migration shape that can change a CHECK.** The
`pydantic-literal-vs-check` rule keys each constraint to the nearest preceding
`CREATE TABLE`, so a rebuild files its CHECK under the scratch table name and
the rule keeps reading the superseded `ALTER TABLE ... ADD COLUMN`. It
therefore reported drift that did not exist — the live CHECK and the Literal
agreed exactly. Since CREATE-COPY-DROP-RENAME is the *only* way SQLite can
alter a CHECK, that blinded the guard to precisely the migrations most likely
to move an enum. The parser now follows `ALTER TABLE <scratch> RENAME TO
<real>` and re-keys. Fixing the rule was the right response to a false
positive whose cause was real; a `noqa` would have silenced a guard that is
otherwise correct.

**Three anti-regression pins fired, which is what they are for.** Gate 9,
Gate 11 and Phase 191B each pin `SCHEMA_VERSION` by literal so an unintended
bump fails loudly. All three were bumped to 52, and two carried **stale
provenance comments** — Gate 9 still described migration 043 and 191B's
opt-out reason said "literal `47`" while asserting 51 — both corrected. After
Phase 235's audit lesson, the sweep looked for every pin rather than only the
ones that failed; Phase 191D generates its fixtures from the constant and
needs no bump.

**A cross-surface guard now asserts what this phase could have broken.** The
vocabulary is written down in three places — the CHECK, a Pydantic `Literal`
and a CLI trust set. A test parses the CHECK out of `sqlite_master` and
asserts it equals `get_args(IssueSource)`, so the next phase to touch the
vocabulary cannot drift the API contract without failing.

**Key finding: a relabelling is a behaviour change unless you check the
render path.** Moving one entry between two provenance values touches no
content, but `source` drives a trust branch in the CLI. The honest-looking
options both had teeth: `unverified` would have held a quoted regulation to
Gate 2's forum-tip rule, and omitting `regulation` from the verified set would
have printed "Origin not recorded" over primary law.
