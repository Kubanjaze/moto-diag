# MotoDiag Phase 164 — Automated Triage Queue

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-21

## Goal

Fifth Track G phase. The "what to fix first?" answer for a mechanic standing in the shop. Pure query-synthesis + deterministic-scoring layer over Phase 161 work_orders + Phase 162 issues + Phase 163 AI priority (consumed via work_orders.priority) + Phase 165 parts availability (soft-guarded since 165 hasn't shipped yet). Writes nothing per query; mutations confined to dedicated CLI subcommands (flag-urgent, skip, weights-tune).

CLI — `shop triage {queue, next, flag-urgent, skip, weights}` — 5 subcommands.

**Design rule:** zero AI calls (Phase 163 scores consumed via priority column, never re-invoked here), zero tokens, micro migration 028 (single ALTER TABLE shops ADD COLUMN triage_weights TEXT). Additive-only to cli/shop.py. Never mutates Phase 161/162/163 surfaces.

Outputs:
- Migration 028 (~30 LoC): `ALTER TABLE shops ADD COLUMN triage_weights TEXT;`
- `src/motodiag/shop/triage_queue.py` (~340 LoC).
- `src/motodiag/shop/__init__.py` +8 LoC.
- `src/motodiag/cli/shop.py` +380 LoC — `triage` subgroup + 5 subcommands.
- `src/motodiag/core/database.py` SCHEMA_VERSION 27 → 28.
- `tests/test_phase164_triage_queue.py` (~35 tests, 4 classes).

## Logic

### Migration 028

```sql
-- Phase 164: per-shop tunable triage weights as JSON.
-- Nullable — NULL means "use ShopTriageWeights defaults".
ALTER TABLE shops ADD COLUMN triage_weights TEXT;
```

Rollback uses SQLite-portable rename-recreate-copy-drop pattern (same as migrations 014 and 022) to avoid depending on `DROP COLUMN` (SQLite ≥3.35). For Phase 164 simplicity, use the recreate pattern explicitly in rollback_sql.

### ShopTriageWeights (Pydantic)

```python
class ShopTriageWeights(BaseModel):
    priority_weight: float = Field(default=100.0, ge=0.0)
    wait_weight: float = Field(default=1.0, ge=0.0)
    parts_ready_weight: float = Field(default=10.0, ge=0.0)
    urgent_flag_bonus: float = Field(default=500.0, ge=0.0)
    skip_penalty: float = Field(default=50.0, ge=0.0)
    model_config = {"extra": "forbid"}
```

### TriageItem (Pydantic)

```python
class TriageItem(BaseModel):
    work_order: dict       # Phase 161 list_work_orders row, denormalized
    issues: list[dict] = []  # Phase 162 issues if importable; else []
    parts_ready: bool = True
    parts_missing_skus: list[str] = []
    wait_hours: float = 0.0
    triage_flag: Optional[str] = None      # 'urgent' or None
    triage_skip_reason: Optional[str] = None
    triage_score: float = 0.0
    rank: int = 0          # 1-based, populated after sort
```

### Triage score formula (deterministic)

```python
triage_score(WO) =
      priority_weight * (1 / max(1, priority))
    + wait_weight      * (wait_hours / 24.0)
    + parts_ready_weight * (1 if parts_ready else 0)
    + urgent_flag_bonus  * (1 if triage_flag == 'urgent' else 0)
    - skip_penalty       * (1 if triage_skip_reason is not None else 0)
```

Defaults: priority_weight=100, wait_weight=1.0, parts_ready_weight=10, urgent_flag_bonus=500, skip_penalty=50.

Tiebreaker: `(-triage_score, created_at ASC, wo_id ASC)` — stable, deterministic.

### Phase 165 soft-guard

```python
def _parts_available_for(wo_id, assumed_available, db_path=None) -> tuple[bool, list[str]]:
    spec = importlib.util.find_spec("motodiag.shop.parts_needs")  # Phase 165 module name
    if spec is None:
        return (assumed_available, [])
    try:
        from motodiag.shop import parts_needs
        # Phase 165 contract: list_parts_for_wo(wo_id, db_path=None)
        lines = parts_needs.list_parts_for_wo(wo_id, db_path=db_path)
    except Exception:
        return (assumed_available, [])
    if not lines:
        return (True, [])
    missing = [
        line.get("part_slug", str(line.get("part_id", "?")))
        for line in lines
        if line.get("status") not in ("received", "installed")
    ]
    return (len(missing) == 0, missing)
```

**CONTRACT:** Phase 165 must export `list_parts_for_wo(wo_id, db_path=None)`. Per consolidation_notes.md migration table.

### Triage markers stored in `description` (no new columns)

`flag_urgent(wo_id)` writes `[TRIAGE_URGENT] ` prefix to description; `skip_work_order(wo_id, reason)` writes `[TRIAGE_SKIP: reason] ` prefix. Parsed on read via prefix-anchored parser.

```python
def _parse_triage_markers(description: Optional[str]) -> dict:
    """Returns {'flag': 'urgent'|None, 'skip_reason': str|None, 'clean_description': str}."""
    if not description:
        return {"flag": None, "skip_reason": None, "clean_description": ""}
    flag = None
    skip_reason = None
    clean = description
    if clean.startswith("[TRIAGE_URGENT] "):
        flag = "urgent"
        clean = clean[len("[TRIAGE_URGENT] "):]
    if clean.startswith("[TRIAGE_SKIP: "):
        end = clean.find("] ")
        if end > 0:
            skip_reason = clean[len("[TRIAGE_SKIP: "):end]
            clean = clean[end + 2:]
    return {"flag": flag, "skip_reason": skip_reason, "clean_description": clean}
```

### triage_queue.py — function inventory

```python
def build_triage_queue(
    shop_id: Optional[int] = None,
    include_unassigned_only: bool = False,
    assumed_parts_available: bool = True,
    assigned_mechanic_user_id: Optional[int] = None,
    include_terminal: bool = False,
    weights: Optional[ShopTriageWeights] = None,
    top: Optional[int] = None,
    now: Optional[datetime] = None,    # injectable for deterministic tests
    db_path: Optional[str] = None,
) -> list[TriageItem]: ...

def load_triage_weights(shop_id, db_path=None) -> ShopTriageWeights: ...
def save_triage_weights(shop_id, weights: ShopTriageWeights, db_path=None) -> bool: ...
def reset_triage_weights(shop_id, db_path=None) -> bool: ...

def flag_urgent(wo_id, db_path=None) -> bool: ...           # priority=1 + [TRIAGE_URGENT] prefix
def clear_urgent(wo_id, db_path=None) -> bool: ...          # remove prefix; priority NOT auto-restored
def skip_work_order(wo_id, reason: str, db_path=None) -> bool: ...   # [TRIAGE_SKIP: reason] prefix; empty reason clears

def _parse_triage_markers(description) -> dict: ...
def _parts_available_for(wo_id, assumed_available, db_path=None) -> tuple[bool, list[str]]: ...
def _compute_wait_hours(opened_at: Optional[str], now: datetime) -> float: ...
def _compute_score(item: TriageItem, weights: ShopTriageWeights) -> float: ...

class ShopTriageError(ValueError): ...
```

### CLI subgroup

```python
@shop_group.group("triage")
def triage_group(): ...

@triage_group.command("queue")
# --shop --mechanic --top --include-terminal --assume-parts-available/--require-parts --json
def triage_queue_cmd(...): ...

@triage_group.command("next")
# --shop  (single highest-ranked WO as Rich Panel)
def triage_next_cmd(shop): ...

@triage_group.command("flag-urgent")
# WO_ID
def triage_flag_urgent_cmd(wo_id): ...

@triage_group.command("skip")
# WO_ID --reason "..."  (empty reason clears)
def triage_skip_cmd(wo_id, reason): ...

@triage_group.command("weights")
# --shop (required) --set key=value (repeatable) --reset
def triage_weights_cmd(shop, set_kv, reset): ...
```

Rich queue table columns: Rank | WO# | Pri | Title | Bike | Customer | Wait | Parts | Mechanic | Flag.

## Key Concepts

- **Soft-guarded Phase 165 dependency.** `find_spec("motodiag.shop.parts_needs")` returns None → treat all parts ready. Same pattern as Phase 150 fleet_analytics → Phase 149 wear.
- **Deterministic scoring (not AI).** Tunable per-shop via `triage_weights` JSON. Running `triage queue` twice = byte-identical output. Phase 163 AI scores already baked into `work_orders.priority`; consumed via that column.
- **Markers in description, not new columns.** Phase 164's migration is one ALTER TABLE; markers ride on existing description field. Trade-off: description grows; mitigated by stripping markers in Title column rendering.
- **`build_triage_queue` is pure read.** Mutations confined to dedicated helpers.
- **`now` injectable for deterministic tests.**
- **Priority inverse via 1/priority weight.** Lower priority number = higher score (matches Phase 161 convention; mechanic intuition).
- **Wait-time anti-starvation.** Default wait_weight=1.0 means 5 days = +5.0 score, lifts pri-3 (~33) toward pri-2 territory (50).
- **Per-shop weights tuning.** Dealership might weight parts_ready high; independent might weight wait_weight high. Mechanics tune via `weights --set wait_weight=2.5`.

## Verification Checklist

- [ ] Migration 028 registered; SCHEMA_VERSION 27 → 28.
- [ ] Fresh init_db creates shops.triage_weights nullable TEXT.
- [ ] rollback_migration(28) preserves Phase 160-163 state.
- [ ] ShopTriageWeights defaults match documented values.
- [ ] ShopTriageWeights rejects negative values.
- [ ] ShopTriageWeights rejects unknown keys (extra=forbid).
- [ ] save_triage_weights round-trips JSON.
- [ ] load_triage_weights on NULL column returns ShopTriageWeights() defaults.
- [ ] reset_triage_weights sets column NULL.
- [ ] build_triage_queue with no WOs returns [].
- [ ] build_triage_queue(shop_id=S) returns only S's WOs.
- [ ] build_triage_queue(assigned_mechanic_user_id=U) returns only U's WOs.
- [ ] build_triage_queue(include_terminal=False) excludes completed/cancelled.
- [ ] Rank 1..N in returned list order.
- [ ] Equal triage_score tie-breaks by (created_at ASC, wo_id ASC).
- [ ] priority=1 outranks priority=5.
- [ ] WO waited 10 days outranks fresh equal-priority WO.
- [ ] flag_urgent outranks unflagged priority=1.
- [ ] skip_work_order drops below unmarked WO.
- [ ] flag_urgent idempotent (no double-prefix).
- [ ] clear_urgent removes prefix; priority NOT auto-restored.
- [ ] skip_work_order(reason="") clears existing skip prefix.
- [ ] _parse_triage_markers correct for all 4 combos (none/urgent/skip/both).
- [ ] _parts_available_for returns (True, []) when Phase 165 module absent (find_spec None).
- [ ] _parts_available_for returns (assumed, []) when Phase 165 import raises.
- [ ] Phase 165 stub returning [] → parts_ready=True.
- [ ] Phase 165 stub returning all-received → parts_ready=True.
- [ ] Phase 165 stub mixed statuses → parts_ready=False, missing_skus populated.
- [ ] Custom ShopTriageWeights(parts_ready_weight=0.0) disables parts factor.
- [ ] CLI shop triage queue --shop 1 --top 5 emits Rich table ≤5 rows.
- [ ] CLI shop triage queue --json emits valid JSON.
- [ ] CLI shop triage next --shop 1 emits Rich Panel.
- [ ] CLI shop triage next on empty queue: friendly message, non-zero exit.
- [ ] CLI shop triage flag-urgent 42 sets priority=1 + marker.
- [ ] CLI shop triage skip 42 --reason "..." adds marker.
- [ ] CLI shop triage weights --shop 1 --set wait_weight=2.5 persists.
- [ ] CLI shop triage weights --shop 1 --set unknown=1.0 raises ValidationError.
- [ ] Phase 160-163 tests still GREEN.
- [ ] Full regression GREEN.

## Risks

- **Phase 165 contract name mismatch.** Soft-guard calls `list_parts_for_wo(wo_id, db_path=None)`. Phase 165's plan reserves this exact name. Verify at Phase 165 build time.
- **Markers in description collision.** Mechanic typing `[TRIAGE_URGENT]` mid-description could confuse parser. Mitigation: parser anchors at `^`. Mid-description text is safe.
- **Wait-time starvation of urgent work.** If wait_weight tuned too high, aged pri-5 could leapfrog fresh pri-1. Urgent-flag bonus (500) is escape hatch.
- **Parts soft-guard bypass on broken Phase 165.** `except Exception:` is broad. If 165 ships buggy, triage silently treats all as ready. Mitigation: 165's tests catch its own bugs.
- **Migration 028 rollback uses rename-recreate.** SQLite portable; required for SQLite <3.35 compatibility.
- **Per-shop weights JSON drift.** Future phase adding key requires migration. extra="forbid" today.
- **clear_urgent doesn't auto-restore priority.** Deliberate. Mechanic uses `shop work-order update WO_ID --set priority=3` to restore.

## Build Notes

Builder follows CLAUDE.md 15-step. Pattern template: `shop/intake_repo.py` (Phase 160 status guarding) + `shop/work_order_repo.py` (Phase 161 lifecycle).

Key contract: Phase 165 must export `list_parts_for_wo(wo_id, db_path=None)` — this is locked.

`flag_urgent` writes priority=1 via `update_work_order` (Phase 161 whitelist) — never raw SQL.

Architect runs phase-specific tests after Builder returns. Do NOT commit/push from worktree.
