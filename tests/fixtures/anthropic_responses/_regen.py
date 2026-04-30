"""Regenerate Anthropic Vision response fixtures from real API calls.

Usage (architect, one-shot — NOT run during tests):

    cd C:\\Users\\Kerwyn\\PycharmProjects\\moto-diag
    .venv\\Scripts\\python.exe tests\\fixtures\\anthropic_responses\\_regen.py

Requires:
    - ANTHROPIC_API_KEY env var
    - 1-3 sample motorcycle frame JPEGs at tests/fixtures/sample_frames/*.jpg
      (regen instructions for sample frames live in
      tests/fixtures/sample_frames/README.md once that directory exists; for
      now, use any motorcycle exhaust + chassis photos under 1 MB each)

Persists:
    tests/fixtures/anthropic_responses/video_analysis_happy.json
        — typical finding-rich response (2-3 findings)
    tests/fixtures/anthropic_responses/video_analysis_clean.json
        — no findings (well-maintained bike)

Why this exists:
    Per Phase 190 Bug 2 lesson, mocked SDK responses pulled from real API
    calls catch shape drift that hand-authored fixtures miss. The
    synthetic fixtures committed alongside this script are good enough for
    Phase 191B Commit 2 (they exercise the pipeline's extraction logic),
    but before any production deploy or major SDK upgrade, run this script
    to regenerate from live API output.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

# Repo-root resolution
REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = Path(__file__).resolve().parent
SAMPLE_FRAMES_DIR = REPO_ROOT / "tests" / "fixtures" / "sample_frames"


def _build_image_blocks(frame_paths: list[Path]) -> list[dict]:
    """Build base64 image content blocks from frame file paths."""
    blocks = []
    for p in frame_paths:
        data = base64.b64encode(p.read_bytes()).decode()
        blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": data,
            },
        })
    return blocks


def _call_real_api(prompt_kind: str, frame_paths: list[Path]) -> dict:
    """Call the real Anthropic API and return the Message dict.

    prompt_kind: 'happy' or 'clean' — selects the user-side prompt to
    elicit a finding-rich vs no-findings response.
    """
    import anthropic  # noqa: F401  (deferred — only run at architect-side)

    from motodiag.media.vision_analysis import (
        VISION_ANALYSIS_PROMPT,
        VehicleContext,
        VisualAnalysisResult,
    )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    image_blocks = _build_image_blocks(frame_paths)

    if prompt_kind == "happy":
        user_text = (
            "VEHICLE CONTEXT:\nVehicle: 2005 Honda CBR600RR\nReported "
            "symptoms: blue smoke at startup\n\n"
            f"Analyzing {len(frame_paths)} frames extracted from a video "
            "diagnostic capture of this motorcycle. Examine each frame for "
            "the diagnostic symptoms in the system prompt and report "
            "findings via the report_video_findings tool."
        )
    else:
        user_text = (
            f"Analyzing {len(frame_paths)} frames extracted from a video "
            "diagnostic capture of a well-maintained motorcycle. Report "
            "any visible diagnostic findings via the report_video_findings "
            "tool — likely none."
        )

    tools = [{
        "name": "report_video_findings",
        "description": (
            "Report structured visual findings extracted from the video "
            "frames of a motorcycle diagnostic capture."
        ),
        "input_schema": VisualAnalysisResult.model_json_schema(),
    }]

    response = client.messages.create(
        model="claude-sonnet-4-5-20241022",
        max_tokens=4096,
        tools=tools,
        tool_choice={"type": "tool", "name": "report_video_findings"},
        system=VISION_ANALYSIS_PROMPT,
        messages=[{
            "role": "user",
            "content": image_blocks + [{"type": "text", "text": user_text}],
        }],
    )

    return response.model_dump()


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY env var not set.", file=sys.stderr)
        return 1

    if not SAMPLE_FRAMES_DIR.exists():
        print(
            f"ERROR: {SAMPLE_FRAMES_DIR} does not exist. "
            "Add 1-3 motorcycle JPEGs there before running.",
            file=sys.stderr,
        )
        return 1

    frame_paths = sorted(SAMPLE_FRAMES_DIR.glob("*.jpg"))
    if not frame_paths:
        print(f"ERROR: No .jpg files found in {SAMPLE_FRAMES_DIR}", file=sys.stderr)
        return 1

    print(f"Found {len(frame_paths)} frames; calling real API for 'happy' fixture...")
    happy = _call_real_api("happy", frame_paths)
    (FIXTURES_DIR / "video_analysis_happy.json").write_text(
        json.dumps(happy, indent=2), encoding="utf-8"
    )
    print(f"  -> {FIXTURES_DIR / 'video_analysis_happy.json'}")

    print("Calling real API for 'clean' fixture...")
    clean = _call_real_api("clean", frame_paths)
    (FIXTURES_DIR / "video_analysis_clean.json").write_text(
        json.dumps(clean, indent=2), encoding="utf-8"
    )
    print(f"  -> {FIXTURES_DIR / 'video_analysis_clean.json'}")

    print("Done. Commit the regenerated JSON fixtures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
