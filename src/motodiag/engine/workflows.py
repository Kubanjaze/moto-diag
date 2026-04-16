"""Multi-step diagnostic workflows — guided troubleshooting with decision-tree branching.

Each workflow is a sequence of test steps. The mechanic performs a test, reports the result,
and the system branches to the next appropriate test based on the finding. This narrows the
diagnosis step by step until a confident conclusion is reached.
"""

from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import TokenUsage


class StepResult(str, Enum):
    """Result of a diagnostic test step."""
    PASS = "pass"       # Test result was normal/expected
    FAIL = "fail"       # Test result was abnormal/unexpected
    UNCLEAR = "unclear" # Mechanic couldn't determine or result was ambiguous
    SKIPPED = "skipped" # Mechanic skipped this test


class WorkflowStep(BaseModel):
    """A single diagnostic test step in a workflow."""
    step_number: int = Field(..., description="Step sequence number")
    test_instruction: str = Field(..., description="What the mechanic should do — clear, specific, no jargon without explanation")
    expected_pass: str = Field(default="", description="What a normal/good result looks like")
    expected_fail: str = Field(default="", description="What an abnormal/bad result looks like")
    result: Optional[StepResult] = Field(None, description="Mechanic's reported result")
    mechanic_notes: Optional[str] = Field(None, description="Optional notes from the mechanic about the result")
    diagnosis_if_fail: Optional[str] = Field(None, description="What this failure points to")
    next_step_if_pass: Optional[str] = Field(None, description="What to test next if this step passes")
    next_step_if_fail: Optional[str] = Field(None, description="What to test next if this step fails")


class WorkflowStatus(str, Enum):
    """Status of a diagnostic workflow."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ABANDONED = "abandoned"


class DiagnosticWorkflow(BaseModel):
    """Manages a multi-step diagnostic session with branching logic.

    Tracks the sequence of tests performed, results at each step,
    and progressively narrows the diagnosis based on findings.
    """
    workflow_id: str = Field(default="", description="Unique workflow identifier")
    vehicle_context: str = Field(default="", description="Vehicle make/model/year string")
    initial_complaint: str = Field(default="", description="The presenting symptom or complaint")
    workflow_type: str = Field(default="custom", description="Workflow template type (no_start, charging, overheating, noise, custom)")
    status: WorkflowStatus = Field(default=WorkflowStatus.NOT_STARTED)
    steps: list[WorkflowStep] = Field(default_factory=list)
    current_step_index: int = Field(default=0)
    working_diagnosis: str = Field(default="", description="Current best-guess diagnosis based on results so far")
    eliminated_causes: list[str] = Field(default_factory=list, description="Causes ruled out by test results")
    remaining_causes: list[str] = Field(default_factory=list, description="Causes still under consideration")
    max_steps: int = Field(default=10, description="Maximum steps before forcing a conclusion")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Return the current step the mechanic should perform."""
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def report_result(self, result: StepResult, notes: Optional[str] = None) -> Optional[WorkflowStep]:
        """Record the result of the current step and advance the workflow.

        Args:
            result: The mechanic's test result (pass/fail/unclear/skipped).
            notes: Optional notes about the finding.

        Returns:
            The next WorkflowStep if the workflow continues, None if complete.
        """
        current = self.get_current_step()
        if current is None:
            return None

        # Record result
        current.result = result
        current.mechanic_notes = notes
        self.status = WorkflowStatus.IN_PROGRESS

        # Update diagnosis state based on result
        if result == StepResult.FAIL and current.diagnosis_if_fail:
            self.working_diagnosis = current.diagnosis_if_fail
        if result == StepResult.PASS and current.diagnosis_if_fail:
            self.eliminated_causes.append(current.diagnosis_if_fail)
            if current.diagnosis_if_fail in self.remaining_causes:
                self.remaining_causes.remove(current.diagnosis_if_fail)

        # Advance to next step
        self.current_step_index += 1

        # Check completion
        if self.is_complete():
            self.status = WorkflowStatus.COMPLETE
            self.completed_at = datetime.now(timezone.utc)
            return None

        return self.get_current_step()

    def is_complete(self) -> bool:
        """Check if the workflow has reached a conclusion."""
        # Complete if we've exceeded max steps
        if self.current_step_index >= self.max_steps:
            return True
        # Complete if we've gone through all predefined steps
        if self.current_step_index >= len(self.steps):
            return True
        # Complete if we have a confident working diagnosis from a failed test
        if self.working_diagnosis and any(
            s.result == StepResult.FAIL for s in self.steps if s.result is not None
        ):
            return True
        return False

    def get_results_summary(self) -> dict:
        """Summarize all test results so far."""
        completed_steps = [s for s in self.steps if s.result is not None]
        return {
            "workflow_id": self.workflow_id,
            "vehicle": self.vehicle_context,
            "complaint": self.initial_complaint,
            "workflow_type": self.workflow_type,
            "status": self.status.value,
            "steps_completed": len(completed_steps),
            "steps_total": len(self.steps),
            "working_diagnosis": self.working_diagnosis,
            "eliminated_causes": self.eliminated_causes,
            "remaining_causes": self.remaining_causes,
            "test_results": [
                {
                    "step": s.step_number,
                    "test": s.test_instruction[:80],
                    "result": s.result.value if s.result else "pending",
                    "notes": s.mechanic_notes,
                }
                for s in self.steps
            ],
        }


# --- Predefined workflow templates ---

def create_no_start_workflow(vehicle_context: str) -> DiagnosticWorkflow:
    """Create a predefined no-start diagnostic workflow.

    Follows the systematic approach: battery → starter circuit → fuel → spark → compression.
    """
    import time
    return DiagnosticWorkflow(
        workflow_id=f"nostart-{int(time.time())}",
        vehicle_context=vehicle_context,
        initial_complaint="Engine won't start / cranks but won't fire",
        workflow_type="no_start",
        status=WorkflowStatus.NOT_STARTED,
        remaining_causes=[
            "Dead or weak battery",
            "Starter relay failure",
            "Safety switch preventing start (clutch/kickstand/kill)",
            "No fuel delivery (pump, relay, filter)",
            "No spark (coil, plug, pickup, CDI)",
            "Low compression (valves, rings, head gasket)",
        ],
        steps=[
            WorkflowStep(
                step_number=1,
                test_instruction="Check battery voltage with a multimeter — connect red lead to positive terminal, black to negative. Read the voltage with ignition OFF.",
                expected_pass="12.4V or higher — battery is charged and healthy.",
                expected_fail="Below 12.0V — battery is dead or weak. Below 10.5V — battery is sulfated and needs replacement.",
                diagnosis_if_fail="Dead or weak battery",
                next_step_if_pass="Battery is good — proceed to starter circuit test.",
                next_step_if_fail="Charge battery to 12.8V+ and retest. If it won't hold charge, replace battery.",
            ),
            WorkflowStep(
                step_number=2,
                test_instruction="Turn ignition ON (don't crank). Listen for the fuel pump prime — a 2-3 second buzzing/whirring sound from under the seat or tank. On carbureted bikes, turn petcock to PRI and check for fuel flow.",
                expected_pass="Fuel pump primes (EFI) or fuel flows from petcock (carb).",
                expected_fail="No fuel pump prime sound (EFI) or no fuel flow (carb).",
                diagnosis_if_fail="No fuel delivery (pump, relay, filter)",
                next_step_if_pass="Fuel delivery is present — proceed to spark test.",
                next_step_if_fail="Check fuel pump relay (swap with adjacent relay). Check fuel pump fuse. Check petcock vacuum line (carb).",
            ),
            WorkflowStep(
                step_number=3,
                test_instruction="Remove a spark plug. Reconnect the plug wire/coil to the plug. Ground the plug threads against the engine (hold plug against a bare metal surface on the cylinder head). Crank the engine and watch for a spark jumping across the plug gap.",
                expected_pass="Strong blue/white spark visible at the plug gap.",
                expected_fail="No spark, weak orange spark, or intermittent spark.",
                diagnosis_if_fail="No spark (coil, plug, pickup, CDI)",
                next_step_if_pass="Spark is present — proceed to compression test.",
                next_step_if_fail="Check kill switch is in RUN. Check safety switches (clutch pulled, kickstand up). Check plug wire/cap resistance. Check ignition coil primary and secondary resistance.",
            ),
            WorkflowStep(
                step_number=4,
                test_instruction="With the spark plug still removed, hold your thumb firmly over the spark plug hole. Crank the engine briefly (2-3 kicks or 2-3 seconds of electric start). You should feel strong air pressure pushing against your thumb.",
                expected_pass="Strong, consistent air pressure pulses against your thumb — compression is adequate.",
                expected_fail="Weak or no air pressure — low compression.",
                diagnosis_if_fail="Low compression (valves, rings, head gasket)",
                next_step_if_pass="Compression is adequate. All three systems (fuel, spark, compression) are present — recheck timing, fuel quality, and intake for air leaks.",
                next_step_if_fail="Perform a proper compression test with a gauge. Spec is typically 150-185 PSI for most motorcycle engines. Low = valve clearance tight, rings worn, or head gasket failed.",
            ),
            WorkflowStep(
                step_number=5,
                test_instruction="Check all safety switches: (1) Pull clutch lever fully — does the starter engage? (2) Ensure kickstand is fully up. (3) Check kill switch is in RUN position. (4) Try starting in neutral with kickstand down.",
                expected_pass="Starter engages in all valid configurations.",
                expected_fail="Starter only works in certain switch positions — a safety switch is faulty.",
                diagnosis_if_fail="Safety switch preventing start (clutch/kickstand/kill)",
                next_step_if_pass="All safety switches functional. Revisit fuel delivery and spark quality.",
                next_step_if_fail="Identify which switch is faulty. Jumper the suspect switch connector to confirm. Replace the faulty switch ($15-30).",
            ),
        ],
        started_at=datetime.now(timezone.utc),
    )


def create_charging_workflow(vehicle_context: str) -> DiagnosticWorkflow:
    """Create a predefined charging system diagnostic workflow.

    Follows the universal 3-step diagnostic: voltage at RPM → stator AC → reg/rec test.
    """
    import time
    return DiagnosticWorkflow(
        workflow_id=f"charging-{int(time.time())}",
        vehicle_context=vehicle_context,
        initial_complaint="Battery dying / not charging / voltage low",
        workflow_type="charging",
        status=WorkflowStatus.NOT_STARTED,
        remaining_causes=[
            "Regulator/rectifier failure",
            "Stator winding failure",
            "Stator connector melting/corrosion",
            "Battery internal failure",
            "Parasitic draw from accessories",
            "Ground circuit resistance",
        ],
        steps=[
            WorkflowStep(
                step_number=1,
                test_instruction="Start the engine and warm it up. With a multimeter on DC voltage across the battery terminals, rev to 5000 RPM and read the voltage.",
                expected_pass="13.8-14.5V at 5000 RPM — charging system is producing adequate output.",
                expected_fail="Below 13.5V = undercharging (stator or reg/rec). Above 15.0V = overcharging (reg/rec failure).",
                diagnosis_if_fail="Charging system fault — proceed to isolate stator vs reg/rec.",
                next_step_if_pass="Charging output is adequate. Check for parasitic draw or battery internal failure.",
                next_step_if_fail="Proceed to stator AC output test to isolate the fault.",
            ),
            WorkflowStep(
                step_number=2,
                test_instruction="Turn engine OFF. Unplug the stator connector from the regulator/rectifier (3-pin white connector, usually behind left engine cover or under seat). Set multimeter to AC voltage. Start engine. Measure AC voltage across all 3 stator wire pairs at 5000 RPM: wire 1-2, wire 1-3, wire 2-3.",
                expected_pass="All 3 pairs read equal AC voltage within 0.5V of each other (typically 50-80V AC at 5000 RPM depending on model).",
                expected_fail="One pair significantly lower or zero = that stator winding is shorted/open. All three low = stator is dying.",
                diagnosis_if_fail="Stator winding failure",
                next_step_if_pass="Stator output is healthy — the reg/rec is the problem.",
                next_step_if_fail="Also test each stator wire to ground (engine case). Any reading to ground = stator is shorted to ground. Replace stator.",
            ),
            WorkflowStep(
                step_number=3,
                test_instruction="With stator still unplugged: set multimeter to resistance (ohms). Measure resistance of each stator wire to engine ground (case). Should be infinite (OL) on all three wires.",
                expected_pass="All three wires show infinite resistance (OL) to ground — no short to ground.",
                expected_fail="Any wire shows continuity to ground (low resistance reading) — stator is shorted to ground.",
                diagnosis_if_fail="Stator shorted to ground — replace stator",
                next_step_if_pass="Stator is not grounded. If AC output was good, the reg/rec is the fault. Replace with MOSFET upgrade.",
                next_step_if_fail="Replace stator AND reg/rec together. A shorted stator may have damaged the reg/rec. Always replace both.",
            ),
            WorkflowStep(
                step_number=4,
                test_instruction="Inspect the stator connector (the 3-pin white connector you unplugged). Look for discoloration, melting, brown/black burned pins, or a burned plastic smell.",
                expected_pass="Connector is clean, white, no discoloration — connector is healthy.",
                expected_fail="Connector shows browning, melting, or deformed pins — resistance heating has damaged it.",
                diagnosis_if_fail="Stator connector melting/corrosion",
                next_step_if_pass="Connector is good. Reconnect and retest system voltage.",
                next_step_if_fail="Cut the connector off both sides. Solder the 3 stator wires directly to the reg/rec wires. Use marine-grade heat shrink. This permanently eliminates the connector as a failure point.",
            ),
        ],
        started_at=datetime.now(timezone.utc),
    )


def create_overheating_workflow(vehicle_context: str) -> DiagnosticWorkflow:
    """Create a predefined overheating diagnostic workflow."""
    import time
    return DiagnosticWorkflow(
        workflow_id=f"overheat-{int(time.time())}",
        vehicle_context=vehicle_context,
        initial_complaint="Engine overheating / temperature gauge high / coolant boiling",
        workflow_type="overheating",
        status=WorkflowStatus.NOT_STARTED,
        remaining_causes=[
            "Thermostat stuck closed",
            "Radiator fan not activating",
            "Low coolant level / leak",
            "Coolant degraded / acidic",
            "Water pump failure",
            "Radiator core blocked",
            "Head gasket failure",
        ],
        steps=[
            WorkflowStep(
                step_number=1,
                test_instruction="With engine COLD, check coolant level in the radiator (remove cap carefully) and overflow reservoir. Top up if low. Also check for visible coolant leaks under the bike and around hose connections.",
                expected_pass="Coolant level is at the correct mark in both radiator and reservoir. No visible leaks.",
                expected_fail="Coolant is low or empty. Visible leak at a hose, gasket, or water pump weep hole.",
                diagnosis_if_fail="Low coolant level / leak",
                next_step_if_pass="Coolant level is okay — proceed to thermostat test.",
                next_step_if_fail="Top up coolant. Pressure test the system to find leaks. Check water pump weep hole (small hole on pump housing — dripping = seal failure).",
            ),
            WorkflowStep(
                step_number=2,
                test_instruction="Start the engine and let it warm up. Feel the upper radiator hose — it should start cold and gradually become hot as the thermostat opens (typically around 175-185°F / 80-85°C). If the hose stays cold while the engine is hot, the thermostat is stuck closed.",
                expected_pass="Upper radiator hose gets hot within 5-10 minutes of running — thermostat is opening normally.",
                expected_fail="Upper hose stays cold while engine temperature climbs — thermostat stuck closed.",
                diagnosis_if_fail="Thermostat stuck closed",
                next_step_if_pass="Thermostat is opening. Check radiator fan next.",
                next_step_if_fail="Replace thermostat ($15-25, 30-minute job). Remove and test in hot water to confirm before installing new one.",
            ),
            WorkflowStep(
                step_number=3,
                test_instruction="With engine at operating temperature, check if the radiator fan activates. Most fans turn on around 210-220°F (100-105°C). If the fan doesn't come on when the engine is hot, disconnect the fan switch connector and jumper the two wires — this should make the fan run.",
                expected_pass="Fan activates at the correct temperature, or runs when jumpering the switch connector.",
                expected_fail="Fan does not run even when jumpering the switch — fan motor or wiring is the problem.",
                diagnosis_if_fail="Radiator fan not activating",
                next_step_if_pass="Fan works. If the bike still overheats with fan running, the radiator core may be blocked or the coolant is degraded.",
                next_step_if_fail="If fan runs with jumper but not via switch: replace fan switch ($15-30). If fan doesn't run at all: check fan fuse, then check fan motor by applying 12V directly.",
            ),
        ],
        started_at=datetime.now(timezone.utc),
    )


# --- AI-generated workflow step ---

WORKFLOW_STEP_PROMPT = """You are guiding a motorcycle mechanic through a diagnostic workflow. Based on the vehicle, complaint, and previous test results, suggest the NEXT diagnostic test step.

Previous test results:
{previous_results}

Current working diagnosis: {working_diagnosis}
Eliminated causes: {eliminated_causes}
Remaining possible causes: {remaining_causes}

Provide the next test step as JSON with these fields:
- test_instruction: Clear, specific instructions for the mechanic (no jargon without explanation)
- expected_pass: What a normal result looks like
- expected_fail: What an abnormal result looks like
- diagnosis_if_fail: What this failure would indicate
- next_step_if_pass: Brief description of what to test next if this passes
- next_step_if_fail: Brief description of what to do if this fails"""


def generate_next_step(
    client: DiagnosticClient,
    workflow: DiagnosticWorkflow,
    ai_model: Optional[str] = None,
) -> tuple[Optional[WorkflowStep], Optional[TokenUsage]]:
    """Use Claude to generate the next diagnostic step based on workflow state.

    This is used when the predefined template steps are exhausted and the
    diagnosis is not yet conclusive.

    Returns:
        Tuple of (WorkflowStep or None, TokenUsage or None).
    """
    import json

    summary = workflow.get_results_summary()
    previous_results = "\n".join(
        f"Step {r['step']}: {r['test']} → Result: {r['result']}" + (f" Notes: {r['notes']}" if r['notes'] else "")
        for r in summary["test_results"]
        if r["result"] != "pending"
    )

    prompt = WORKFLOW_STEP_PROMPT.format(
        previous_results=previous_results or "No tests performed yet.",
        working_diagnosis=workflow.working_diagnosis or "Not yet determined",
        eliminated_causes=", ".join(workflow.eliminated_causes) or "None yet",
        remaining_causes=", ".join(workflow.remaining_causes) or "Unknown — needs initial assessment",
    )

    full_prompt = f"{workflow.vehicle_context}\nComplaint: {workflow.initial_complaint}\n\n{prompt}"

    response_text, usage = client.ask(prompt=full_prompt, model=ai_model)

    try:
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)
        step = WorkflowStep(
            step_number=len(workflow.steps) + 1,
            test_instruction=data.get("test_instruction", "Perform the recommended test."),
            expected_pass=data.get("expected_pass", ""),
            expected_fail=data.get("expected_fail", ""),
            diagnosis_if_fail=data.get("diagnosis_if_fail"),
            next_step_if_pass=data.get("next_step_if_pass"),
            next_step_if_fail=data.get("next_step_if_fail"),
        )
        workflow.steps.append(step)
        return step, usage
    except (json.JSONDecodeError, KeyError, ValueError):
        return None, usage
