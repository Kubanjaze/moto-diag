"""Command registry for modular CLI organization.

Phase 109: Allows subcommand modules to register themselves with the main CLI
group. Each Track D phase (110-120) will create its own command module and
register it here.
"""

from typing import Callable, Optional

from pydantic import BaseModel, Field


class CommandInfo(BaseModel):
    """Metadata about a registered CLI command."""
    name: str = Field(..., description="Command name as exposed on the CLI")
    description: str = Field(default="", description="Short description shown in help")
    group: str = Field(default="main", description="Command group (main, diagnostic, data, admin)")
    added_in_phase: int = Field(default=0, description="Phase where this command was added")
    required_tier: Optional[str] = Field(None, description="Minimum subscription tier, if gated")


class CommandRegistry:
    """Registry of CLI commands for modular organization and help generation.

    Phase 109 provides the registration infrastructure. Subsequent phases
    (110-120) register their commands here so the main CLI can build
    a complete help index without tight coupling.
    """

    def __init__(self):
        self._commands: dict[str, CommandInfo] = {}
        self._callbacks: dict[str, Callable] = {}

    def register(
        self,
        name: str,
        callback: Callable,
        description: str = "",
        group: str = "main",
        added_in_phase: int = 0,
        required_tier: Optional[str] = None,
    ) -> None:
        """Register a CLI command with its metadata."""
        self._commands[name] = CommandInfo(
            name=name,
            description=description,
            group=group,
            added_in_phase=added_in_phase,
            required_tier=required_tier,
        )
        self._callbacks[name] = callback

    def get(self, name: str) -> Optional[CommandInfo]:
        """Get command info by name."""
        return self._commands.get(name)

    def get_callback(self, name: str) -> Optional[Callable]:
        """Get the registered callback for a command name."""
        return self._callbacks.get(name)

    def list_commands(self, group: Optional[str] = None) -> list[CommandInfo]:
        """List all registered commands, optionally filtered by group."""
        cmds = list(self._commands.values())
        if group:
            cmds = [c for c in cmds if c.group == group]
        return sorted(cmds, key=lambda c: (c.group, c.name))

    def groups(self) -> list[str]:
        """Return all unique command groups."""
        return sorted({c.group for c in self._commands.values()})

    def count(self) -> int:
        """Return total number of registered commands."""
        return len(self._commands)

    def is_registered(self, name: str) -> bool:
        """Check if a command is registered."""
        return name in self._commands

    def clear(self) -> None:
        """Clear all registered commands. Mainly for testing."""
        self._commands.clear()
        self._callbacks.clear()


# Global singleton registry — imported by command modules
_global_registry: CommandRegistry = CommandRegistry()


def get_registry() -> CommandRegistry:
    """Get the global command registry instance."""
    return _global_registry


def register_command(
    name: str,
    description: str = "",
    group: str = "main",
    added_in_phase: int = 0,
    required_tier: Optional[str] = None,
) -> Callable:
    """Decorator that registers a function as a CLI command.

    Usage:
        @register_command("garage", "Manage vehicle garage", group="diagnostic", added_in_phase=110)
        def garage_command(): ...
    """
    def decorator(func: Callable) -> Callable:
        get_registry().register(
            name=name,
            callback=func,
            description=description,
            group=group,
            added_in_phase=added_in_phase,
            required_tier=required_tier,
        )
        return func
    return decorator
