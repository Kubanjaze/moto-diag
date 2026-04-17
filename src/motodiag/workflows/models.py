"""Workflow template Pydantic models.

Phase 114: WorkflowCategory enum covering all workflow types (diagnostic +
Track N's 12 non-diagnostic workflows), WorkflowTemplate, ChecklistItem.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowCategory(str, Enum):
    """Types of workflows in the system.

    Phase 114: enumerates all workflow types that the template substrate
    supports. Phase 82's diagnostic workflows are now just one of 13
    categories. Track N phases (259-272) will populate templates for each
    non-diagnostic category.
    """
    DIAGNOSTIC = "diagnostic"            # Phase 82 diagnostic workflows
    PPI = "ppi"                          # Pre-purchase inspection (phase 259-260)
    TIRE_SERVICE = "tire_service"        # Tire wear/DOT/TPMS (phase 261)
    CRASH_SUPPORT = "crash_support"      # Insurance claim / salvage (phase 262)
    TRACK_PREP = "track_prep"            # Track-day/race prep (phase 263)
    WINTERIZATION = "winterization"      # Winterization protocol (phase 264)
    DE_WINTERIZATION = "de_winterization"  # Spring startup (phase 265)
    BREAK_IN = "break_in"                # Engine rebuild break-in (phase 266)
    EMISSIONS = "emissions"              # Emissions / smog compliance (phase 267)
    VALVE_SERVICE = "valve_service"      # Valve adjustment workflow (phase 268)
    BRAKE_SERVICE = "brake_service"      # Brake service workflow (phase 269)
    SUSPENSION_SERVICE = "suspension_service"  # Fork/shock service (phase 270)
    DRIVETRAIN_SERVICE = "drivetrain_service"  # Chain/belt/shaft (phase 271)


class WorkflowTemplate(BaseModel):
    """A persistent workflow template.

    Templates are either built-in (seeded via migration, tier='individual',
    created_by_user_id=1) or shop-custom (created via create_template,
    tier='shop' or higher, created_by_user_id = shop owner's user id).
    """
    id: Optional[int] = Field(None, description="Primary key")
    slug: str = Field(..., description="Unique stable identifier (e.g., 'generic_ppi_v1')")
    name: str = Field(..., description="Human-readable template name")
    description: Optional[str] = Field(None, description="What this workflow does")
    category: WorkflowCategory = Field(..., description="Workflow type")
    applicable_powertrains: list[str] = Field(
        default_factory=lambda: ["ice", "electric", "hybrid"],
        description="Which powertrains this template applies to",
    )
    estimated_duration_minutes: Optional[int] = Field(
        None,
        description="Estimated time to complete the full workflow",
    )
    required_tier: str = Field(
        default="individual",
        description="Minimum subscription tier to access this template",
    )
    created_by_user_id: int = Field(
        default=1,
        description="User who created the template (1 = system/built-in)",
    )
    is_active: bool = Field(default=True, description="Whether template is available")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChecklistItem(BaseModel):
    """A single step/item in a workflow template."""
    id: Optional[int] = Field(None, description="Primary key")
    template_id: int = Field(..., description="Parent workflow template ID")
    sequence_number: int = Field(..., description="Display/execution order (1-based)")
    title: str = Field(..., description="Short title for this step")
    description: Optional[str] = Field(None, description="Expanded description")
    instruction_text: str = Field(
        ...,
        description="Detailed mechanic-friendly instructions for performing the step",
    )
    expected_pass: Optional[str] = Field(
        None,
        description="What a normal/passing result looks like",
    )
    expected_fail: Optional[str] = Field(
        None,
        description="What an abnormal/failing result looks like",
    )
    diagnosis_if_fail: Optional[str] = Field(
        None,
        description="What a failure indicates (narrows the diagnosis)",
    )
    required: bool = Field(
        default=True,
        description="Whether this step is required or optional",
    )
    tools_needed: list[str] = Field(
        default_factory=list,
        description="Tools needed for this step",
    )
    estimated_minutes: Optional[int] = Field(
        None,
        description="Estimated time for this step",
    )
