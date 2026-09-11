"""Phase 244N — passive capture of what the product already produces.

Three streams of exactly the data this product needs pass through it every day
and are discarded at the end of the request. This package stops discarding
them. It adds no work for a technician, asks no question, and changes nothing a
user sees.

**Passive means byproduct.** The capture that works is the one attached to work
someone already had a reason to do. The `feedback/` subsystem is the proof of
the converse: a correct schema, a complete repo, two tables and tests, built at
Phase 116 -- and zero rows, for nine phases, because every path into it required
someone to go out of their way and nobody ever does.

**Record, never label.** Nothing here writes an outcome, a verdict, or a
correctness score, and no such column exists in the schema. A finding nobody
acted on is *unresolved*, not *wrong* -- it may have been right and
deprioritised, or right and fixed without paperwork. A nullable outcome column
invites a default, and a default fabricates negatives that nothing downstream
could later detect. Interpretation belongs to a phase that can be judged on it.

**Capture never costs the thing being captured.** Every write here is wrapped
and swallowed. A logging failure that 500s a technician's edit has traded the
thing that matters for the thing that might matter later. Same contract Phase
244L set for cost recording, for the same reason.
"""

from motodiag.capture.guidance_log import (
    record_guidance_interaction,
    list_interactions,
)
from motodiag.capture.overrides import capture_session_overrides
from motodiag.capture.analyses import (
    record_analysis,
    list_analyses,
    current_analysis,
)
from motodiag.capture.stats import capture_stats

__all__ = [
    "record_guidance_interaction",
    "list_interactions",
    "capture_session_overrides",
    "record_analysis",
    "list_analyses",
    "current_analysis",
    "capture_stats",
]
