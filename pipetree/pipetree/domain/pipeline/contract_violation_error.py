"""Pipeline-related errors."""


class ContractViolationError(Exception):
    """Raised when a step violates its capability contract."""

    pass
