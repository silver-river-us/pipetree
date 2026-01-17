"""
Pipetree - A modular, benchmarkable pipeline framework for document processing.

This module re-exports all public APIs.
The codebase follows DDD and Screaming Architecture patterns:

- domain/           Core business logic (Capability, Step, Pipetree, Types)
- infrastructure/   External concerns (CheckpointStore, Registry)
- benchmarking/     A/B testing and performance evaluation
"""

# Domain - Types
# Benchmarking
from pipetree.benchmarking import BenchRunner, Fixture, Metrics

# Domain - Capability
from pipetree.domain.capability import Capability

# Domain - Pipetree
from pipetree.domain.pipeline import ContractViolationError, Pipetree

# Domain - Step
from pipetree.domain.step import Router, Step
from pipetree.domain.types import (
    Chunk,
    ConcurrencyConfig,
    Context,
    Cursor,
    VecBatch,
    VecRecord,
)

# Infrastructure - Checkpoint
from pipetree.infrastructure.checkpoint import (
    CheckpointStore,
    FileCheckpointStore,
    InMemoryCheckpointStore,
)

# Infrastructure - Progress
from pipetree.infrastructure.progress import (
    FileProgressNotifier,
    InMemoryProgressNotifier,
    NullProgressNotifier,
    ProgressEvent,
    ProgressNotifier,
    SQLiteProgressNotifier,
)

# Infrastructure - Registry
from pipetree.infrastructure.registry import Registry, global_registry, register

__all__ = [
    # Types
    "Chunk",
    "ConcurrencyConfig",
    "Context",
    "Cursor",
    "VecBatch",
    "VecRecord",
    # Capability
    "Capability",
    # Step
    "Step",
    "Router",
    # Pipeline
    "Pipetree",
    "ContractViolationError",
    # Checkpoint
    "CheckpointStore",
    "InMemoryCheckpointStore",
    "FileCheckpointStore",
    # Progress
    "ProgressEvent",
    "ProgressNotifier",
    "NullProgressNotifier",
    "InMemoryProgressNotifier",
    "FileProgressNotifier",
    "SQLiteProgressNotifier",
    # Registry
    "Registry",
    "global_registry",
    "register",
    # Benchmarking
    "Fixture",
    "Metrics",
    "BenchRunner",
]
