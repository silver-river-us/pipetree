"""Capability definitions for the stress test pipeline."""

from pipetree import Capability

# Stage 1: Initialization
INITIALIZE = Capability(
    name="initialize",
    requires={"name"},
    provides={"initialized"},
)

# Stage 2: Data Ingestion
INGEST_DATA = Capability(
    name="ingest_data",
    requires={"initialized"},
    provides={"raw_data", "ingested"},
)

# Stage 3: Validation
VALIDATE = Capability(
    name="validate",
    requires={"raw_data"},
    provides={"validated", "validation_errors"},
)

# Stage 4: Normalization
NORMALIZE = Capability(
    name="normalize",
    requires={"validated", "raw_data"},
    provides={"normalized", "normalized_data"},
)

# Stage 5-7: Enrichment (3 stages)
ENRICH_STAGE1 = Capability(
    name="enrich_stage1",
    requires={"normalized_data"},
    provides={"enriched_stage1"},
)

ENRICH_STAGE2 = Capability(
    name="enrich_stage2",
    requires={"enriched_stage1"},
    provides={"enriched_stage2"},
)

ENRICH_STAGE3 = Capability(
    name="enrich_stage3",
    requires={"enriched_stage2"},
    provides={"enriched_stage3"},
)

# Stage 8: Transformation
TRANSFORM = Capability(
    name="transform",
    requires={"enriched_stage3", "normalized_data"},
    provides={"transformed", "transformed_data"},
)

# Stage 9-11: Analysis (3 stages)
ANALYZE_BASIC = Capability(
    name="analyze_basic",
    requires={"transformed_data"},
    provides={"analyzed_basic"},
)

ANALYZE_ADVANCED = Capability(
    name="analyze_advanced",
    requires={"analyzed_basic"},
    provides={"analyzed_advanced"},
)

ANALYZE_DEEP = Capability(
    name="analyze_deep",
    requires={"analyzed_advanced"},
    provides={"analyzed_deep", "analysis_results"},
)

# Stage 12: Aggregation
AGGREGATE = Capability(
    name="aggregate",
    requires={"analysis_results"},
    provides={"aggregated", "aggregation_results"},
)

# Stage 13: Quality Check
QUALITY_CHECK = Capability(
    name="quality_check",
    requires={"aggregation_results"},
    provides={"quality_checked", "quality_score"},
)

# Stage 14: Optimization
OPTIMIZE = Capability(
    name="optimize",
    requires={"quality_checked"},
    provides={"optimized"},
)

# Stage 15: Serialization
SERIALIZE = Capability(
    name="serialize",
    requires={"optimized", "aggregation_results"},
    provides={"serialized", "serialized_data"},
)

# Stage 16: Compression
COMPRESS = Capability(
    name="compress",
    requires={"serialized_data"},
    provides={"compressed"},
)

# Stage 17: Encryption
ENCRYPT = Capability(
    name="encrypt",
    requires={"compressed"},
    provides={"encrypted"},
)

# Stage 18: Output Generation
GENERATE_OUTPUT = Capability(
    name="generate_output",
    requires={"encrypted"},
    provides={"output_generated"},
)

# Stage 19: Notification
NOTIFY = Capability(
    name="notify",
    requires={"output_generated"},
    provides={"notified"},
)

# Stage 20: Cleanup
CLEANUP = Capability(
    name="cleanup",
    requires={"notified"},
    provides={"cleaned_up"},
)

# Stage 21: Completion
COMPLETE = Capability(
    name="complete",
    requires={"cleaned_up"},
    provides={"completed"},
)

# Router capability for branching after analysis
ROUTE_BY_QUALITY = Capability(
    name="route_by_quality",
    requires={"quality_score"},
    provides={"branch_a_result", "branch_b_result", "branch_c_result"},
)

# Branch-specific capabilities
PROCESS_HIGH_QUALITY = Capability(
    name="process_high_quality",
    requires={"quality_score"},
    provides={"branch_a_result"},
)

PROCESS_MEDIUM_QUALITY = Capability(
    name="process_medium_quality",
    requires={"quality_score"},
    provides={"branch_b_result"},
)

PROCESS_LOW_QUALITY = Capability(
    name="process_low_quality",
    requires={"quality_score"},
    provides={"branch_c_result"},
)
