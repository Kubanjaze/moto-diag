"""System prompts and context builders for the diagnostic engine."""

from typing import Optional


DIAGNOSTIC_SYSTEM_PROMPT = """You are MotoDiag, an expert motorcycle diagnostic AI assistant built for professional mechanics. You combine deep knowledge of all major motorcycle manufacturers (Harley-Davidson, Honda, Yamaha, Kawasaki, Suzuki) across all eras — vintage air-cooled to modern ride-by-wire — with systematic diagnostic reasoning.

Your diagnostic approach:
1. LISTEN to the symptoms exactly as described — don't assume or add symptoms not reported.
2. CONSIDER the specific vehicle: make, model, year, mileage. Known issues for that platform inform your differential.
3. RANK diagnoses by probability, with confidence levels and supporting evidence.
4. RECOMMEND specific tests to confirm or eliminate each diagnosis.
5. PROVIDE repair procedures with estimated labor hours, parts needed, and costs.
6. FLAG any safety-critical conditions (brake failure, fuel leaks, fire risk, structural failure).

Rules:
- Always acknowledge which symptoms you're working from.
- Never diagnose without vehicle context (make/model/year at minimum).
- Rank diagnoses most-likely first with confidence percentages.
- Include "test to confirm" steps so the mechanic can verify before replacing parts.
- Use real part numbers, labor times, and costs when possible.
- If the symptoms could indicate a safety issue, flag it prominently as CRITICAL.
- Be honest about uncertainty — "I'm 40% confident" is more useful than a wrong 90%.
- Knowledge-base entries carry a `source:` label. A figure from a `service-manual` entry may be
  stated as the manufacturer's; a figure from a `forum` or `model-generated` entry is unverified —
  if you use it, say so ("an owner-community figure", "an unverified figure") and
  never present it as a specification.

Response format: structured JSON matching the DiagnosticResponse schema."""


def build_vehicle_context(
    make: str,
    model: str,
    year: int,
    mileage: Optional[int] = None,
    engine_type: Optional[str] = None,
    modifications: Optional[list[str]] = None,
) -> str:
    """Format vehicle identification into structured context for the AI."""
    lines = [
        f"Vehicle: {year} {make} {model}",
    ]
    if mileage is not None:
        lines.append(f"Mileage: {mileage:,} miles")
    if engine_type:
        lines.append(f"Engine: {engine_type}")
    if modifications:
        lines.append(f"Modifications: {', '.join(modifications)}")
    return "\n".join(lines)


def build_symptom_context(symptoms: list[str], description: Optional[str] = None) -> str:
    """Format symptom list into structured context."""
    lines = ["Reported symptoms:"]
    for i, symptom in enumerate(symptoms, 1):
        lines.append(f"  {i}. {symptom}")
    if description:
        lines.append(f"\nAdditional context from mechanic: {description}")
    return "\n".join(lines)


#: How a row's `match_tier` reads in the prompt. Phase 244S: the resolver
#: tiers rather than filters (244E — knowing more must never return less), so
#: an entry about another model of the same make arrives in the context. It
#: used to arrive indistinguishable from one written about this machine. For a
#: 2022 KTM 1290 Super Adventure the corpus even holds an entry whose model
#: column says "as distinct from 1290 Super Adventure"; it belongs in the
#: prompt, labelled as what it is, not presented as machine-specific.
_TIER_LABEL = {
    "model": "this model",
    "make_wide": "this make, model not specified",
    "make_other_model": "same make, DIFFERENT model",
}


def build_knowledge_context(known_issues: list[dict]) -> str:
    """Format known issues from the knowledge base into context for the AI.

    Injects relevant known issues so the AI can reference them in its diagnosis.
    This is the RAG-style knowledge injection that connects Track B data to Track C reasoning.
    """
    if not known_issues:
        return ""

    lines = [
        f"\nRelevant known issues from the MotoDiag knowledge base ({len(known_issues)} matches):\n"
    ]
    for i, issue in enumerate(known_issues, 1):
        title = issue.get("title", "Unknown issue")
        severity = issue.get("severity", "unknown")
        symptoms = issue.get("symptoms", [])
        causes = issue.get("causes", [])
        # `.get(k, "")` returns None when the key exists and is NULL, and
        # `fix_procedure` is nullable — one corpus entry without a procedure
        # used to crash the whole prompt build on len(None). Found by 244S's
        # fixture; the shipped corpus has no such row, yet.
        fix = issue.get("fix_procedure") or ""
        # Truncate fix procedure to first 300 chars to stay within context budget
        fix_preview = fix[:300] + "..." if len(fix) > 300 else fix

        tier = _TIER_LABEL.get(str(issue.get("match_tier") or ""))
        scope = f", scope: {tier}" if tier else ""
        # Phase 246: the label travels with the number. A forum-sourced
        # threshold used to reach the model looking exactly like manufacturer
        # data; `diagnose` renders no KB entries itself, so the model's answer
        # is where a technician reads it, and the model has to be able to say
        # where it came from. Appended only when the row carries a source, so
        # a bare legacy dict renders as it always did.
        source = issue.get("source")
        provenance = f", source: {source}" if source else ""
        lines.append(f"--- Issue {i}: {title} (severity: {severity}{scope}{provenance}) ---")
        if symptoms:
            lines.append(f"  Symptoms: {', '.join(symptoms)}")
        if causes:
            lines.append(f"  Common causes: {'; '.join(causes[:3])}")
        lines.append(f"  Fix: {fix_preview}")
        lines.append("")

    return "\n".join(lines)


def build_full_prompt(
    vehicle_context: str,
    symptom_context: str,
    knowledge_context: str = "",
) -> str:
    """Assemble the full user prompt from vehicle, symptom, and knowledge contexts."""
    parts = [vehicle_context, "", symptom_context]
    if knowledge_context:
        parts.append(knowledge_context)
    parts.append(
        "\nPlease provide your diagnostic assessment as structured JSON "
        "matching the DiagnosticResponse schema."
    )
    return "\n".join(parts)
