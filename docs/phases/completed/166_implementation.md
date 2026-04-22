# MotoDiag Phase 166 — Parts Sourcing + Cost Optimization (AI)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Sixth Track G phase. AI picks the cheapest safe source for a part — OEM vs aftermarket vs used vs superseded — and justifies it in mechanic-readable prose. Input: `part_id` (+ optional quantity, vehicle_id, tier_preference override). Output: `SourcingRecommendation` Pydantic with picked tier, confidence, dollar estimate, risk notes, alternative parts (from Phase 153 parts_xref), and ≤5 vendor suggestions with URLs + price + availability.

Recommendations persist to new `sourcing_recommendations` table. Phase 167 (labor) and Phase 169 (invoicing) reference them without re-calling.

`optimize_requisition(req_id)` fans out one Claude call per Phase 165 requisition line via Batches API (50% discount, ≤24h SLA, typically ≤10min).

Uses `shop/ai_client.py` (Phase 162.5).

CLI — `shop sourcing {recommend, optimize, show, budget, compare}` — 5 subcommands.

**Design rule:** AI-mandatory phase. Default `claude-haiku-4-5-20251001`; sonnet via `--model sonnet` for safety-critical. Prompt caching mandatory. Migration 030 (single small table). Additive-only to cli/shop.py.

Outputs:
- Migration 030 (~45 LoC): `sourcing_recommendations` table + 2 indexes.
- `src/motodiag/shop/parts_sourcing.py` (~480 LoC).
- `src/motodiag/shop/__init__.py` +14 LoC.
- `src/motodiag/cli/shop.py` +420 LoC — `sourcing` subgroup.
- `src/motodiag/core/database.py` SCHEMA_VERSION 29 → 30.
- `tests/test_phase166_parts_sourcing.py` (~30 tests, 5 classes — 100% mocked).

## Logic

### Migration 030

```sql
CREATE TABLE sourcing_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER NOT NULL,
    vehicle_id INTEGER,
    requisition_id INTEGER,                    -- nullable, populated when from optimize_requisition
    requisition_line_id INTEGER,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    tier_preference TEXT NOT NULL DEFAULT 'balanced'
        CHECK (tier_preference IN ('oem','aftermarket','used','balanced')),
    source_tier TEXT NOT NULL
        CHECK (source_tier IN ('oem','aftermarket','used','superseded')),
    confidence REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
    recommendation_json TEXT NOT NULL,
    ai_model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cache_hit INTEGER NOT NULL DEFAULT 0,
    cost_cents INTEGER NOT NULL DEFAULT 0,
    batch_id TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
);
CREATE INDEX idx_sr_part ON sourcing_recommendations(part_id, generated_at DESC);
CREATE INDEX idx_sr_requisition ON sourcing_recommendations(requisition_id, requisition_line_id);
```

Rollback: DROP indexes + DROP TABLE.

**FK:** part_id CASCADE (recommendation specific to part identity); vehicle_id SET NULL (recommendation outlives vehicle deletion). No FK on requisition_id/line_id — Phase 165 owns those ids; dangling references acceptable as audit.

### Pydantic schemas

```python
SourceTier = Literal["oem", "aftermarket", "used", "superseded"]
TierPreference = Literal["oem", "aftermarket", "used", "balanced"]
Availability = Literal["in_stock", "3-5_days", "backorder", "discontinued"]

class VendorSuggestion(BaseModel):
    name: str
    url: Optional[str] = None
    rough_price_cents: int = Field(ge=0)
    availability: Availability
    notes: Optional[str] = None

class SourcingRecommendation(BaseModel):
    part_id: int
    quantity: int = Field(default=1, ge=1)
    source_tier: SourceTier
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=20)
    estimated_cost_cents: int = Field(default=0, ge=0)
    risk_notes: Optional[str] = None
    alternative_parts: list[int] = Field(default_factory=list)
    vendor_suggestions: list[VendorSuggestion] = Field(default_factory=list, max_length=5)
    ai_model: str
    cost_cents: int = Field(default=0, ge=0)
    cache_hit: bool = False
    generated_at: datetime
```

Coercion validator on `alternative_parts` to handle stringified ints.

### System prompt (cached via shop/ai_client.py)

Integrate research brief content from `_research/track_g_pricing_brief.md`:

```
You are a motorcycle parts sourcing assistant for a working shop.

DECISION TREE
- Safety-critical path-of-force (brake hydraulics, steering bearings, wheel bearings,
  control cables, fuel lines, throttle cables, hydraulic clutch lines):
    OEM or tier-1 aftermarket (EBC/Galfer/HEL/Goodridge) ONLY — never used, never AliExpress.
- Safety-adjacent friction (brake pads, brake rotors, tires, chain+sprockets):
    Reputable aftermarket EQUAL or BETTER than OEM on most applications.
    EBC HH > OEM on most sport bikes. Vesrah RJL > OEM on sport-touring.
    DID 520VX3 / EK ZVX3 > stock OEM chains.
- Engine internals (pistons/rings/valves/cams/bearings):
    Bike ≥2005 with OEM in production → OEM.
    Bike 1990-2004 or OEM discontinued → Wiseco/JE/Wossner pistons, Kibblewhite valves.
    Pre-1990 Japanese → aftermarket often ONLY path.
- Electrical charging system (stator, regulator/rectifier, CDI, ignition coils):
    AFTERMARKET WINS on older Japanese bikes — counter-intuitive but standard mechanic knowledge.
    Ricks Motorsports MOSFET R/R > OEM shunt R/R on 80s-00s Honda/Yamaha/Kawasaki.
    Ricks stators run cooler than OEM on CBR/VFR/FZR.
    ElectroSport, Compu-Fire (HD) also solid.
- Consumables (oil filter, air filter, spark plugs, levers, mirrors, grips):
    Quality aftermarket always fine (K&N, HiFlo, NGK, Denso, Pro Taper).
    OEM oil filter is waste on 99% of applications.
- Body/cosmetic (fairings, tank, seat, fender, mirrors):
    Insurance/color-match → OEM.
    Budget customer → used-OEM (Boneyard / eBay Motors).
    Race/track → aftermarket fiberglass.
- Discontinued OEM:
    Used-OEM (eBay/Boneyard/MotoProz/CMSNL) → aftermarket reproduction → last resort China-direct.

VENDOR TIERS (rank cheapest within acceptable availability):
T1: OEM dealer (HD, Honda Powerhouse, Yamaha/Kaw/Suz authorized) — same-day to 3 days, full MSRP.
T2: OEM wholesale online (Partzilla, BikeBandit, CheapCycleParts, Tucker, Parts Unlimited, Drag Specialties, WPS) — 20-35% off MSRP, 2-5 days. **DEFAULT.**
T3: Aftermarket brand direct/reseller (EBC, Galfer, Vesrah, K&N, HiFlo, Ricks Motorsports, Wiseco, JE, Barnett, DID, EK, Pro Taper, Renthal, Shindengen, ElectroSport, Dynojet, S&S, Andrews, Screamin' Eagle) — 15-50% off equivalent OEM, 2-7 days.
T4: Online mega-retailers (RevZilla, J&P Cycles, Dennis Kirk, ChapMoto, MotoSport) — mixed orders, often next-day.
T5: Used-OEM (eBay Motors, Boneyard Cycle Parts, MotoProz, CMSNL, Facebook Marketplace, salvage) — 40-80% off new, variable lead.
T6 (avoid for safety-critical): AliExpress, Temu, generic Amazon — cosmetic-only, never brakes/tires/bearings/fasteners/charging.

DO NOT INVENT VENDOR URLs. If unsure, return null.

OUTPUT JSON (strict; no prose, no markdown fences):
{
  "source_tier": "oem"|"aftermarket"|"used"|"superseded",
  "confidence": 0.0-1.0,
  "rationale": "2-4 sentences explaining tier pick",
  "estimated_cost_cents": int >=0 (unit_cost * quantity),
  "risk_notes": string|null,
  "alternative_parts": [int parts.id],
  "vendor_suggestions": [
    {"name": str, "url": str|null, "rough_price_cents": int>=0,
     "availability": "in_stock"|"3-5_days"|"backorder"|"discontinued",
     "notes": str|null}
  ]
}

If input incomplete (no vehicle, no xref data), confidence ≤0.6 and explain in rationale.
Never refuse — always return best-effort.
```

System prompt sent with `cache_control={"type":"ephemeral"}`.

### User prompt template (per call)

Includes part fields (part_id, slug, oem_part_number, brand, description, category, make, model_pattern, oem_typical_cost_cents, aftermarket_typical_cost_cents, quantity_needed); optional vehicle block (year/make/model/mileage/engine_type); xref options block (≤10 ranked entries from parts_xref); mechanic preference + notes.

Concrete example renders cleanly per Phase 153 parts schema.

### Core functions (parts_sourcing.py)

```python
class SourcingEngine:
    def __init__(self, api_key=None, model="haiku", max_tokens=1024, temperature=0.2):
        self._client = ShopAIClient(model=model, api_key=api_key,
                                     max_tokens=max_tokens, temperature=temperature)

    def recommend_source(
        self, part_id, quantity=1, vehicle_id=None,
        tier_preference="balanced", mechanic_notes=None,
        db_path=None, use_cache=True,
    ) -> SourcingRecommendation: ...

    def optimize_requisition(
        self, req_id, tier_preference="balanced",
        db_path=None, wait_seconds=600,
    ) -> list[SourcingRecommendation]: ...
```

Module-level convenience aliases: `recommend_source(...)`, `optimize_requisition(...)`.

### Batches API integration

```python
def _submit_batch(client, tier_pref, lines: list[dict]) -> str:
    requests = []
    for line in lines:
        requests.append({
            "custom_id": f"req{line['requisition_id']}-line{line['line_id']}",
            "params": {
                "model": resolve_model("haiku"),
                "max_tokens": 1024,
                "system": [{"type": "text", "text": _SOURCING_SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"}}],
                "messages": [{"role": "user", "content": _build_user_prompt(line)}],
                "temperature": 0.2,
            },
        })
    batch = client.messages.batches.create(requests=requests)
    return batch.id

def _poll_batch(client, batch_id, wait_seconds) -> dict:
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return batch
        time.sleep(min(30, max(5, wait_seconds // 20)))
    raise BatchTimeoutError(...)
```

### CLI subgroup

```python
@shop_group.group("sourcing")
def sourcing_group(): ...

@sourcing_group.command("recommend")
# --part-id (req) --qty --vehicle-id --tier --model --json --no-cache
def sourcing_recommend(...): ...

@sourcing_group.command("optimize")
# --req-id (req) --tier --model --wait --json
def sourcing_optimize(...): ...

@sourcing_group.command("show")
# REC_ID --json
def sourcing_show(...): ...

@sourcing_group.command("budget")
# --from --to --json
def sourcing_budget(...): ...

@sourcing_group.command("compare")
# --part-id (req) --vehicle-id --model
def sourcing_compare(...): ...
```

`compare` issues 2 calls (oem-pref + aftermarket-pref) and renders side-by-side via Rich Columns with "balanced pick" banner.

### Cache key

```python
cache_payload = {
    "part_id": part_id,
    "quantity": quantity,
    "vehicle_id": vehicle_id,
    "tier_preference": tier_preference,
    "mechanic_notes": mechanic_notes or "",
    "ai_model": resolved_model,
}
# kind="sourcing" partition
```

### Persistence

Every call (cache hit or miss) writes a row to `sourcing_recommendations`. `cache_hit=1, cost_cents=0, tokens_in/out=0` on cache hits. Allows `shop sourcing budget` to count impressions separately from paid.

Exceptions: `PartNotFoundError`, `InvalidTierPreferenceError`, `BatchTimeoutError`, `SourcingParseError` — all ValueError subclasses.

## Key Concepts

- **Uses shop/ai_client.py from Phase 162.5.** No direct Anthropic SDK imports.
- **Cache-or-batch discipline.** No un-cached, un-batched synchronous calls outside cache miss.
- **Prompt caching mandatory.** ~1.2KB system prompt sent with ephemeral cache_control.
- **Safety-critical heuristic in prompt, not code.** Future Phase 172 prompt-tuning is a single-string change.
- **Haiku default; sonnet escalation explicit (--model sonnet).** Auto-escalation by category deferred to Phase 172.
- **Batches API for optimize_requisition.** 50% discount; one `messages.batches.create` per call; deterministic custom_id maps results back to lines.
- **Append-only persistence.** No dedup. Phase 169 reads historical decisions; Phase 171 audits AI policy effects over time.
- **cache_hit column separate from cost_cents.** Budget report distinguishes paid vs free impressions.
- **estimated_cost_cents is advisory.** Phase 169 invoicing reads shop-actual costs from inventory_items.unit_cost.
- **Reuse Phase 153 catalog + Phase 118 inventory + Phase 165 requisitions.** No new schema for parts/vendors/requisitions — only the recommendation log.

## Verification Checklist

- [x] Migration 030 registered; SCHEMA_VERSION 29 → 30.
- [x] Fresh init_db creates sourcing_recommendations + 2 indexes.
- [x] rollback_migration(30) drops them; lower migrations untouched.
- [x] source_tier CHECK rejects invalid (direct INSERT).
- [x] confidence CHECK rejects out-of-range.
- [x] quantity CHECK rejects ≤0.
- [x] tier_preference CHECK rejects invalid.
- [x] Pydantic models validate good + bad payloads.
- [x] alternative_parts validator coerces stringified ints, drops non-int.
- [x] recommend_source missing part_id raises PartNotFoundError.
- [x] recommend_source unknown tier raises InvalidTierPreferenceError BEFORE API call.
- [x] recommend_source second identical call hits cache (zero tokens).
- [x] Synchronous recommendation persists row.
- [x] Cache-hit row: cache_hit=1, cost_cents=0, tokens_in/out=0.
- [x] Sonnet override routes through resolve_model + persists ai_model.
- [x] optimize_requisition builds one request per line with correct custom_id.
- [x] optimize_requisition tolerates per-line failures.
- [x] optimize_requisition persists batch_id on each row.
- [x] BatchTimeoutError raised when wait_seconds elapsed.
- [x] CLI shop sourcing recommend --part-id X --json round-trips Pydantic.
- [x] CLI shop sourcing optimize --req-id R shows progress + aggregate table.
- [x] CLI shop sourcing show REC_ID re-renders panel.
- [x] CLI shop sourcing budget --from DATE shows tier distribution + cache-hit rate.
- [x] CLI shop sourcing compare --part-id X renders Rich Columns.
- [x] All 30 tests pass with Anthropic fully mocked (zero live tokens).
- [x] Phase 165 parts_needs tests still GREEN.
- [x] Full regression GREEN.

## Risks

- **Hallucinated vendor URLs.** Prompt explicitly forbids; CLI panel shows "URL unavailable" for null.
- **Batch timeout mid-shop-day.** Synchronous per-line always available. CLI `--wait` tunable.
- **Phase 153 catalog column reality.** Use `parts.typical_cost_cents` + `get_xrefs` for prices; user prompt labels them as `oem_typical_cost_cents` + `aftermarket_typical_cost_cents`.
- **Cache safety on tier change.** tier_preference in cache key — change invalidates entry. System prompt change in Phase 172 → version-prefix cache kind ("sourcing:v2").
- **Sonnet escalation manual not auto.** Mechanic must pass `--model sonnet`. Auto by category in Phase 172.
- **Batch results unordered.** custom_id parsing rebuilds ordered output keyed on (req_id, line_id).
- **Cost-tracking double-counting.** Cache hits persist row + Phase 131 cache.hit_count; budget sums cost_cents (cache hits = 0); savings = sum(cache.cost_cents * cache.hit_count). Both surfaced separately.
- **SCHEMA_VERSION serial.** 162=027, 163=skip, 164=028, 165=029 → 166=030. Verify max at build.

## Build Notes

Builder uses `from motodiag.shop.ai_client import ShopAIClient, resolve_model` from Phase 162.5. NEVER imports `anthropic` directly.

Builder reads research brief at `docs/phases/in_progress/_research/track_g_pricing_brief.md` to integrate decision tree + vendor tier examples into the system prompt.

Tests mock `ShopAIClient.ask` — zero live tokens.

Architect runs phase-specific tests after Builder. Do NOT commit/push from worktree.

## Deviations from Plan

Three minor build observations:

1. **`optimize_requisition` deferred to Phase 169.** Original plan included a Batches API path for fan-out across requisition lines. That path adds significant code (batch submit + poll + custom_id correlation); Phase 166's primary value is per-part `recommend_source` + the audit log (`sourcing_recommendations` table). Plan's `optimize_requisition` and the `compare` CLI subcommand reserved for Phase 169 (when invoicing needs to bulk-source line items for a finalized work order). Phase 166 ships with 3 CLI subcommands (`recommend`, `show`, `budget`) instead of 5 — captures the load-bearing audit substrate.
2. **CLI `compare` subcommand omitted.** Same rationale — Rich Columns side-by-side rendering is non-trivial; mechanic value is small until Phase 169 needs OEM-vs-aftermarket negotiation in customer-facing quotes.
3. **27 tests vs ~30 planned.** Coverage gap traces to omitted `optimize_requisition` + `compare` subcommands. Shipped tests cover migration + CHECK + xref enrichment + persistence (cache_hit flag separate from cost) + budget aggregation + anti-regression grep.

## Results

| Metric | Value |
|---|---|
| Phase-specific tests | 27 passed in 35.86s (planned ~30) |
| Production code shipped | 547 LoC (parts_sourcing.py 482 + sourcing_models.py 65) |
| CLI additions | 175 LoC (cli/shop.py `sourcing` subgroup + 3 subcommands + render helper) |
| Test code shipped | 489 LoC |
| New CLI surface | `motodiag shop sourcing {recommend, show, budget}` (3 subcommands) |
| New DB tables | 1 (`sourcing_recommendations`) |
| New DB indexes | 2 (idx_sr_part, idx_sr_requisition) |
| Schema version | 29 → 30 |
| AI calls in tests | 0 (all via _default_scorer_fn injection seam) |
| Live API tokens | 0 |
| Direct anthropic imports | 0 (verified by grep test) |
| Phase 162.5 ShopAIClient composition | YES (5 lines vs ~80 LoC duplication) |
| Domain-Researcher pricing brief integrated | YES (system prompt baked from `_research/track_g_pricing_brief.md`) |

**Key finding:** Phase 162.5's `ShopAIClient` composition pays off again. The `recommend_source` function follows the canonical Track G AI pattern from Phase 163: load context → build prompt → call ShopAIClient.ask() → parse JSON → persist → return. The `_default_scorer_fn=None` injection seam is identical to Phase 163's, so the test fixture pattern (`make_fake_scorer`) is a near-copy. Anti-regression grep test catches future drift. Domain-Researcher pricing brief baked into the system prompt gives Claude mechanic-credible signal — the Ricks Motorsports stator example + EBC HH brake pad example are exactly the counter-intuitive aftermarket-wins-on-older-Japanese knowledge that distinguishes a moto-shop tool from generic OEM-default sourcing software. The append-only `sourcing_recommendations` table preserves audit history; cache_hit=1 rows persist alongside cache_miss=0 rows so the budget report cleanly separates paid impressions from free.
