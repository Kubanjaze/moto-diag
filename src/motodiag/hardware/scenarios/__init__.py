"""Built-in hardware-simulator scenarios (Phase 144).

The ten YAML files shipped in this package are the factory-stocked
scenario library for :class:`~motodiag.hardware.simulator.SimulatedAdapter`.
They cover the common diagnostic drills a shop mechanic would rehearse
on a working dyno bench — idle baseline, cold-start warmup, overheat
development, misfire, lean fault, O2 sensor failure, charging fault,
ECU dropout, and two bike-specific warmups (Harley Sportster J1850 VPW,
Honda CBR600 KWP2000).

The ``BUILTIN_NAMES`` tuple is the source of truth for the CLI's
``simulate list`` discovery path and for the Phase 144 test suite's
parametrized loader tests. Adding a new built-in requires (1) the YAML
file, (2) an entry here, (3) a new parametrize case in the test suite.

``importlib.resources`` is the loader of record — it works identically
whether the package is installed from a wheel, an editable install, or
a zipapp, which matters because moto-diag ships all three.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path


BUILTIN_NAMES: tuple[str, ...] = (
    "cbr600_warm_idle",
    "charging_fault",
    "cold_start",
    "ecu_crash_recovery",
    "harley_sporty_warmup",
    "healthy_idle",
    "lean_fault",
    "misfire",
    "o2_sensor_fail",
    "overheat",
)


def builtin_path(name: str) -> Path:
    """Return the filesystem :class:`Path` to a built-in YAML by name.

    Raises :class:`FileNotFoundError` if the name is not in
    :data:`BUILTIN_NAMES`. Uses ``importlib.resources.files`` so the
    lookup works across wheel / editable / zipapp installs.
    """
    if name not in BUILTIN_NAMES:
        raise FileNotFoundError(
            f"{name!r} is not a built-in scenario; "
            f"known: {', '.join(BUILTIN_NAMES)}"
        )
    resource = resources.files(__package__).joinpath(f"{name}.yaml")
    # Traversable → filesystem path; `.as_posix()` works on all installs
    # but we want a pathlib.Path for the API.
    return Path(str(resource))


__all__ = ["BUILTIN_NAMES", "builtin_path"]
