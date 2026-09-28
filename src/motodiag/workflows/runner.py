"""A workflow template's checklist as Phase 82's step engine.

Phase 356. `motodiag workflow run` walks a template through
`DiagnosticWorkflow`; Phase 357's saved runs build the same workflow.

A checklist is not a decision tree: every item is answered, whatever an
earlier one found, so the workflow is built with `stop_on_fail=False`.
The engine's steps have no field for an item's title, description,
required flag or tools; the caller keeps the items beside the steps, by
index.
"""

from motodiag.engine.workflows import DiagnosticWorkflow, WorkflowStep


def checklist_workflow(template: dict, items: list[dict]) -> DiagnosticWorkflow:
    """One step per checklist item, in the order given."""
    return DiagnosticWorkflow(
        workflow_id=template["slug"],
        workflow_type=template["category"],
        max_steps=len(items),
        stop_on_fail=False,
        steps=[
            WorkflowStep(
                step_number=item["sequence_number"],
                test_instruction=item["instruction_text"],
                # A ChecklistItem may leave these None; the step's are str.
                expected_pass=item["expected_pass"] or "",
                expected_fail=item["expected_fail"] or "",
                diagnosis_if_fail=item["diagnosis_if_fail"],
            )
            for item in items
        ],
    )
