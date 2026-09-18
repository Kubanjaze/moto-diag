"""Symptom analysis subsystem — structured intake, categorization, and differential diagnosis.

Two-pass diagnostic approach:
1. Query the knowledge base for known issues matching the vehicle and symptoms.
2. Feed knowledge base matches as context to Claude for AI-enhanced differential diagnosis.
"""




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



