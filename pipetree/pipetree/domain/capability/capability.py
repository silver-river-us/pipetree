"""Capability-based contract system."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    """
    Defines a contract for a step with explicit pre/postconditions.

    Steps are interchangeable only if they implement the same capability.
    The pipeline validates contracts before and after each step.
    """

    name: str
    requires: set[str] = field(default_factory=set)
    provides: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        # Convert to frozenset for immutability
        object.__setattr__(self, "requires", frozenset(self.requires))
        object.__setattr__(self, "provides", frozenset(self.provides))

    def validate_preconditions(self, ctx_keys: set[str]) -> bool:
        """Check if context satisfies preconditions."""
        return self.requires <= ctx_keys

    def missing_requirements(self, ctx_keys: set[str]) -> set[str]:
        """Return missing required keys."""
        return self.requires - ctx_keys
