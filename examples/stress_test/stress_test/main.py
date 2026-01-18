"""
Stress Test Pipeline Example

A very long pipeline with 21+ steps to test the visualizer's performance
with many sequential steps, progress reporting, and branching.

Pipeline Structure:
  1. initialize
  2. ingest_data (with progress)
  3. validate (with progress)
  4. normalize (with progress)
  5. enrich_stage1 (with progress)
  6. enrich_stage2 (with progress)
  7. enrich_stage3 (with progress)
  8. transform (with progress)
  9. analyze_basic (with progress)
  10. analyze_advanced (with progress)
  11. analyze_deep (with progress)
  12. aggregate (with progress)
  13. quality_check (with progress)
  14. route_by_quality -> [high | medium | low]
  15. optimize (with progress)
  16. serialize (with progress)
  17. compress
  18. encrypt (with progress)
  19. generate_output (with progress)
  20. notify (with progress)
  21. cleanup (with progress)
  22. complete
"""

import asyncio
import time
from pathlib import Path
from threading import Event, Thread

from pipetree import Pipetree, SQLiteProgressNotifier

from .capabilities import (
    AGGREGATE,
    ANALYZE_ADVANCED,
    ANALYZE_BASIC,
    ANALYZE_DEEP,
    CLEANUP,
    COMPLETE,
    COMPRESS,
    ENCRYPT,
    ENRICH_STAGE1,
    ENRICH_STAGE2,
    ENRICH_STAGE3,
    GENERATE_OUTPUT,
    INGEST_DATA,
    INITIALIZE,
    NORMALIZE,
    NOTIFY,
    OPTIMIZE,
    PROCESS_HIGH_QUALITY,
    PROCESS_LOW_QUALITY,
    PROCESS_MEDIUM_QUALITY,
    QUALITY_CHECK,
    ROUTE_BY_QUALITY,
    SERIALIZE,
    TRANSFORM,
    VALIDATE,
)
from .context import StressTestContext
from .steps import (
    AggregateStep,
    AnalyzeAdvancedStep,
    AnalyzeBasicStep,
    AnalyzeDeepStep,
    CleanupStep,
    CompleteStep,
    CompressStep,
    EncryptStep,
    EnrichStage1Step,
    EnrichStage2Step,
    EnrichStage3Step,
    GenerateOutputStep,
    IngestDataStep,
    InitializeStep,
    NormalizeStep,
    NotifyStep,
    OptimizeStep,
    ProcessHighQualityStep,
    ProcessLowQualityStep,
    ProcessMediumQualityStep,
    QualityCheckStep,
    QualityRouter,
    SerializeStep,
    TransformStep,
    ValidateStep,
)


def watch_progress(db_path: Path, run_id: str, stop_event: Event) -> None:
    """Simple progress watcher that prints updates."""
    import sqlite3

    last_event_id = 0

    while not stop_event.is_set():
        try:
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT id, step_index, event_type, message, current, total
                    FROM events
                    WHERE run_id = ? AND id > ?
                    ORDER BY id
                    """,
                    (run_id, last_event_id),
                )

                for row in cursor.fetchall():
                    event_id, _step_index, _event_type, _message, _current, _total = row
                    last_event_id = event_id

                conn.close()

            stop_event.wait(0.2)

        except Exception:
            stop_event.wait(0.5)


def create_pipeline(
    db_path: Path | None = None,
) -> tuple[Pipetree, SQLiteProgressNotifier | None]:
    """Create the stress test pipeline."""
    notifier = SQLiteProgressNotifier(db_path) if db_path else None

    pipeline = Pipetree(
        steps=[
            # Stage 1-4: Initial processing
            InitializeStep(INITIALIZE, "initialize"),
            IngestDataStep(INGEST_DATA, "ingest_data"),
            ValidateStep(VALIDATE, "validate"),
            NormalizeStep(NORMALIZE, "normalize"),
            # Stage 5-7: Enrichment (3 stages)
            EnrichStage1Step(ENRICH_STAGE1, "enrich_stage1"),
            EnrichStage2Step(ENRICH_STAGE2, "enrich_stage2"),
            EnrichStage3Step(ENRICH_STAGE3, "enrich_stage3"),
            # Stage 8: Transformation
            TransformStep(TRANSFORM, "transform"),
            # Stage 9-11: Analysis (3 stages)
            AnalyzeBasicStep(ANALYZE_BASIC, "analyze_basic"),
            AnalyzeAdvancedStep(ANALYZE_ADVANCED, "analyze_advanced"),
            AnalyzeDeepStep(ANALYZE_DEEP, "analyze_deep"),
            # Stage 12-13: Aggregation and Quality
            AggregateStep(AGGREGATE, "aggregate"),
            QualityCheckStep(QUALITY_CHECK, "quality_check"),
            # Stage 14: Quality-based routing
            QualityRouter(
                cap=ROUTE_BY_QUALITY,
                name="route_by_quality",
                table={
                    "high": ProcessHighQualityStep(
                        PROCESS_HIGH_QUALITY, "process_high_quality"
                    ),
                    "medium": ProcessMediumQualityStep(
                        PROCESS_MEDIUM_QUALITY, "process_medium_quality"
                    ),
                    "low": ProcessLowQualityStep(
                        PROCESS_LOW_QUALITY, "process_low_quality"
                    ),
                },
                default="medium",
            ),
            # Stage 15-22: Final processing
            OptimizeStep(OPTIMIZE, "optimize"),
            SerializeStep(SERIALIZE, "serialize"),
            CompressStep(COMPRESS, "compress"),
            EncryptStep(ENCRYPT, "encrypt"),
            GenerateOutputStep(GENERATE_OUTPUT, "generate_output"),
            NotifyStep(NOTIFY, "notify"),
            CleanupStep(CLEANUP, "cleanup"),
            CompleteStep(COMPLETE, "complete"),
        ],
        progress_notifier=notifier,
        name="Stress Test Pipeline",
    )

    # Register branches with the notifier
    if notifier:
        notifier.register_branch(
            parent_step="route_by_quality",
            branch_name="high",
            step_names=["process_high_quality"],
            start_index=14,
        )
        notifier.register_branch(
            parent_step="route_by_quality",
            branch_name="medium",
            step_names=["process_medium_quality"],
            start_index=14,
        )
        notifier.register_branch(
            parent_step="route_by_quality",
            branch_name="low",
            step_names=["process_low_quality"],
            start_index=14,
        )

    return pipeline, notifier


async def main(iterations: int = 15) -> None:
    """Run the stress test pipeline."""
    project_root = Path(__file__).parent.parent
    db_path = project_root / "db" / "progress.db"

    # Ensure db directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Stress Test Pipeline")
    print("=" * 60)
    print(f"Database: {db_path}")
    print(f"Iterations: {iterations}")
    print()
    print("Pipeline structure (22 steps):")
    print("  1. initialize")
    print("  2. ingest_data -> 3. validate -> 4. normalize")
    print("  5. enrich_stage1 -> 6. enrich_stage2 -> 7. enrich_stage3")
    print("  8. transform")
    print("  9. analyze_basic -> 10. analyze_advanced -> 11. analyze_deep")
    print("  12. aggregate -> 13. quality_check")
    print("  14. route_by_quality")
    print("       |-- high -> process_high_quality")
    print("       |-- medium -> process_medium_quality")
    print("       |-- low -> process_low_quality")
    print("  15. optimize -> 16. serialize -> 17. compress -> 18. encrypt")
    print("  19. generate_output -> 20. notify -> 21. cleanup -> 22. complete")
    print()
    print("View progress at: http://localhost:8000")
    print("=" * 60)
    print()

    # Create pipeline
    pipeline, notifier = create_pipeline(db_path=db_path)
    run_id = notifier.run_id if notifier else ""

    # Start progress watcher
    stop_event = Event()
    watcher_thread = Thread(target=watch_progress, args=(db_path, run_id, stop_event))
    watcher_thread.start()

    # Create context
    ctx = StressTestContext(
        name="stress_test_run",
        iterations=iterations,
    )

    # Run pipeline
    start_time = time.perf_counter()
    try:
        result = await pipeline.run(ctx)
        total_time = time.perf_counter() - start_time

        # Stop watcher
        stop_event.set()
        watcher_thread.join(timeout=1.0)

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
        stop_event.set()
        watcher_thread.join(timeout=1.0)
        print(f"Pipeline failed: {e}")
        raise

    finally:
        if notifier:
            notifier.close()


if __name__ == "__main__":
    import sys

    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    asyncio.run(main(iterations=iterations))
