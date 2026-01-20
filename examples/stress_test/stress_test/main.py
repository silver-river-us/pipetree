"""
Stress Test Pipeline Example - DSL Version

A long pipeline with 22 steps to test the visualizer's performance
with many sequential steps, progress reporting, and branching.

Pipeline Structure (DSL):
    Initialize
    IngestData
    Validate
    Normalize
    EnrichStage1
    EnrichStage2
    EnrichStage3
    Transform
    AnalyzeBasic
    AnalyzeAdvanced
    AnalyzeDeep
    Aggregate
    QualityCheck
    quality >> [
        high >> ProcessHighQuality,
        medium >> ProcessMediumQuality,
        low >> ProcessLowQuality,
    ]
    Optimize
    Serialize
    Compress
    Encrypt
    GenerateOutput
    Notify
    Cleanup
    Complete
"""

import asyncio
import time
from pathlib import Path

from pipetree import (
    B,
    Pipetree,
    SQLiteProgressNotifier,
    SQLiteProgressWatcher,
    pipeline,
    route,
)

from .context import StressTestContext
from .steps import (
    Aggregate,
    AnalyzeAdvanced,
    AnalyzeBasic,
    AnalyzeDeep,
    Cleanup,
    Complete,
    Compress,
    Encrypt,
    EnrichStage1,
    EnrichStage2,
    EnrichStage3,
    GenerateOutput,
    IngestData,
    Initialize,
    Normalize,
    Notify,
    Optimize,
    ProcessHighQuality,
    ProcessLowQuality,
    ProcessMediumQuality,
    QualityCheck,
    Serialize,
    Transform,
    Validate,
)

# =============================================================================
# Route markers
# =============================================================================

quality = route("quality", default="medium")

# Branch markers
high = B("high")
medium = B("medium")
low = B("low")


# =============================================================================
# Pipeline definition - the structure is immediately visible!
# =============================================================================


def create_pipeline(
    db_path: Path | None = None,
) -> tuple[Pipetree, SQLiteProgressNotifier | None]:
    """Create the stress test pipeline."""
    notifier = SQLiteProgressNotifier(db_path) if db_path else None

    stress_pipeline = pipeline(
        "Stress Test Pipeline",
        [
            # Stage 1-4: Initial processing
            Initialize,
            IngestData,
            Validate,
            Normalize,
            # Stage 5-7: Enrichment
            EnrichStage1,
            EnrichStage2,
            EnrichStage3,
            # Stage 8: Transform
            Transform,
            # Stage 9-11: Analysis
            AnalyzeBasic,
            AnalyzeAdvanced,
            AnalyzeDeep,
            # Stage 12-13: Aggregation and Quality
            Aggregate,
            QualityCheck,
            # Stage 14: Quality-based routing
            quality
            >> [
                high >> ProcessHighQuality,
                medium >> ProcessMediumQuality,
                low >> ProcessLowQuality,
            ],
            # Stage 15-22: Final processing
            Optimize,
            Serialize,
            Compress,
            Encrypt,
            GenerateOutput,
            Notify,
            Cleanup,
            Complete,
        ],
        progress_notifier=notifier,
    )

    return stress_pipeline, notifier


# =============================================================================
# Main entry point
# =============================================================================


async def main(iterations: int = 15) -> None:
    """Run the stress test pipeline."""
    project_root = Path(__file__).parent.parent
    db_path = project_root / "db" / "progress.db"

    db_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Stress Test Pipeline (DSL Version)")
    print("=" * 60)
    print(f"Database: {db_path}")
    print(f"Iterations: {iterations}")
    print()
    print("Pipeline structure (22 steps):")
    print("  1. Initialize -> 2. IngestData -> 3. Validate -> 4. Normalize")
    print("  5. EnrichStage1 -> 6. EnrichStage2 -> 7. EnrichStage3")
    print("  8. Transform")
    print("  9. AnalyzeBasic -> 10. AnalyzeAdvanced -> 11. AnalyzeDeep")
    print("  12. Aggregate -> 13. QualityCheck")
    print("  14. quality >> [high, medium, low]")
    print("  15. Optimize -> 16. Serialize -> 17. Compress -> 18. Encrypt")
    print("  19. GenerateOutput -> 20. Notify -> 21. Cleanup -> 22. Complete")
    print()
    print("View progress at: http://localhost:8000")
    print("=" * 60)
    print()

    # Create pipeline
    stress_pipeline, notifier = create_pipeline(db_path=db_path)
    run_id = notifier.run_id if notifier else ""

    # Start progress watcher
    watcher = SQLiteProgressWatcher(db_path, run_id)
    watcher.start()

    # Create context
    ctx = StressTestContext(
        name="stress_test_run",
        iterations=iterations,
    )

    # Run pipeline
    start_time = time.perf_counter()
    try:
        result = await stress_pipeline.run(ctx)
        total_time = time.perf_counter() - start_time

        watcher.stop()

        # Summary
        print()
        print("=" * 60)
        print("Pipeline Complete!")
        print("=" * 60)
        print(f"Total stages completed: {len(result.stages_completed)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Quality score: {result.quality_score:.2f}")
        print(f"Records processed: {len(result.transformed_data)}")
        print()

        # Show branch result
        if result.branch_a_result:
            print(f"Branch taken: HIGH - {result.branch_a_result['action']}")
        elif result.branch_b_result:
            print(f"Branch taken: MEDIUM - {result.branch_b_result['action']}")
        elif result.branch_c_result:
            print(f"Branch taken: LOW - {result.branch_c_result['action']}")

        print()
        print(f"View run at: http://localhost:8000/runs/{run_id}?db={db_path}")

    except Exception as e:
        watcher.stop()
        print(f"Pipeline failed: {e}")
        raise

    finally:
        if notifier:
            notifier.close()


if __name__ == "__main__":
    import sys

    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    asyncio.run(main(iterations=iterations))
