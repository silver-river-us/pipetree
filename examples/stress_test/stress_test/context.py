"""Context for the stress test pipeline."""

from dataclasses import dataclass, field

from pipetree import Context


@dataclass
class StressTestContext(Context):
    """Context that accumulates data through many pipeline stages."""

    # Initial input
    name: str = "stress_test"
    iterations: int = 10

    # Stage tracking
    current_stage: int = 0
    stages_completed: list[str] = field(default_factory=list)

    # Data accumulation through stages
    data: dict = field(default_factory=dict)

    # Initialization
    initialized: bool = False

    # Data ingestion
    raw_data: list[dict] = field(default_factory=list)
    ingested: bool = False

    # Validation
    validated: bool = False
    validation_errors: list[str] = field(default_factory=list)

    # Normalization
    normalized: bool = False
    normalized_data: list[dict] = field(default_factory=list)

    # Enrichment stages
    enriched_stage1: bool = False
    enriched_stage2: bool = False
    enriched_stage3: bool = False

    # Transformation
    transformed: bool = False
    transformed_data: list[dict] = field(default_factory=list)

    # Analysis stages
    analyzed_basic: bool = False
    analyzed_advanced: bool = False
    analyzed_deep: bool = False
    analysis_results: dict = field(default_factory=dict)

    # Aggregation
    aggregated: bool = False
    aggregation_results: dict = field(default_factory=dict)

    # Quality check
    quality_checked: bool = False
    quality_score: float = 0.0

    # Optimization
    optimized: bool = False

    # Serialization
    serialized: bool = False
    serialized_data: str = ""

    # Compression
    compressed: bool = False

    # Encryption
    encrypted: bool = False

    # Output generation
    output_generated: bool = False

    # Notification
    notified: bool = False

    # Cleanup
    cleaned_up: bool = False

    # Final stage
    completed: bool = False

    # Branch-specific results
    branch_a_result: dict | None = None
    branch_b_result: dict | None = None
    branch_c_result: dict | None = None
