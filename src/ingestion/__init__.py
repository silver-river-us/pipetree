"""
Ingestion Framework - A modular, benchmarkable ingestion framework for large PDFs.

This module re-exports all public APIs for backward compatibility.
The codebase follows DDD and Screaming Architecture patterns:

- domain/           Core business logic (Capability, Step, Pipeline, Types)
- infrastructure/   External concerns (CheckpointStore, Registry)
- benchmarking/     A/B testing and performance evaluation
"""

# Domain - Types
# Benchmarking
from ingestion.benchmarking import BenchRunner, Fixture, Metrics

# Domain - Capability
from ingestion.domain.capability import Capability

# Domain - Pipeline
from ingestion.domain.pipeline import ContractViolationError, Pipeline

# Domain - Step
from ingestion.domain.step import BaseRouter, BaseStep, Router, Step
from ingestion.domain.types import (
    Chunk,
    ConcurrencyConfig,
    Ctx,
    Cursor,
    VecBatch,
    VecRecord,
)

# Infrastructure - Checkpoint
from ingestion.infrastructure.checkpoint import (
    CheckpointStore,
    FileCheckpointStore,
    InMemoryCheckpointStore,
)

# Infrastructure - Registry
from ingestion.infrastructure.registry import Registry, global_registry

__all__ = [
    # Types
    "Cursor",
    "Chunk",
    "VecRecord",
    "VecBatch",
    "Ctx",
    "ConcurrencyConfig",
    # Capability
    "Capability",
    # Step
    "Step",
    "Router",
    "BaseStep",
    "BaseRouter",
    # Pipeline
    "Pipeline",
    "ContractViolationError",
    # Checkpoint
    "CheckpointStore",
    "InMemoryCheckpointStore",
    "FileCheckpointStore",
    # Registry
    "Registry",
    "global_registry",
    # Benchmarking
    "Fixture",
    "Metrics",
    "BenchRunner",
]
