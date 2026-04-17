"""Workflows package — persistent workflow templates for non-diagnostic procedures.

Phase 114 (Retrofit): introduces workflow template substrate that Track N
phases 259-272 (PPI, tire service, winterization, break-in, emissions, etc.)
will populate with real content. Bridges Phase 82's in-memory
DiagnosticWorkflow engine to persistent, shop-definable templates.

Custom templates require shop tier or higher. Built-in templates (seeded
via migration 007) are available to all tiers.
"""

from motodiag.workflows.models import (
    WorkflowCategory, WorkflowTemplate, ChecklistItem,
)
from motodiag.workflows.template_repo import (
    create_template, get_template, get_template_by_slug,
    list_templates, update_template, deactivate_template,
    add_checklist_item, get_checklist_items, update_checklist_item,
    delete_checklist_item,
    count_templates,
)

__all__ = [
    # Models
    "WorkflowCategory", "WorkflowTemplate", "ChecklistItem",
    # Template repo
    "create_template", "get_template", "get_template_by_slug",
    "list_templates", "update_template", "deactivate_template",
    "add_checklist_item", "get_checklist_items", "update_checklist_item",
    "delete_checklist_item",
    "count_templates",
]
