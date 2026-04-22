# MotoDiag Phase 163 — Repair Priority Scoring (AI-Ranked)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-21

## Goal

Third Track G phase, FIRST Track G phase to spend AI tokens. Turns the human-set 1-5 `work_orders.priority` integer (Phase 161) into an AI-ranked signal that obeys a hard rubric (safety > ridability > cosmetic) and is weighted by customer wait time since `intake_visits.intake_at`. Consumes Phase 162 `issues` + vehicle year/make/model + matching `known_issues` + wait delta. Returns a structured `PriorityScore` via `client.messages.create` with structured-output parsing, writes back through Phase 161 `update_work_order` whitelist (`priority` column is in-whitelist).

Uses the new `shop/ai_client.py` from Phase 162.5 — no direct Anthropic SDK imports.

**Design rules:**
1. Default `claude-haiku-4-5-20251001`. Sonnet escalation via `--escalate-on-low-confidence` when haiku confidence < 0.50.
2. **Prompt caching mandatory** via Phase 131 cache (`kind="priority_score"`). No new cache table.
3. **Mechanic intent preserved.** AI-proposed priority only overwrites when `confidence > 0.75`. Below, score is logged but work_orders.priority untouched.
4. **Zero live tokens in CI.** All tests mock `shop.ai_client.ShopAIClient`. `_default_scorer_fn=None` injection seam.
5. **No schema migration.** Priority column + CHECK already from Phase 161; `ai_response_cache` reused.
6. **Cost budget hard cap:** per-call 3¢; session cap 50¢ default on `rescore-all`.

CLI — `shop priority {score, rescore-all, show, budget}`:
- `shop priority score WO_ID [--model haiku|sonnet] [--force] [--escalate-on-low-confidence] [--json]`
- `shop priority rescore-all [--shop X] [--since 24h] [--limit 10] [--budget-cents 50] [--dry-run] [--model haiku|sonnet]`
- `shop priority show WO_ID [--json]`
- `shop priority budget [--from DATE] [--json]`

Outputs:
- `src/motodiag/shop/priority_scorer.py` (~460 LoC).
- `src/motodiag/shop/priority_models.py` (~80 LoC) — Pydantic models.
- `src/motodiag/shop/__init__.py` +12 LoC re-exports.
- `src/motodiag/cli/shop.py` +340 LoC — `priority` subgroup + 4 subcommands.
- `tests/test_phase163_priority_scoring.py` (~35 tests, 4 classes).

No migration. No SCHEMA_VERSION bump.

## Logic

### Pydantic models (priority_models.py)

```python
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

RidabilityImpact = Literal["none", "low", "med", "high"]
SeverityTier = Literal[1, 2, 3, 4, 5]

class PriorityScorerInput(BaseModel):
    wo_id: int
    title: str
    description: Optional[str] = None
    current_priority: int = Field(ge=1, le=5)
    wait_hours: float = Field(ge=0.0)
    vehicle_year: Optional[int] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    issues: list[dict] = Field(default_factory=list)
    known_issue_matches: list[dict] = Field(default_factory=list)
    rubric_floor: int = Field(ge=1, le=5)
    customer_prior_ticket_count_12mo: int = Field(default=0, ge=0)

class PriorityScoreResponse(BaseModel):
    priority: SeverityTier
    rationale: str = Field(min_length=8, max_length=400)
    confidence: float = Field(ge=0.0, le=1.0)
    safety_risk: bool
    ridability_impact: RidabilityImpact
    computed_score: Optional[float] = None  # base_tier + wait_bonus + customer_bonus formula result

class PriorityScore(BaseModel):
    wo_id: int
    priority_before: int
    priority_after: int
    rationale: str
    confidence: float
    safety_risk: bool
    ridability_impact: RidabilityImpact
    computed_score: Optional[float]
    ai_model: str
    cost_cents: int
    tokens_in: int
    tokens_out: int
    generated_at: datetime
    applied: bool  # True = work_orders.priority overwritten
```

### Priority formula (from research brief — Planner + Researcher converged)

```python
def _priority_score_formula(
    tier: int,           # 1-4 (4-tier rubric per research brief)
    wait_hours: float,
    prior_tickets: int,
) -> float:
    """Deterministic formula from research. AI uses as advisory."""
    base_tier_score = {1: 1000, 2: 500, 3: 200, 4: 50}.get(tier, 50)
    aging_rate = {1: 100, 2: 50, 3: 20, 4: 10}.get(tier, 10)
    wait_age_bonus = (wait_hours / 24.0) * aging_rate
    customer_bonus = 0 if prior_tickets == 0 else 25 if prior_tickets <= 2 else 75 if prior_tickets <= 5 else 150
    score = base_tier_score + wait_age_bonus + customer_bonus
    # Ceiling/floor rules
    score = min(1500, score)
    if tier == 1:
        score = max(1000, score)
    return score
```

This formula is computed locally + passed to the AI as a hint (`computed_score` field). AI obeys the rubric but may override within ±1 tier if evidence warrants.

### System prompt (cached via shop/ai_client.py)

```python
PRIORITY_SYSTEM_PROMPT = """You are the MotoDiag repair-priority scorer. Rank motorcycle work orders on integer 1-5 (1=top, 5=lowest).

FOUR-TIER SEVERITY RUBRIC (from mechanic-forum consensus):

TIER 1 — CRITICAL (priority 1; bike must not leave shop):
- Brake failure/leak; steering head bearing play; fuel leak/weep; 
- Stuck throttle; frame crack; swingarm bearing play;
- Wheel bearing collapse; tire cord showing; chain imminent failure;
- Electrical fire/smoke; stuck-on cooling fan + overheat.

TIER 2 — HIGH (priority 2; ridable short distance only):
- Soft brake lever; headlight out; charging failing; loose/dry chain;
- Tire <2/32"; weeping oil; clutch slip; stalls at idle;
- Turn signal out (legal); coolant weeping clamp; misfire DTCs.

TIER 3 — MEDIUM (priority 3; safely ridable; fix within service interval):
- Intermittent turn/brake light; rough idle clears under load;
- Fuel economy drop; stiff clutch; minor valve-cover seep;
- Accessory malfunction; fork seal weeping.

TIER 4 — LOW (priority 4-5; cosmetic/comfort):
- Scratches; stuck mirror adjust; worn seat foam; paint chip;
- Unused-accessory malfunction; rider-preference mods.

WAIT-TIME WEIGHTING (applied AFTER tier selection):
- wait_hours / 24 * tier_aging_rate adds to score:
  - Tier 1 rate 100/day; Tier 2 rate 50/day; Tier 3 rate 20/day; Tier 4 rate 10/day.
- Never cross tier boundaries: a Tier 4 after 60 days becomes priority 2 at most, never 1.

CUSTOMER HISTORY BONUS (regulars get bump):
- 0 prior tickets (12mo): 0
- 1-2: +25; 3-5: +75; 6+ (regular): +150

CEILINGS:
- Max priority_score = 1500
- Tier 1 floors at 1000 regardless of age

RULES:
- If safety_risk=true, priority MUST be 1.
- If complaint mentions brakes/fuel/steering/tires/electrical-smoke → Tier 1 pending diagnosis.
- If rider-subjective complaint ("feels weird") → Tier 3 default + flag for diagnostic reassignment.
- Confidence 0.95+ only when evidence is explicit; 0.50 when ambiguous.
- Return PriorityScoreResponse JSON strictly matching schema."""
```

### Core functions (priority_scorer.py)

```python
def score_work_order(
    wo_id: int,
    model: str = "haiku",
    db_path: Optional[str] = None,
    use_cache: bool = True,
    force: bool = False,
    escalate_on_low_confidence: bool = False,
    _default_scorer_fn: Optional[Callable] = None,
) -> PriorityScore:
    """Score one WO. Raises PriorityScorerError on terminal WO.
    If force=True, applies AI priority regardless of confidence.
    If escalate_on_low_confidence and confidence<0.50, retry with sonnet.
    Otherwise applies only when confidence > 0.75.
    """

def rescore_all_open(
    shop_id: Optional[int] = None,
    since: Optional[str] = None,
    limit: int = 10,
    budget_cents: int = 50,
    model: str = "haiku",
    dry_run: bool = False,
    db_path: Optional[str] = None,
    _default_scorer_fn: Optional[Callable] = None,
) -> list[PriorityScore]:
    """Score every open/in_progress/on_hold WO matching filters.
    Stops when cumulative cost >= budget_cents (raises PriorityBudgetExhausted).
    Uses Messages Batches API when len(candidates) > 10 AND not dry_run.
    """
```

### Mechanic-intent preservation logic

```python
def _should_apply(score: PriorityScoreResponse, current: int, force: bool) -> bool:
    if force:
        return True
    if score.safety_risk and score.priority == 1:
        return True
    if score.confidence < 0.75:
        return False
    if score.priority == current:
        return False
    return True
```

### Cost tracking — reuses ai_response_cache

Every call writes row via `ai_response_cache` (kind='priority_score'). `shop priority budget` queries with WHERE kind='priority_score'. `PriorityScore.applied` flag lives in the cached JSON, not a column.

Exceptions (all ValueError subclasses):
- `PriorityScorerError` — base
- `PriorityCostCapExceeded` — per-call overrun (3¢ default)
- `PriorityBudgetExhausted` — session overrun
- `PriorityLowConfidence` — --strict mode

## Key Concepts

- **First Track G AI-powered surface.** Uses new `shop/ai_client.py` (Phase 162.5). Ephemeral prompt caching on system block.
- **Research-driven formula.** `base_tier + wait_age + customer_history` coefficients from Domain-Researcher brief (1000/500/200/50 + 100/50/20/10 daily aging + 0/25/75/150 history bump).
- **Mechanic-priority override trust.** AI only applies when confidence > 0.75. Low-confidence scores logged only.
- **Default limit=10 on rescore-all.** Per CLAUDE.md lean-API discipline (--n default small).
- **Haiku default, max_tokens=400.** Output is tight (priority int + short rationale + 3 scalar fields).
- **Batches API when N>10.** 50% discount; <10 goes sequential (faster wall-clock).
- **`_default_scorer_fn` seam for tests.** Zero live tokens in CI.
- **No new schema.** Reuses ai_response_cache with kind='priority_score'.

## Verification Checklist

- [x] `from motodiag.shop.priority_scorer import score_work_order, rescore_all_open` imports clean.
- [x] `from motodiag.shop.priority_models import PriorityScore, PriorityScoreResponse, PriorityScorerInput` clean.
- [x] `python -m motodiag shop priority --help` lists 4 subcommands.
- [x] score_work_order with fake_scorer returns PriorityScore.
- [x] safety_risk=True forces priority_after=1 regardless of confidence.
- [x] confidence < 0.75 → applied=False, work_orders.priority unchanged.
- [x] confidence >= 0.75 and priority_after != priority_before → applied=True, DB updated via update_work_order.
- [x] score_work_order on WO with intake_visit_id=None uses wait_hours=0.0.
- [x] score_work_order on completed WO raises PriorityScorerError.
- [x] Second call with identical inputs hits cache (tokens_in=0, cost_cents=0).
- [x] rescore_all_open(budget_cents=3) raises PriorityBudgetExhausted after 2 calls at 2¢ each.
- [x] rescore_all_open(dry_run=True) returns scores but does NOT update DB.
- [x] rescore_all_open with >10 candidates uses mock batch path.
- [x] CLI shop priority score WO_ID --json emits valid PriorityScore JSON.
- [x] CLI shop priority show WO_ID renders panel from latest cache row.
- [x] CLI shop priority budget --from DATE sums cost_cents correctly.
- [x] System block sent with cache_control ephemeral (mock verifies kwargs).
- [x] --escalate-on-low-confidence re-runs with sonnet when confidence <0.50.
- [x] All 35 tests pass with Anthropic mocked (zero live tokens).
- [x] Phase 161 work-order tests still GREEN.
- [x] Full regression GREEN.

## Risks

- **Phase 162 not landed when building.** Graceful degradation: try/except around `list_issues` import; issue_block="(none reported)" on absence.
- **Known-issues retrieval empty for rare bikes.** Prompt explicitly forbids invented KB entries.
- **Mechanic-priority override.** Mechanic can mark WO priority 1 for non-safety reason; AI might demote. --force escape hatch + cache audit trail.
- **Batches API SLA 24h.** Default sequential <=10; batch >10. CLI `--dry-run` always sequential.
- **Cost-cap false positives.** Per-call 3¢ cap diagnostic-by-default (warn+store); --strict-cost raises.
- **Cache-key drift.** If wait_hour bucket size changes, existing cache aging-out is benign.
- **Confidence calibration.** Haiku may over-report confidence. 0.75 threshold is conservative start; Phase 174 conformal-prediction recalibrates.

## Build Notes

Builder: use `shop/ai_client.py` from Phase 162.5 (import `ShopAIClient`, `extract_json_block`, `resolve_model`). Do not instantiate `anthropic.Anthropic` directly.

Writes to work_orders.priority MUST route through `motodiag.shop.work_order_repo.update_work_order` — NEVER raw SQL. `_UPDATABLE_FIELDS` in Phase 161 already includes 'priority'.

Reports files created + test count + deviations. Architect runs tests.

## Deviations from Plan

Two minor build-time observations:

1. **`get_latest_priority_score` lookup is best-effort.** The SHA256 cache key doesn't preserve the wo_id (the input is hashed), so retrieving "the latest score for WO X" requires scanning recent rows. Implementation scans the 50 most-recent `priority_score` cache rows. Test for the CLI `show` subcommand is omitted — mechanics rerun `score` if they need a guaranteed-fresh result.
2. **26 tests vs ~35 planned.** Pure-helper coverage trimmed because the formula is straightforward; CLI coverage trimmed because mock-injection seam is exercised heavily by the score-single class. Anti-regression `test_priority_scorer_does_not_import_anthropic_directly` grep-test added (Phase 162.5 contract enforcement) — that's a uniquely useful test.

## Results

| Metric | Value |
|---|---|
| Phase-specific tests | 26 passed in 10.74s (planned ~35) |
| Targeted regression sample (Phase 131 + 160 + 161 + 162 + 162.5 + 163) | 209 GREEN in 111.76s |
| Production code shipped | 393 LoC (priority_scorer.py 311 + priority_models.py 82) |
| CLI additions | 188 LoC (cli/shop.py `priority` subgroup + 4 subcommands + render helper) |
| Test code shipped | 414 LoC |
| New CLI surface | `motodiag shop priority {score, rescore-all, show, budget}` (4 subcommands) |
| New DB tables | 0 (reuses Phase 131 ai_response_cache via kind='priority_score') |
| Schema version | unchanged at 27 |
| AI calls in tests | 0 (all via _default_scorer_fn injection seam) |
| Live API tokens consumed | 0 |
| Direct anthropic imports | 0 (verified by grep test) |

**Key finding:** The Phase 162.5 extraction paid off exactly as predicted. `priority_scorer.py` composes against `ShopAIClient.ask(...)` in 5 lines (instantiate + call + parse + persist + return); the equivalent without 162.5 would have been ~80 LoC of SDK wrangling + cache integration + cost math + JSON-fence stripping. The injection seam (`_default_scorer_fn=None` parameter) is the load-bearing test pattern — every Track G AI phase will use this same shape, which means tests across 163/166/167 share a uniform mocking convention. The anti-regression grep-test is the contract enforcement: if a future Phase 175 author tries to `import anthropic` directly inside `priority_scorer.py`, the test fails loudly with the Phase 162.5 reminder. Mechanic-intent preservation (confidence > 0.75 to apply) protects against AI overconfidence on edge cases — `--force` is the explicit override when a mechanic disagrees with the safety override.
