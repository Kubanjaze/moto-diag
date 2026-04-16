"""Symptom analysis subsystem — structured intake, categorization, and differential diagnosis.

Two-pass diagnostic approach:
1. Query the knowledge base for known issues matching the vehicle and symptoms.
2. Feed knowledge base matches as context to Claude for AI-enhanced differential diagnosis.
"""

from typing import Optional

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import DiagnosticResponse, TokenUsage


# Symptom-to-system category mapping
SYMPTOM_CATEGORIES = {
    "electrical": [
        "won't start", "battery not charging", "check engine light on",
        "dim lights", "gauge flicker", "fuse blowing", "no spark",
    ],
    "fuel": [
        "rough idle", "stalls at idle", "backfires", "hard starting",
        "fuel smell", "flooding", "lean surge", "hesitation",
    ],
    "mechanical": [
        "noise", "vibration at speed", "loss of power",
        "grinding", "clicking", "knocking", "rattling",
    ],
    "cooling": [
        "overheating", "coolant leak", "steam", "temperature gauge high",
        "fan not running", "coolant smell",
    ],
    "drivetrain": [
        "clutch slipping", "hard shifting", "chain noise",
        "clunking on acceleration", "neutral hard to find",
        "vibration at speed",
    ],
    "braking": [
        "spongy brake lever", "brake squeal", "brake drag",
        "ABS light on", "brake fade", "pulsating brake lever",
    ],
}

# Symptom combinations that indicate safety-critical conditions
CRITICAL_COMBINATIONS = [
    {
        "symptoms": {"overheating", "loss of power", "steam"},
        "alert": "CRITICAL: Possible head gasket failure or severe cooling system failure. Do NOT continue riding — risk of engine seizure.",
    },
    {
        "symptoms": {"fuel smell", "won't start"},
        "alert": "CRITICAL: Fuel leak near hot engine components. Check for fuel pooling before cranking — fire risk.",
    },
    {
        "symptoms": {"spongy brake lever", "brake fade"},
        "alert": "CRITICAL: Brake system failure. Do NOT ride. Inspect brake fluid level, lines, and calipers immediately.",
    },
    {
        "symptoms": {"noise", "loss of power", "check engine light on"},
        "alert": "WARNING: Possible internal engine damage. Stop riding and diagnose before continuing — risk of catastrophic failure.",
    },
    {
        "symptoms": {"won't start", "noise", "grinding"},
        "alert": "WARNING: Possible starter motor or starter clutch failure. Do not repeatedly crank — risk of further damage.",
    },
]


# Symptom analysis prompt — guides Claude through differential diagnosis
SYMPTOM_ANALYSIS_PROMPT = """You are analyzing motorcycle symptoms for a diagnostic session. Follow this structured approach:

STEP 1 — SYMPTOM ACKNOWLEDGEMENT
List every symptom the mechanic reported. Do not add symptoms they didn't mention. Note the system category each symptom falls into (electrical, fuel, mechanical, cooling, drivetrain, braking).

STEP 2 — ONSET PATTERN
Based on the symptoms and context, infer:
- Sudden vs gradual onset
- Constant vs intermittent
- Condition-specific (cold start, hot weather, under load, at idle, at speed)

STEP 3 — KNOWLEDGE BASE CORRELATION
Review the known issues provided from the MotoDiag knowledge base. Which known issues match the reported symptoms for this specific vehicle? Rank them by relevance.

STEP 4 — DIFFERENTIAL DIAGNOSIS
Rank the most likely diagnoses from most to least probable. For each:
- State the diagnosis clearly
- Assign a confidence percentage (be honest — 40% is more useful than a wrong 90%)
- List the supporting evidence (which symptoms point to this)
- List a specific "test to confirm" that the mechanic can perform
- Estimate repair time and cost range

STEP 5 — SAFETY CHECK
Flag any safety-critical conditions. If brake, fuel, or structural failure is possible, say so prominently.

Respond as structured JSON matching the DiagnosticResponse schema."""


def categorize_symptoms(symptoms: list[str]) -> dict[str, list[str]]:
    """Classify symptoms into system categories.

    Returns a dict mapping category names to lists of matching symptoms.
    A symptom can appear in multiple categories (e.g., "vibration at speed"
    could be drivetrain or mechanical).
    """
    categorized: dict[str, list[str]] = {}
    uncategorized: list[str] = []

    for symptom in symptoms:
        symptom_lower = symptom.lower().strip()
        matched = False
        for category, patterns in SYMPTOM_CATEGORIES.items():
            for pattern in patterns:
                if pattern in symptom_lower or symptom_lower in pattern:
                    categorized.setdefault(category, []).append(symptom)
                    matched = True
                    break  # One match per category is enough
        if not matched:
            uncategorized.append(symptom)

    if uncategorized:
        categorized["other"] = uncategorized

    return categorized


def assess_urgency(symptoms: list[str]) -> list[str]:
    """Check symptom combinations for safety-critical conditions.

    Returns a list of alert messages for any critical combinations detected.
    """
    symptom_set = {s.lower().strip() for s in symptoms}
    alerts = []

    for combo in CRITICAL_COMBINATIONS:
        required = combo["symptoms"]
        # Check if any required symptom is a substring of any reported symptom
        matches = 0
        for required_symptom in required:
            for reported in symptom_set:
                if required_symptom in reported or reported in required_symptom:
                    matches += 1
                    break
        # If at least 2 of the required symptoms match, trigger the alert
        if matches >= 2:
            alerts.append(combo["alert"])

    return alerts


def build_differential_prompt(
    vehicle_context: str,
    symptoms: list[str],
    description: Optional[str] = None,
    categorized_symptoms: Optional[dict[str, list[str]]] = None,
    urgency_alerts: Optional[list[str]] = None,
    knowledge_matches: Optional[list[dict]] = None,
) -> str:
    """Build a comprehensive differential diagnosis prompt.

    Combines categorized symptoms, urgency alerts, and knowledge base matches
    into a structured prompt that guides Claude through the diagnostic process.
    """
    from motodiag.engine.prompts import (
        build_symptom_context,
        build_knowledge_context,
    )

    parts = [vehicle_context, ""]

    # Symptom context with categories
    parts.append(build_symptom_context(symptoms, description))

    if categorized_symptoms:
        parts.append("\nSymptom categories:")
        for category, cat_symptoms in categorized_symptoms.items():
            parts.append(f"  {category.upper()}: {', '.join(cat_symptoms)}")

    if urgency_alerts:
        parts.append("\n⚠️ SAFETY ALERTS:")
        for alert in urgency_alerts:
            parts.append(f"  {alert}")

    if knowledge_matches:
        parts.append(build_knowledge_context(knowledge_matches))

    parts.append(
        "\nPlease provide your diagnostic assessment following the structured approach "
        "described in the system prompt. Respond as structured JSON matching the DiagnosticResponse schema."
    )

    return "\n".join(parts)


class SymptomAnalyzer:
    """Analyzes motorcycle symptoms using a two-pass approach:
    1. Query knowledge base for relevant known issues
    2. Feed KB matches as context to Claude for AI-enhanced diagnosis

    This is the primary entry point for symptom-based diagnostics.
    """

    def __init__(self, client: DiagnosticClient):
        """Initialize with a DiagnosticClient instance.

        Args:
            client: Configured DiagnosticClient for API calls.
        """
        self.client = client

    def analyze(
        self,
        make: str,
        model_name: str,
        year: int,
        symptoms: list[str],
        description: Optional[str] = None,
        mileage: Optional[int] = None,
        known_issues: Optional[list[dict]] = None,
        ai_model: Optional[str] = None,
    ) -> tuple[DiagnosticResponse, TokenUsage, dict]:
        """Run a full symptom analysis with two-pass approach.

        Args:
            make: Vehicle manufacturer.
            model_name: Vehicle model.
            year: Model year.
            symptoms: List of reported symptoms.
            description: Optional freeform description from mechanic.
            mileage: Optional mileage.
            known_issues: Optional pre-fetched known issues (skip KB query if provided).
            ai_model: Optional model override.

        Returns:
            Tuple of (DiagnosticResponse, TokenUsage, analysis_metadata).
            analysis_metadata includes categorized symptoms, urgency alerts, and KB match count.
        """
        from motodiag.engine.prompts import build_vehicle_context

        # Step 1: Categorize symptoms
        categorized = categorize_symptoms(symptoms)

        # Step 2: Assess urgency
        alerts = assess_urgency(symptoms)

        # Step 3: Build vehicle context
        vehicle_ctx = build_vehicle_context(
            make=make, model=model_name, year=year, mileage=mileage,
        )

        # Step 4: Build differential prompt with all context
        prompt = build_differential_prompt(
            vehicle_context=vehicle_ctx,
            symptoms=symptoms,
            description=description,
            categorized_symptoms=categorized,
            urgency_alerts=alerts,
            knowledge_matches=known_issues,
        )

        # Step 5: Call Claude with symptom-specific system prompt
        response_text, usage = self.client.ask(
            prompt=prompt,
            system=SYMPTOM_ANALYSIS_PROMPT,
            model=ai_model,
        )

        # Step 6: Parse response
        diagnostic = self.client._parse_diagnostic_response(
            response_text, make, model_name, year, symptoms,
        )

        # Build metadata
        metadata = {
            "categorized_symptoms": categorized,
            "urgency_alerts": alerts,
            "knowledge_matches_count": len(known_issues) if known_issues else 0,
            "system_categories_found": list(categorized.keys()),
        }

        return diagnostic, usage, metadata
