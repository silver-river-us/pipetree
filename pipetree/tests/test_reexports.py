"""Tests for backward-compatible re-export modules."""


class TestPipelineReexports:
    """Test pipetree.pipeline re-exports."""

    def test_imports_from_pipeline_module(self) -> None:
        """Test that pipeline module re-exports work."""
        # Verify they're the same as domain imports
        from pipetree.domain.pipeline import (
            ContractViolationError as DomainError,
        )
        from pipetree.domain.pipeline import (
            Pipetree as DomainPipetree,
        )
        from pipetree.pipeline import ContractViolationError, Pipetree

        assert ContractViolationError is DomainError
        assert Pipetree is DomainPipetree


class TestRegistryReexports:
    """Test pipetree.registry re-exports."""

    def test_imports_from_registry_module(self) -> None:
        """Test that registry module re-exports work."""
        # Verify they're the same as infrastructure imports
        from pipetree.infrastructure.registry import (
            Registry as InfraRegistry,
        )
        from pipetree.infrastructure.registry import (
            global_registry as infra_global,
        )
        from pipetree.infrastructure.registry import (
            register as infra_register,
        )
        from pipetree.registry import Registry, global_registry, register

        assert Registry is InfraRegistry
        assert global_registry is infra_global
        assert register is infra_register
