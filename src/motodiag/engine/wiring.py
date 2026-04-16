"""Wiring diagram reference — circuit descriptions, connector pinouts, wire colors.

Phase 92: Provides structured wiring reference data for common motorcycle circuits
across all makes. Not actual wiring diagrams (those are copyrighted) but the
diagnostic information a mechanic needs: what wire goes where, what color it is,
what connector to check, and what voltage/resistance to expect.
"""

from typing import Optional
from pydantic import BaseModel, Field


class WireReference(BaseModel):
    """A single wire in a circuit."""
    color: str = Field(..., description="Wire color (e.g., 'black/white stripe')")
    function: str = Field(..., description="What this wire does")
    connector_location: str = Field(default="", description="Where to find the connector")
    expected_voltage: Optional[str] = Field(None, description="Expected voltage reading")
    expected_resistance: Optional[str] = Field(None, description="Expected resistance reading")


class CircuitReference(BaseModel):
    """A complete circuit reference for diagnostic use."""
    circuit_name: str = Field(..., description="Name of the circuit (e.g., 'Charging circuit')")
    system: str = Field(default="", description="System category (electrical, fuel, ignition, etc.)")
    description: str = Field(default="", description="What this circuit does and how it works")
    makes_applicable: list[str] = Field(default_factory=list, description="Which makes this applies to")
    wires: list[WireReference] = Field(default_factory=list, description="Wires in this circuit")
    test_points: list[str] = Field(default_factory=list, description="Key test points for diagnosis")
    common_failures: list[str] = Field(default_factory=list, description="What commonly goes wrong")
    diagnostic_tips: list[str] = Field(default_factory=list, description="Practical diagnostic advice")


# --- Common motorcycle circuit references ---
# These are generic patterns that apply across makes with make-specific notes

CIRCUIT_REFERENCES: list[dict] = [
    {
        "circuit_name": "Charging circuit — stator to battery",
        "system": "electrical",
        "description": "Three-phase AC from the stator → regulator/rectifier (converts to DC and regulates to 14V) → battery. The stator connector is the junction between stator and reg/rec.",
        "makes_applicable": ["Honda", "Yamaha", "Kawasaki", "Suzuki", "Harley-Davidson"],
        "wires": [
            {"color": "Yellow (3 wires)", "function": "Stator AC output — three phase leads", "connector_location": "Behind left engine cover or under seat", "expected_voltage": "50-80V AC at 5000 RPM (per pair)"},
            {"color": "Red", "function": "B+ output from reg/rec to battery", "connector_location": "Reg/rec output connector", "expected_voltage": "13.8-14.5V DC at 5000 RPM"},
            {"color": "Green or Black", "function": "Ground — reg/rec to frame/engine", "connector_location": "Frame bolt or engine case bolt", "expected_resistance": "<0.5 ohm to battery negative"},
        ],
        "test_points": [
            "Battery terminals: DC voltage at idle and 5000 RPM",
            "Stator connector: AC voltage across all 3 pairs at 5000 RPM",
            "Stator to ground: resistance from each yellow wire to engine case (should be infinite/OL)",
            "Reg/rec ground: voltage drop from reg/rec ground wire to battery negative under load",
        ],
        "common_failures": [
            "Stator winding shorted to ground — AC voltage drops on affected phase",
            "Reg/rec internal failure — output voltage too low (<13.5V) or too high (>15V)",
            "Stator connector melting — resistance at connector heats up, melts housing",
            "Ground connection corroded — voltage drop >0.5V indicates bad ground",
        ],
        "diagnostic_tips": [
            "Always test at 5000 RPM — idle voltage is not diagnostic",
            "All 3 stator AC pairs must be equal within 0.5V — unequal means one winding is failing",
            "Any stator wire reading to ground = shorted stator, replace immediately",
            "If connector shows any browning/melting, solder wires directly as permanent fix",
        ],
    },
    {
        "circuit_name": "Starting circuit — battery to starter motor",
        "system": "electrical",
        "description": "Battery → main fuse → starter relay (controlled by start button through safety switches) → starter motor. Safety switches (clutch, kickstand, neutral, kill) form a series circuit that must be complete for the relay to energize.",
        "makes_applicable": ["Honda", "Yamaha", "Kawasaki", "Suzuki", "Harley-Davidson"],
        "wires": [
            {"color": "Red (heavy gauge)", "function": "Battery positive to starter relay input", "connector_location": "Main fuse block", "expected_voltage": "12.4V+ with ignition off"},
            {"color": "Red (heavy gauge)", "function": "Starter relay output to starter motor", "connector_location": "Starter relay to motor cable", "expected_voltage": "10V+ during cranking"},
            {"color": "Yellow/Red or Blue/White (varies)", "function": "Start button signal to relay coil", "connector_location": "Right handlebar switch connector", "expected_voltage": "12V when start button pressed"},
            {"color": "Green", "function": "Ground return through safety switch chain", "connector_location": "Multiple — clutch switch, kickstand switch, neutral switch", "expected_resistance": "<1 ohm through complete chain"},
        ],
        "test_points": [
            "Battery voltage during cranking — should stay above 10V",
            "Starter relay: 12V at coil terminal when start button pressed (with clutch pulled)",
            "Safety switch chain: continuity from start button ground through clutch→kickstand→neutral",
            "Starter motor cable: voltage drop from battery to starter terminal during cranking (<0.5V)",
        ],
        "common_failures": [
            "Starter relay contacts corroded — clicks but no crank",
            "Clutch safety switch open — no click at all",
            "Battery cable voltage drop — slow cranking from corroded terminals",
            "Kill switch corroded contacts — intermittent no-start",
        ],
        "diagnostic_tips": [
            "No click = switch/relay coil circuit. Click but no crank = relay contacts or motor",
            "Tap the starter relay while pressing start — if it cranks, relay contacts are bad",
            "Jumper the clutch switch connector (2 wires) to eliminate it as a suspect",
            "Check voltage AT the starter motor terminal during cranking, not just at the battery",
        ],
    },
    {
        "circuit_name": "Fuel injection — pump, relay, and injectors",
        "system": "fuel",
        "description": "Ignition ON → ECU powers FI relay → relay energizes fuel pump for 2-3 sec prime → pump maintains 43 PSI rail pressure → ECU pulses injectors based on sensor inputs (TPS, MAP, ECT, RPM).",
        "makes_applicable": ["Honda", "Yamaha", "Kawasaki", "Suzuki"],
        "wires": [
            {"color": "Black/White or Blue (varies)", "function": "FI relay coil — ECU control", "connector_location": "Relay block under seat", "expected_voltage": "12V for 2-3 sec at key ON"},
            {"color": "Orange or Red/Blue", "function": "Fuel pump power — through FI relay", "connector_location": "Fuel pump connector under tank/seat", "expected_voltage": "12V during prime and running"},
            {"color": "Various (2 wires per injector)", "function": "Injector pulse — ECU ground-switches injector", "connector_location": "At each injector connector on throttle body", "expected_voltage": "12V constant + ground pulse (varies with RPM)"},
        ],
        "test_points": [
            "Fuel pump relay: swap with adjacent same-type relay for quick test",
            "Fuel pump connector: 12V present during key-ON prime (2-3 seconds)",
            "Fuel rail pressure: 43 PSI (3.0 bar) typical for Japanese sport bikes",
            "Injector resistance: 10-14 ohms per injector (high impedance type)",
        ],
        "common_failures": [
            "FI relay contacts corroded — no fuel pump prime",
            "Fuel pump motor weakening — pressure drops under high-RPM load",
            "Injector clogged — lean condition on affected cylinder",
            "TPS/MAP sensor drifted — ECU computing wrong fuel pulse width",
        ],
        "diagnostic_tips": [
            "Key ON: listen for 2-3 sec pump prime buzz — no sound = relay or pump",
            "Swap the FI relay with headlight relay (same type) for instant roadside test",
            "Fuel pump relay is the #1 stranding part across all EFI Suzuki/Kawasaki models",
            "Injector balance test: measure resistance across all injectors — should be within 1 ohm of each other",
        ],
    },
    {
        "circuit_name": "Ignition — CDI/ECU to coils to plugs",
        "system": "ignition",
        "description": "Pickup coil (CKP sensor) sends RPM/position signal to CDI/ECU → CDI/ECU triggers ignition coil primary → coil secondary steps up to 20-40kV → spark plug fires. Modern bikes use coil-on-plug (COP) with ECU controlling individual coils.",
        "makes_applicable": ["Honda", "Yamaha", "Kawasaki", "Suzuki"],
        "wires": [
            {"color": "Blue/Yellow or White/Blue (varies)", "function": "Pickup coil signal to CDI/ECU", "connector_location": "Behind stator cover, connector near engine case", "expected_resistance": "100-500 ohm (model-specific)"},
            {"color": "Orange or Yellow (varies)", "function": "CDI/ECU trigger signal to coil primary", "connector_location": "Coil primary connector", "expected_voltage": "Pulsing 12V at cranking RPM"},
            {"color": "Black with colored stripe", "function": "Coil primary ground — ECU-controlled", "connector_location": "Coil connector", "expected_resistance": "Primary 2-4 ohms, secondary 10-15K ohms"},
        ],
        "test_points": [
            "Pickup coil resistance: should be within spec (100-500 ohm, model-specific)",
            "Pickup coil air gap: 0.5-1.5mm to rotor/reluctor",
            "Coil primary resistance: 2-4 ohms across primary terminals",
            "Coil secondary resistance: 10-15K ohms from primary to spark plug terminal",
        ],
        "common_failures": [
            "Pickup coil wiring insulation cracked from heat — intermittent signal loss",
            "Ignition coil secondary winding breakdown — weak spark under load",
            "Plug wire/cap resistance too high — NGK caps should be ~5K ohm",
            "Kill switch contacts corroded — intermittent ground interrupting ignition",
        ],
        "diagnostic_tips": [
            "Spark but no start: check timing — a slipped pickup or broken woodruff key shifts timing",
            "Intermittent misfire: wiggle test — move wiring harness while engine idles to find loose connection",
            "Weak spark: measure coil secondary resistance — out-of-spec = coil is breaking down internally",
            "COP systems: swap coils between cylinders — if the misfire moves, the coil is bad",
        ],
    },
    {
        "circuit_name": "ABS wheel speed sensor circuit",
        "system": "braking",
        "description": "Magnetic reluctance or Hall-effect sensor mounted near a toothed tone ring on wheel hub. Generates a signal as each tooth passes, telling ABS ECU the wheel rotational speed. ABS ECU compares front/rear speed for slip detection.",
        "makes_applicable": ["Honda", "Yamaha", "Kawasaki", "Suzuki", "Harley-Davidson"],
        "wires": [
            {"color": "White/Green and White/Blue (typical)", "function": "Wheel speed sensor signal pair", "connector_location": "Along fork leg (front) or swingarm (rear)", "expected_voltage": "AC signal — increases with wheel speed"},
            {"color": "Black", "function": "Sensor ground/shield", "connector_location": "ABS ECU connector block", "expected_resistance": "Sensor resistance typically 800-1400 ohms"},
        ],
        "test_points": [
            "Sensor resistance: 800-1400 ohms across sensor terminals (model-specific)",
            "Sensor air gap: 0.5-1.5mm from sensor tip to tone ring teeth",
            "Sensor to ground: should be infinite/OL (no short to frame)",
            "AC signal check: spin wheel by hand with multimeter on AC — should see 0.2-1.0V AC",
        ],
        "common_failures": [
            "Sensor tip contaminated with brake dust/metallic debris — false readings",
            "Sensor wiring chafed against fork/swingarm — intermittent signal loss",
            "Tone ring damaged or cracked — irregular signal pattern",
            "Sensor gap changed from axle adjustment — signal too weak",
        ],
        "diagnostic_tips": [
            "ABS light ON: read codes first (dealer tool or self-diagnostic mode)",
            "Clean sensor tip with brake cleaner at every tire change — 90% of ABS faults are contamination",
            "After chain/sprocket work: verify rear sensor gap hasn't changed from axle position",
            "Unexpected ABS activation at low speed: usually dirty sensor or mismatched tire sizes",
        ],
    },
]


def get_circuit_reference(circuit_name: str) -> Optional[CircuitReference]:
    """Look up a circuit reference by name (partial match)."""
    name_lower = circuit_name.lower()
    for ref_dict in CIRCUIT_REFERENCES:
        if name_lower in ref_dict["circuit_name"].lower():
            wires = [WireReference(**w) for w in ref_dict.get("wires", [])]
            return CircuitReference(
                circuit_name=ref_dict["circuit_name"],
                system=ref_dict.get("system", ""),
                description=ref_dict.get("description", ""),
                makes_applicable=ref_dict.get("makes_applicable", []),
                wires=wires,
                test_points=ref_dict.get("test_points", []),
                common_failures=ref_dict.get("common_failures", []),
                diagnostic_tips=ref_dict.get("diagnostic_tips", []),
            )
    return None


def get_circuits_by_system(system: str) -> list[CircuitReference]:
    """Get all circuit references for a given system (electrical, fuel, ignition, braking)."""
    results = []
    for ref_dict in CIRCUIT_REFERENCES:
        if ref_dict.get("system", "").lower() == system.lower():
            wires = [WireReference(**w) for w in ref_dict.get("wires", [])]
            results.append(CircuitReference(
                circuit_name=ref_dict["circuit_name"],
                system=ref_dict.get("system", ""),
                description=ref_dict.get("description", ""),
                makes_applicable=ref_dict.get("makes_applicable", []),
                wires=wires,
                test_points=ref_dict.get("test_points", []),
                common_failures=ref_dict.get("common_failures", []),
                diagnostic_tips=ref_dict.get("diagnostic_tips", []),
            ))
    return results


def list_all_circuits() -> list[str]:
    """Return a list of all available circuit reference names."""
    return [ref["circuit_name"] for ref in CIRCUIT_REFERENCES]


def build_wiring_context(circuit: CircuitReference) -> str:
    """Format a circuit reference into context for AI prompt injection."""
    lines = [
        f"\n--- Circuit Reference: {circuit.circuit_name} ---",
        f"System: {circuit.system}",
        f"Description: {circuit.description}",
        f"Applicable makes: {', '.join(circuit.makes_applicable)}",
        "",
        "Wire details:",
    ]
    for wire in circuit.wires:
        line = f"  [{wire.color}] {wire.function}"
        if wire.expected_voltage:
            line += f" — Expected: {wire.expected_voltage}"
        if wire.expected_resistance:
            line += f" — Expected: {wire.expected_resistance}"
        lines.append(line)

    lines.append("\nTest points:")
    for tp in circuit.test_points:
        lines.append(f"  • {tp}")

    lines.append("\nCommon failures:")
    for cf in circuit.common_failures:
        lines.append(f"  • {cf}")

    lines.append("\nDiagnostic tips:")
    for tip in circuit.diagnostic_tips:
        lines.append(f"  • {tip}")

    return "\n".join(lines)
