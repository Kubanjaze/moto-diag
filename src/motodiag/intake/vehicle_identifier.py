"""Photo-based vehicle identification.

Phase 122: takes a motorcycle photo and returns VehicleGuess with
approximate make/model/year_range/engine_cc_range/confidence. Uses
Claude Haiku 4.5 by default; escalates to Sonnet when Haiku confidence
is below threshold. Enforces per-tier monthly quotas and maintains a
sha256 image cache so accidental re-uploads cost zero tokens.

Image bytes never persist — only the preprocessed-bytes sha256 hash.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from motodiag.core.database import get_connection
from motodiag.engine.client import MODEL_ALIASES
from motodiag.intake.models import (
    IdentifyKind,
    IntakeError,
    IntakeQuota,
    QuotaExceededError,
    VehicleGuess,
)


# --- Constants (easily tuned; future Track T 343 moves to DB config) ---

# Phase 191D: import-from-SSOT instead of literal pin (F9 subspecies (ii)
# generalized; F20 mitigation; same family as Phase 191B C2 fix-cycle-4).
# This file is data point 1 toward the F24 promotion criterion (extend
# rule scope from tests/** to src/**); a second production-side hit
# triggers F24 escalation to its own phase.
HAIKU_MODEL_ID = MODEL_ALIASES["haiku"]
SONNET_MODEL_ID = MODEL_ALIASES["sonnet"]

MONTHLY_CAPS: dict[str, Optional[int]] = {
    "individual": 20,
    "shop": 200,
    "company": None,  # unlimited
}

BUDGET_ALERT_THRESHOLD = 0.80  # 80% of monthly cap
SONNET_ESCALATION_THRESHOLD = 0.5  # Haiku confidence below this → retry with Sonnet

MAX_IMAGE_DIM = 1024  # Pixels on the longer side; preserves aspect ratio
JPEG_QUALITY = 85

# Approximate API pricing (cents per million tokens — order-of-magnitude accuracy is enough)
_MODEL_COSTS_CENTS_PER_MTOK = {
    "haiku": {"input": 100, "output": 500},    # $1 input / $5 output per MTok
    "sonnet": {"input": 300, "output": 1500},  # $3 input / $15 output per MTok
}

_IDENTIFIER_SYSTEM_PROMPT = (
    "You are a motorcycle identification assistant. Given one photograph of a "
    "motorcycle, identify the make, model, likely year range, and engine "
    "displacement range.\n\n"
    "Use every visual cue available: tank badge or decal, engine layout "
    "(V-twin / inline / parallel / boxer / single / electric), fairing "
    "silhouette, exhaust routing, fender shape, frame geometry, wheel design, "
    "instrument cluster, headlight style.\n\n"
    "Year-range width should reflect uncertainty — a generic-looking bike gets "
    "a wider range (5-10 years); a distinctive one-year model gets a tight "
    "range (1-2 years). Engine cc range should be similarly calibrated.\n\n"
    "If the bike is electric, set powertrain_guess='electric' and "
    "engine_cc_range=null.\n\n"
    "Respond ONLY with a single JSON object matching this schema — no prose, "
    "no markdown fences:\n"
    "{\n"
    '  "make": "string",\n'
    '  "model": "string",\n'
    '  "year_low": int, "year_high": int,\n'
    '  "engine_cc_low": int|null, "engine_cc_high": int|null,\n'
    '  "powertrain_guess": "ice"|"electric"|"hybrid",\n'
    '  "confidence": float_between_0_and_1,\n'
    '  "reasoning": "one or two sentences"\n'
    "}"
)


# --- Helpers (module-level so they are unit-testable without the class) ---


def _preprocess_image(path: Path | str) -> tuple[bytes, str]:
    """Resize to MAX_IMAGE_DIM on the longer side, re-encode as JPEG quality 85,
    flatten PNG alpha to white, and return (jpeg_bytes, sha256_hex).

    Raises ValueError on bad path; RuntimeError if Pillow is not installed.
    """
    p = Path(path)
    if not p.exists():
        raise ValueError(f"Image file not found: {p}")
    if not p.is_file():
        raise ValueError(f"Image path is not a file: {p}")

    try:
        from PIL import Image, ImageOps
    except ImportError as e:
        raise RuntimeError(
            "Pillow is required for photo intake. Install with:  "
            "pip install 'motodiag[vision]'"
        ) from e

    try:
        img = Image.open(p)
    except Exception as e:
        raise ValueError(f"Unsupported or unreadable image: {p} ({e})") from e

    # Flatten transparency to white background
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # ImageOps.contain fits within a bounding box without upscaling
    img = ImageOps.contain(img, (MAX_IMAGE_DIM, MAX_IMAGE_DIM))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    jpeg_bytes = buf.getvalue()

    sha = hashlib.sha256(jpeg_bytes).hexdigest()
    return jpeg_bytes, sha


def _compute_cost_cents(model: str, tokens_input: int, tokens_output: int) -> int:
    """Approximate API cost in cents (rounded up to nearest whole cent).

    Rates are order-of-magnitude accurate; exact billing is not this module's job.
    """
    rates = _MODEL_COSTS_CENTS_PER_MTOK.get(model, _MODEL_COSTS_CENTS_PER_MTOK["haiku"])
    in_cost = tokens_input * rates["input"] / 1_000_000
    out_cost = tokens_output * rates["output"] / 1_000_000
    # Round up so zero-cent calls only happen when both token counts are zero
    total = in_cost + out_cost
    if total == 0:
        return 0
    import math
    return max(1, math.ceil(total))


def _parse_guess_json(raw: str, model_used: str, image_hash: str) -> VehicleGuess:
    """Parse a model JSON response into a VehicleGuess. Raises IntakeError on bad JSON."""
    # Strip common wrapping (some models add ```json fences despite instructions)
    text = raw.strip()
    if text.startswith("```"):
        # Drop the opening fence line + closing fence
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as e:
        raise IntakeError(f"Model did not return valid JSON: {e}. Raw: {raw[:200]!r}") from e

    required = {"make", "model", "year_low", "year_high", "confidence"}
    missing = required - data.keys()
    if missing:
        raise IntakeError(f"Model JSON missing required keys: {sorted(missing)}")

    engine_low = data.get("engine_cc_low")
    engine_high = data.get("engine_cc_high")
    engine_range: Optional[tuple[int, int]] = None
    if engine_low is not None and engine_high is not None:
        engine_range = (int(engine_low), int(engine_high))

    return VehicleGuess(
        make=str(data["make"]).strip(),
        model=str(data["model"]).strip(),
        year_range=(int(data["year_low"]), int(data["year_high"])),
        engine_cc_range=engine_range,
        powertrain_guess=str(data.get("powertrain_guess", "ice")).lower(),
        confidence=float(data["confidence"]),
        reasoning=str(data.get("reasoning", "")).strip(),
        model_used=model_used,
        image_hash=image_hash,
    )


# --- User tier lookup ---


def _get_user_tier(user_id: int, db_path: str | None = None) -> str:
    """Return the subscription tier for a user, or 'individual' as fallback.

    Reads the most recent active/trialing subscription row. Missing row → individual.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """SELECT tier FROM subscriptions
               WHERE user_id = ? AND status IN ('active', 'trialing')
               ORDER BY started_at DESC, id DESC LIMIT 1""",
            (user_id,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
    return "individual"


# --- VehicleIdentifier ---


class VehicleIdentifier:
    """Photo-based vehicle identification orchestrator.

    Typical usage:

        identifier = VehicleIdentifier(db_path=db)
        guess = identifier.identify("/path/to/bike.jpg", user_id=42)
        print(guess.make, guess.model, guess.year_range, guess.confidence)
    """

    def __init__(
        self,
        vision_call=None,
        default_model: str = "haiku",
        sonnet_escalation_threshold: float = SONNET_ESCALATION_THRESHOLD,
        db_path: Optional[str] = None,
    ) -> None:
        """
        Args:
            vision_call: Injectable callable for the Claude Vision API. Signature:
                (image_bytes: bytes, hints: Optional[str], model_id: str) ->
                tuple[str_raw_response, tokens_input: int, tokens_output: int]
                Left None in production (lazy-bound to `_default_vision_call`).
                In tests, inject a mock that returns canned responses without burning tokens.
            default_model: 'haiku' (default) or 'sonnet'.
            sonnet_escalation_threshold: Haiku confidence below this triggers a Sonnet retry.
            db_path: SQLite path override.
        """
        self._vision_call = vision_call
        self._default_model = default_model
        self._sonnet_threshold = sonnet_escalation_threshold
        self._db_path = db_path

    # --- Quota ---

    def check_quota(self, user_id: int) -> IntakeQuota:
        """Return current-month quota status for a user."""
        tier = _get_user_tier(user_id, self._db_path)
        monthly_limit = MONTHLY_CAPS.get(tier, MONTHLY_CAPS["individual"])
        used = self._count_this_month(user_id)

        if monthly_limit is None:
            return IntakeQuota(
                tier=tier,
                monthly_limit=None,
                used_this_month=used,
                remaining=None,
                percent_used=0.0,
            )

        remaining = max(0, monthly_limit - used)
        percent = used / monthly_limit if monthly_limit > 0 else 0.0
        return IntakeQuota(
            tier=tier,
            monthly_limit=monthly_limit,
            used_this_month=used,
            remaining=remaining,
            percent_used=round(percent, 4),
        )

    def _count_this_month(self, user_id: int) -> int:
        """Count identify-kind usage rows in the current calendar month for this user."""
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1).isoformat()
        with get_connection(self._db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM intake_usage_log "
                "WHERE user_id = ? AND kind = ? AND created_at >= ?",
                (user_id, IdentifyKind.IDENTIFY.value, month_start),
            )
            return cursor.fetchone()[0]

    # --- Main identify flow ---

    def identify(
        self,
        image_path: str | Path,
        user_id: int = 1,
        hints: Optional[str] = None,
        force_model: Optional[str] = None,
    ) -> VehicleGuess:
        """Identify a motorcycle from a photo.

        Orchestration:
          1. Check quota (QuotaExceededError if exhausted)
          2. Preprocess image → resize 1024px, sha256 hash
          3. Cache lookup — return cached guess if same hash + model seen before
          4. Call Claude Vision (Haiku unless force_model='sonnet')
          5. If Haiku confidence < threshold → retry with Sonnet
          6. Log usage to intake_usage_log
          7. Attach budget alert if this call crossed 80% threshold

        Raises:
            QuotaExceededError: user at their monthly cap
            ValueError: bad image path or format
            RuntimeError: Pillow not installed
            IntakeError: bad API response or malformed JSON
        """
        # Quota pre-check
        quota_before = self.check_quota(user_id)
        if quota_before.monthly_limit is not None and quota_before.remaining == 0:
            raise QuotaExceededError(
                tier=quota_before.tier,
                used=quota_before.used_this_month,
                limit=quota_before.monthly_limit,
            )

        # Preprocess
        jpeg_bytes, image_hash = _preprocess_image(image_path)

        # Cache lookup
        cached = self._cache_lookup(image_hash)
        if cached is not None:
            self._log_usage(
                user_id=user_id,
                kind=IdentifyKind.IDENTIFY,
                model_used=cached.model_used,
                confidence=cached.confidence,
                image_hash=image_hash,
                tokens_input=0,
                tokens_output=0,
            )
            cached.cached = True
            self._maybe_attach_alert(user_id, quota_before, cached)
            return cached

        # Vision call — Haiku first (or Sonnet if forced)
        initial_model = force_model or self._default_model
        guess = self._run_vision(jpeg_bytes, hints, initial_model, image_hash, user_id)

        # Escalation: low Haiku confidence → retry with Sonnet
        if (
            initial_model == "haiku"
            and guess.confidence < self._sonnet_threshold
            and force_model is None
        ):
            guess = self._run_vision(jpeg_bytes, hints, "sonnet", image_hash, user_id)

        self._maybe_attach_alert(user_id, quota_before, guess)
        return guess

    def _run_vision(
        self,
        image_bytes: bytes,
        hints: Optional[str],
        model: str,
        image_hash: str,
        user_id: int,
    ) -> VehicleGuess:
        """Single vision call + parse + log. Retries once on malformed JSON."""
        model_id = SONNET_MODEL_ID if model == "sonnet" else HAIKU_MODEL_ID
        call = self._vision_call or _default_vision_call

        # First attempt
        raw, tin, tout = call(image_bytes, hints, model_id)
        try:
            guess = _parse_guess_json(raw, model_used=model, image_hash=image_hash)
        except IntakeError:
            # One retry with reinforced JSON-only instruction
            retry_hints = (hints or "") + "\n\nIMPORTANT: Respond ONLY with valid JSON. No prose, no markdown."
            raw, tin2, tout2 = call(image_bytes, retry_hints, model_id)
            tin += tin2
            tout += tout2
            guess = _parse_guess_json(raw, model_used=model, image_hash=image_hash)

        self._log_usage(
            user_id=user_id,
            kind=IdentifyKind.IDENTIFY,
            model_used=model,
            confidence=guess.confidence,
            image_hash=image_hash,
            tokens_input=tin,
            tokens_output=tout,
        )
        return guess

    # --- Cache + logging ---

    def _cache_lookup(self, image_hash: str) -> Optional[VehicleGuess]:
        """Return the most recent non-cached guess for this image_hash, or None.

        Only real API calls (where tokens_input > 0) are cached — zero-token
        cache-hit rows do not shadow the original.
        """
        with get_connection(self._db_path) as conn:
            cursor = conn.execute(
                "SELECT model_used, confidence FROM intake_usage_log "
                "WHERE image_hash = ? AND kind = ? AND tokens_input > 0 "
                "ORDER BY created_at DESC, id DESC LIMIT 1",
                (image_hash, IdentifyKind.IDENTIFY.value),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            # We don't store the full VehicleGuess in the log — just reconstruct a
            # minimal cached marker. The cache's job is to avoid burning tokens;
            # if the caller needs the full original prose we'd have to add a
            # guess_json column later.
            return VehicleGuess(
                make="(cached)",
                model="(cached)",
                year_range=(0, 0),
                confidence=row[1] or 0.0,
                model_used=row[0] or "haiku",
                image_hash=image_hash,
                cached=True,
                reasoning="Cached result — original guess text not preserved in log.",
            )

    def _log_usage(
        self,
        user_id: int,
        kind: IdentifyKind,
        model_used: Optional[str],
        confidence: Optional[float],
        image_hash: Optional[str],
        tokens_input: int,
        tokens_output: int,
    ) -> None:
        cost = _compute_cost_cents(model_used or "haiku", tokens_input, tokens_output)
        with get_connection(self._db_path) as conn:
            conn.execute(
                """INSERT INTO intake_usage_log
                   (user_id, kind, model_used, confidence, image_hash,
                    tokens_input, tokens_output, cost_cents)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id, kind.value, model_used, confidence, image_hash,
                    tokens_input, tokens_output, cost,
                ),
            )

    def _maybe_attach_alert(
        self,
        user_id: int,
        quota_before: IntakeQuota,
        guess: VehicleGuess,
    ) -> None:
        """Attach a budget alert string to the guess iff this call crossed the 80% threshold."""
        if quota_before.monthly_limit is None:
            return  # Unlimited tier, no alerts

        quota_after = self.check_quota(user_id)
        before_pct = quota_before.percent_used
        after_pct = quota_after.percent_used
        if before_pct < BUDGET_ALERT_THRESHOLD <= after_pct:
            guess.alert = (
                f"You've used {int(after_pct * 100)}% of your monthly photo-ID quota "
                f"({quota_after.used_this_month}/{quota_after.monthly_limit}). "
                f"Consider upgrading your tier."
            )


# --- Default vision call (production) ---


def _default_vision_call(
    image_bytes: bytes,
    hints: Optional[str],
    model_id: str,
) -> tuple[str, int, int]:
    """Default production vision caller.

    Separate from VehicleIdentifier so tests can inject a mock without needing
    anthropic installed. Lazy-imports anthropic so the intake package can load
    without the AI extra.
    """
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic SDK required for live vision calls. Install with:  "
            "pip install 'motodiag[ai]'"
        ) from e

    client = Anthropic()
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")

    user_content: list[dict] = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64,
            },
        },
    ]
    user_text = (
        "Identify this motorcycle. Respond with the JSON object only."
        if not hints else
        f"Identify this motorcycle. Additional hints from the user: {hints}\n\n"
        f"Respond with the JSON object only."
    )
    user_content.append({"type": "text", "text": user_text})

    response = client.messages.create(
        model=model_id,
        max_tokens=1024,
        system=_IDENTIFIER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text_out = ""
    for block in response.content:
        if hasattr(block, "text"):
            text_out += block.text

    return (
        text_out,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
