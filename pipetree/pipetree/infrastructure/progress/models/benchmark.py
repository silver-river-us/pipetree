"""Benchmark model - represents a benchmark suite for comparing implementations."""

from sqlmodel import Field, Relationship, SQLModel


class Benchmark(SQLModel, table=True):
    """A benchmark suite comparing multiple implementations of a capability."""

    __tablename__ = "benchmarks"

    id: str = Field(primary_key=True)
    name: str  # Human-readable name, e.g., "Text Extraction Comparison"
    capability: str  # The capability being benchmarked, e.g., "text_extraction"
    description: str | None = None
    created_at: float | None = None
    completed_at: float | None = None
    status: str = Field(default="pending")  # pending, running, completed, failed

    # Relationships
    results: list["BenchmarkResult"] = Relationship(back_populates="benchmark")


class BenchmarkResult(SQLModel, table=True):
    """A single benchmark result for one implementation on one fixture."""

    __tablename__ = "benchmark_results"

    id: int | None = Field(default=None, primary_key=True)
    benchmark_id: str = Field(foreign_key="benchmarks.id", index=True)
    impl_name: str = Field(index=True)  # Implementation name, e.g., "pypdf"
    fixture_id: str  # Identifier for the test fixture

    # Timing metrics
    wall_time_s: float | None = None
    cpu_time_s: float | None = None

    # Memory metrics
    peak_mem_mb: float | None = None

    # Throughput metrics
    throughput_items_s: float | None = None
    items_processed: int | None = None

    # Quality metrics
    correctness: float | None = None  # 0.0 - 1.0

    # Additional metrics as JSON
    extra_metrics: str | None = None  # JSON string for extensibility

    # Error info
    error: str | None = None

    # Relationships
    benchmark: "Benchmark" = Relationship(back_populates="results")


# Rebuild models to resolve forward references
Benchmark.model_rebuild()
BenchmarkResult.model_rebuild()
