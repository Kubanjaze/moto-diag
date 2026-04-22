# MotoDiag Phase 167 — AI Labor Time Estimation

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-21

## Goal

Seventh Track G phase. AI reads work order (title + description + Phase 162 issues) + vehicle context (make/model/year/mileage) + skill tier, returns structured labor estimate (base hours + skill/mileage adjustments + per-step breakdown + alternatives). Persists to new `labor_estimates` history table AND writes back `work_orders.estimated_hours` via Phase 161 `update_work_order` whitelist (NEVER raw SQL — preserves lifecycle guard).

Uses `shop/ai_client.py` (Phase 162.5).

CLI — `shop labor {estimate, bulk, show, history, reconcile, budget}` — 6 subcommands.

**Design rule:** AI-mandatory. Default `claude-haiku-4-5-20251001`; sonnet via `--model sonnet`. Prompt caching mandatory. Migration 031 (single table). Additive-only to cli/shop.py. **Write-back through Phase 161 whitelist; grep-test enforces no raw SQL.**

Outputs:
- Migration 031 (~95 LoC): `labor_estimates` table + 3 indexes.
- `src/motodiag/shop/labor_estimator.py` (~520 LoC).
- `src/motodiag/shop/__init__.py` +18 LoC.
- `src/motodiag/cli/shop.py` +420 LoC — `labor` subgroup.
- `src/motodiag/core/database.py` SCHEMA_VERSION 30 → 31.
- `tests/test_phase167_labor_estimator.py` (~32 tests, 5 classes — 100% mocked).

## Logic

### Migration 031

```sql
CREATE TABLE labor_estimates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_id INTEGER NOT NULL,
    skill_tier TEXT NOT NULL DEFAULT 'journeyman'
        CHECK (skill_tier IN ('apprentice','journeyman','master')),
    base_hours REAL NOT NULL,
    adjusted_hours REAL NOT NULL,
    skill_adjustment REAL NOT NULL DEFAULT 0.0,
    mileage_adjustment REAL NOT NULL DEFAULT 0.0,
    confidence REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    rationale TEXT NOT NULL,
    breakdown_json TEXT NOT NULL DEFAULT '[]',
    alternatives_json TEXT NOT NULL DEFAULT '[]',
    environment_notes TEXT,
    ai_model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_cents INTEGER NOT NULL DEFAULT 0,
    prompt_cache_hit INTEGER NOT NULL DEFAULT 0,
    user_prompt_snapshot TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wo_id) REFERENCES work_orders(id) ON DELETE CASCADE
);
CREATE INDEX idx_labor_est_wo ON labor_estimates(wo_id);
CREATE INDEX idx_labor_est_generated ON labor_estimates(generated_at);
CREATE INDEX idx_labor_est_model ON labor_estimates(ai_model);
```

Rollback: drop indexes + DROP TABLE.

### Pydantic schemas

```python
class LaborStep(BaseModel):
    step_name: str
    step_hours: float = Field(ge=0.0, le=50.0)
    tools_needed: list[str] = Field(default_factory=list)

class AlternativeEstimate(BaseModel):
    scenario_name: str
    hours: float = Field(ge=0.0, le=100.0)
    notes: str = ""

class LaborEstimate(BaseModel):
    base_hours: float = Field(ge=0.0, le=100.0)
    adjusted_hours: float = Field(ge=0.0, le=100.0)
    skill_adjustment: float = Field(ge=-1.0, le=2.0)
    mileage_adjustment: float = Field(ge=-0.5, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1, max_length=2000)
    breakdown: list[LaborStep] = Field(default_factory=list)
    alternative_estimates: list[AlternativeEstimate] = Field(default_factory=list)
    skill_tier: Literal["apprentice", "journeyman", "master"] = "journeyman"
    environment_notes: Optional[str] = Field(default=None, max_length=500)

class ReconciliationReport(BaseModel):
    wo_id: int
    estimated_hours: float
    actual_hours: float
    delta_hours: float
    delta_pct: Optional[float]    # None if estimated was 0
    bucket: Literal["under", "within", "over"]
    notes: str
```

### System prompt (cached via shop/ai_client.py)

Integrate baseline labor table from `_research/track_g_pricing_brief.md`:

```
You are a veteran motorcycle shop foreman estimating wrench time. Return JSON only.

LABOR NORMS RUBRIC (journeyman, well-equipped shop):
- Oil + filter change (most bikes): 0.5h
- Chain + sprocket replacement: 1.0-1.5h
- Brake pad replacement per wheel: 1.0-1.5h
- Brake fluid flush + bleed (both circuits): 0.75-1.25h
- Coolant flush: 0.75h
- Spark plug replacement (accessible): 0.5h/plug; (buried under tank): +1.0h
- Battery replacement: 0.25h
- Tire replacement (off-bike mount): 0.75h/tire + 0.25h/wheel R&R
- Harley valve adjustment (air-cooled V-twin): 2.0-3.0h
- Honda CBR / Yamaha R carb sync (4-cyl): 1.5-2.0h
- FI throttle-body sync: 0.75-1.25h
- Fork seal replacement (pair): 2.0-3.0h
- Clutch cable: 0.5-0.75h
- Clutch plate (Japanese wet): 2.0-3.5h; HD dry primary 1.5h
- Timing chain/tensioner service: 3.0-5.0h
- Cam chain tensioner (Japanese twins): 1.5-2.5h
- Top-end rebuild: 8-14h
- Stator / R/R swap: 1.0-2.0h
- Fuel pump (in-tank): 1.25-2.0h
- Wheel bearing replacement per wheel: 1.0-1.5h

PER-PLATFORM ADJUSTMENTS (from research brief):
- HD TC/M8: pushrod (no shim), valve check 1.5h, valve adjust pushrod
- Honda CBR/I4: shim-under-bucket valve adjust 5.0h
- Yamaha R1/R6: 6.0h shim adjust
- Suzuki GSX-R: 5.5h
- Kawasaki ZX: 5.5h
- Dual-sport (KLR/DR/XR): screw-adjust simpler, 2.0h
- Cruiser mid-Japanese: 3.5h

SKILL TIER ADJUSTMENTS (multiplicative):
- apprentice (0-2yr): +25% (skill_adjustment = +0.25)
- journeyman (3-8yr): 0% (baseline)
- master (8+yr): -15% (skill_adjustment = -0.15)

MILEAGE / ENVIRONMENT (additive on skill-adjusted):
- > 50,000 mi: +10% (mileage_adjustment = 0.10)
- > 100,000 mi: +20% (mileage_adjustment = 0.20)
- Coastal/Florida/salt: add alternative_estimates entry "seized-fastener scenario" +30-50%
- Tropical humidity / long-stored fuel system: note in environment_notes
- Prior-bad-work signs (stripped Phillips, JB Weld, mismatched fasteners): +25% (alternative entry)

OUTPUT JSON SCHEMA (strict — match field names exactly):
{
  "base_hours": float,
  "adjusted_hours": float,
  "skill_adjustment": float,
  "mileage_adjustment": float,
  "confidence": float in [0,1],
  "rationale": string,
  "breakdown": [{"step_name": str, "step_hours": float, "tools_needed": [str]}],
  "alternative_estimates": [{"scenario_name": str, "hours": float, "notes": str}],
  "skill_tier": "apprentice"|"journeyman"|"master",
  "environment_notes": string|null
}

RULES:
- adjusted_hours MUST equal base_hours * (1 + skill_adjustment) * (1 + mileage_adjustment),
  rounded to 2 decimals. Include math in rationale.
- Multi-job WO (e.g. "oil change + brake pads"): SUM rubric lines; breakdown one entry per sub-job.
- Unknown/ambiguous job → confidence ≤ 0.5 + explain in rationale.
- Return JSON ONLY. No markdown. No prose outside JSON.
```

System block sent with `cache_control={"type":"ephemeral"}`.

### User prompt template

```
Work Order #{wo_id}
Shop: {shop_name}
Vehicle: {year} {make} {model} — {mileage} miles
Skill tier requested: {skill_tier}

Title: {title}
Description: {description_or_none}

Linked issues (Phase 162):
{formatted_issues_or_none}

Environment hint (optional): {environment_hint_or_none}

Estimate the wrench time. Return JSON only.
```

`formatted_issues_or_none`: numbered list `1. [severity] title — description_truncated_200c`, or `(none)`.

### Core functions

```python
def estimate_labor(
    wo_id: int,
    skill_tier: Literal["apprentice","journeyman","master"] = "journeyman",
    model: str = "haiku",
    environment_hint: Optional[str] = None,
    write_back: bool = True,
    db_path: Optional[str] = None,
    client: Optional["ShopAIClient"] = None,    # injectable for tests
) -> LaborEstimate:
    """
    1. require_work_order(wo_id) → row + denormalized
    2. list_issues(wo_id) via try/except ImportError → enrichment
    3. Build system + user prompts
    4. shop.ai_client.ShopAIClient.ask(...) with prompt caching
    5. Parse JSON via extract_json_block + LaborEstimate validation
    6. Math consistency guard: adjusted ≈ base * (1+skill) * (1+mileage), within 0.01h.
       On mismatch retry once at temp 0.1; second failure → LaborEstimateMathError.
    7. persist_labor_estimate(...)
    8. If write_back: update_work_order(wo_id, {"estimated_hours": estimate.adjusted_hours})
       — NEVER raw SQL.
    9. Return LaborEstimate.
    """

def bulk_estimate_open_wos(
    shop_id: int,
    model: str = "haiku",
    skill_tier: Literal["apprentice","journeyman","master"] = "journeyman",
    force: bool = False,
    db_path: Optional[str] = None,
    client: Optional["ShopAIClient"] = None,
) -> list[LaborEstimate]:
    """list_work_orders(shop_id, status=['open','in_progress']);
    skip WOs with estimated_hours set unless force=True;
    sequential calls (Batches API not used this phase)."""

def reconcile_with_actual(wo_id, db_path=None) -> ReconciliationReport:
    """Pure arithmetic — no AI call. Requires WO completed + actual_hours set.
    Computes delta_hours, delta_pct, bucket ('under'/'within'/'over' at ±20%)."""

def persist_labor_estimate(
    wo_id, estimate, ai_model, tokens_in, tokens_out, cost_cents,
    prompt_cache_hit, user_prompt_snapshot, db_path=None,
) -> int: ...

def load_labor_estimate(estimate_id, db_path=None) -> Optional[dict]: ...
def list_labor_estimates(wo_id=None, since=None, limit=50, db_path=None) -> list[dict]: ...
def labor_budget(shop_id=None, since=None, db_path=None) -> dict: ...
```

### CLI subgroup

```python
@shop_group.group("labor")
def labor_group(): ...

@labor_group.command("estimate")
# WO_ID --skill-tier --model --environment --no-write-back --json
def labor_estimate(...): ...

@labor_group.command("bulk")
# --shop (req) --skill-tier --model --force --json
def labor_bulk(...): ...

@labor_group.command("show")
# ESTIMATE_ID --json
def labor_show(...): ...

@labor_group.command("history")
# WO_ID --json (all past + actual_hours + delta if set)
def labor_history(...): ...

@labor_group.command("reconcile")
# WO_ID --json
def labor_reconcile(...): ...

@labor_group.command("budget")
# --shop --from --json
def labor_budget_cmd(...): ...
```

### Mandatory write-back path

```python
from motodiag.shop.work_order_repo import update_work_order

# After persist_labor_estimate succeeds:
if write_back:
    update_work_order(
        wo_id=wo_id,
        updates={"estimated_hours": float(estimate.adjusted_hours)},
        db_path=db_path,
    )
```

NEVER `UPDATE work_orders SET estimated_hours = ? WHERE id = ?` directly.

## Key Concepts

- **Uses shop/ai_client.py from Phase 162.5.** No direct Anthropic SDK imports.
- **AI labor rubric as cached system prompt.** Norms + skill math + output schema in static system prompt with ephemeral cache_control. Shop running 20 estimates in morning hits cache on #2-#20.
- **Whitelist-only write-back.** Calls Phase 161 `update_work_order({estimated_hours: ...})` — NEVER raw SQL. Preserves lifecycle guard. Reuses `_validate_hours` for free.
- **Separate history table with full audit.** model, tokens, cost, cache_hit, rationale, breakdown JSON, truncated user_prompt_snapshot. Audit trail for disputes.
- **Reconciliation = pure arithmetic.** No AI cost. Future phase can use deltas as few-shot exemplars.
- **Graceful Phase 162 degradation.** try/except ImportError on list_issues. Estimator works on title+description alone.
- **Bulk = sequential (not batched).** Volume per shop per day is dozens. Phase 170+ can layer batch mode.
- **Math consistency guard with single retry.** adjusted_hours = base * (1+skill) * (1+mileage), ±0.01h tolerance. Retry at temp 0.1; second failure raises LaborEstimateMathError.
- **Reconcile NEVER mutates.** Read-only report. One-way: estimate → WO → complete → reconcile → read.
- **Default temp 0.2.** Labor norms should be stable, not creative.
- **max_tokens=2048.** Breakdown can be lengthy.

## Verification Checklist

- [ ] Migration 031 registered; SCHEMA_VERSION 30 → 31.
- [ ] Fresh init_db creates labor_estimates + 3 indexes.
- [ ] rollback_migration(31) drops cleanly; 030 untouched.
- [ ] CHECK on skill_tier rejects invalid (direct INSERT).
- [ ] CHECK on confidence rejects out-of-range.
- [ ] LaborEstimate Pydantic validates valid + rejects out-of-range.
- [ ] estimate_labor with mocked client returns LaborEstimate.
- [ ] estimate_labor calls update_work_order with {"estimated_hours": X} (mock asserts call args; NOT raw SQL).
- [ ] estimate_labor with write_back=False does NOT call update_work_order.
- [ ] estimate_labor persists labor_estimates row with tokens/cost/model/cache_hit populated.
- [ ] Math consistency guard: mismatched adjusted_hours triggers retry; second failure raises LaborEstimateMathError.
- [ ] skill_tier=apprentice → skill_adjustment ≈ +0.25.
- [ ] skill_tier=master → skill_adjustment ≈ -0.15.
- [ ] mileage > 50k → mileage_adjustment ≥ 0.10.
- [ ] bulk_estimate_open_wos iterates only open/in_progress; skips with estimated_hours set unless force=True.
- [ ] reconcile_with_actual raises on non-completed WO.
- [ ] reconcile_with_actual returns correct bucket at ±20%.
- [ ] list_labor_estimates(wo_id=X) newest-first; filters by since.
- [ ] labor_budget aggregates total_cost_cents + tokens correctly.
- [ ] System prompt sent with cache_control={"type":"ephemeral"} (mock verifies).
- [ ] Phase 162 issues block formats correctly when present; "(none)" when absent.
- [ ] CLI shop labor estimate WO_ID end-to-end with mock returns expected output.
- [ ] CLI shop labor bulk --shop X --force re-estimates even when set.
- [ ] CLI shop labor show ESTIMATE_ID --json emits valid JSON.
- [ ] CLI shop labor history WO_ID shows past + delta vs actual.
- [ ] CLI shop labor reconcile WO_ID works on completed; clean error otherwise.
- [ ] CLI shop labor budget --shop X --from 7d renders Rich panel.
- [ ] **GREP TEST:** `grep -E "UPDATE work_orders" src/motodiag/shop/labor_estimator.py` returns ZERO hits.
- [ ] Phase 161 work-order tests still GREEN.
- [ ] Phase 160 shop tests still GREEN.
- [ ] Full regression GREEN.
- [ ] Zero live API tokens (all mocked).

## Risks

- **AI math inconsistency.** Validate adjusted ≈ base * (1+skill) * (1+mileage); retry once at temp 0.1; raise on second failure. Rubric encoded in prompt to prime correct math first attempt.
- **Rubric coverage gaps.** Prompt instructs confidence ≤0.5 outside rubric — clear "don't trust this" signal.
- **Shared AI-client boilerplate.** Phase 162.5 micro-phase already extracted ShopAIClient. This phase imports from it.
- **Phase 162 issues may not exist when building.** try/except ImportError; "(none)" fallback.
- **Write-back may clobber manual estimates.** CLI `--no-write-back` flag; bulk skips set values unless `--force`. labor_estimates history preserves the AI value.
- **Cost creep in bulk mode.** Haiku cheap; cache cuts 90%; budget surfaces spend. Bulk prompts "about to call AI N times, confirm?" unless `--yes`.
- **actual_hours reliability.** Phase 161 complete_work_order accepts actual_hours optional. If skipped, reconcile raises ReconcileMissingDataError. Phase 170 timer integration solves.
- **Reopen + estimate history.** Reopened WOs get new estimate rows; history shows both pre-completion + post-reopen. Correct audit.
- **SCHEMA_VERSION serial.** 162=027, 163=skip, 164=028, 165=029, 166=030 → 167=031. Verify max at build.

## Build Notes

Builder uses `from motodiag.shop.ai_client import ShopAIClient, extract_json_block, resolve_model` from Phase 162.5. NEVER imports `anthropic` directly.

Builder reads `docs/phases/in_progress/_research/track_g_pricing_brief.md` to integrate baseline labor table + per-platform adjustments into system prompt.

Tests mock `ShopAIClient.ask` — zero live tokens.

**CRITICAL:** Builder must NOT write raw SQL against work_orders. Write-back path must call `update_work_order` from Phase 161. Verification checklist enforces this via grep.

Architect runs phase-specific tests + grep test after Builder. Do NOT commit/push from worktree.
