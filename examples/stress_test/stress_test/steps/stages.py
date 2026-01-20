"""Main pipeline stages for stress testing."""

import asyncio
import json
import random
import time

from pipetree import Step, step

from ..context import StressTestContext


@step(requires={"name"}, provides={"initialized"})
class Initialize(Step):
    """Stage 1: Initialize the pipeline."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print(f"[1/21] Initializing pipeline: {ctx.name}")
        await asyncio.sleep(random.uniform(0.3, 0.8))

        ctx.initialized = True
        ctx.current_stage = 1
        ctx.stages_completed.append("initialize")
        ctx.data["start_time"] = time.time()

        return ctx


@step(requires={"initialized"}, provides={"raw_data", "ingested"})
class IngestData(Step):
    """Stage 2: Ingest raw data with progress reporting."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print(f"[2/21] Ingesting data ({ctx.iterations} records)...")

        # Simulate ingesting multiple records with progress
        for i in range(ctx.iterations):
            await asyncio.sleep(random.uniform(0.1, 0.3))
            ctx.raw_data.append(
                {
                    "id": i + 1,
                    "value": random.randint(1, 100),
                    "timestamp": time.time(),
                    "source": f"source_{random.choice(['a', 'b', 'c'])}",
                }
            )
            ctx.report_progress(i + 1, ctx.iterations, f"Record {i + 1}")

        ctx.ingested = True
        ctx.current_stage = 2
        ctx.stages_completed.append("ingest_data")

        return ctx


@step(requires={"raw_data"}, provides={"validated", "validation_errors"})
class Validate(Step):
    """Stage 3: Validate ingested data."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print(f"[3/21] Validating {len(ctx.raw_data)} records...")

        for i, record in enumerate(ctx.raw_data):
            await asyncio.sleep(random.uniform(0.05, 0.15))

            # Simulate validation logic
            if record["value"] < 0:
                ctx.validation_errors.append(f"Record {record['id']}: negative value")

            ctx.report_progress(i + 1, len(ctx.raw_data), "Validating")

        ctx.validated = True
        ctx.current_stage = 3
        ctx.stages_completed.append("validate")

        return ctx


@step(requires={"validated", "raw_data"}, provides={"normalized", "normalized_data"})
class Normalize(Step):
    """Stage 4: Normalize validated data."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print(f"[4/21] Normalizing {len(ctx.raw_data)} records...")

        max_value = max(r["value"] for r in ctx.raw_data) if ctx.raw_data else 1

        for i, record in enumerate(ctx.raw_data):
            await asyncio.sleep(random.uniform(0.05, 0.1))

            normalized_record = {
                **record,
                "normalized_value": record["value"] / max_value,
                "normalized_at": time.time(),
            }
            ctx.normalized_data.append(normalized_record)
            ctx.report_progress(i + 1, len(ctx.raw_data), "Normalizing")

        ctx.normalized = True
        ctx.current_stage = 4
        ctx.stages_completed.append("normalize")

        return ctx


@step(requires={"normalized_data"}, provides={"enriched_stage1"})
class EnrichStage1(Step):
    """Stage 5: First enrichment pass."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[5/21] Enrichment Stage 1: Adding metadata...")

        for i, record in enumerate(ctx.normalized_data):
            await asyncio.sleep(random.uniform(0.05, 0.1))
            record["enriched_1"] = {
                "category": random.choice(["high", "medium", "low"]),
                "priority": random.randint(1, 5),
            }
            ctx.report_progress(i + 1, len(ctx.normalized_data), "Enriching")

        ctx.enriched_stage1 = True
        ctx.current_stage = 5
        ctx.stages_completed.append("enrich_stage1")

        return ctx


@step(requires={"enriched_stage1"}, provides={"enriched_stage2"})
class EnrichStage2(Step):
    """Stage 6: Second enrichment pass."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[6/21] Enrichment Stage 2: Adding external data...")

        for i, record in enumerate(ctx.normalized_data):
            await asyncio.sleep(random.uniform(0.05, 0.15))
            record["enriched_2"] = {
                "external_score": random.uniform(0, 1),
                "tags": random.sample(["tag1", "tag2", "tag3", "tag4", "tag5"], k=2),
            }
            ctx.report_progress(i + 1, len(ctx.normalized_data), "External data")

        ctx.enriched_stage2 = True
        ctx.current_stage = 6
        ctx.stages_completed.append("enrich_stage2")

        return ctx


@step(requires={"enriched_stage2"}, provides={"enriched_stage3"})
class EnrichStage3(Step):
    """Stage 7: Third enrichment pass."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[7/21] Enrichment Stage 3: Computing derived fields...")

        for i, record in enumerate(ctx.normalized_data):
            await asyncio.sleep(random.uniform(0.05, 0.1))
            record["enriched_3"] = {
                "derived_score": (
                    record["normalized_value"] * 0.5
                    + record["enriched_2"]["external_score"] * 0.5
                ),
                "computed_at": time.time(),
            }
            ctx.report_progress(i + 1, len(ctx.normalized_data), "Computing")

        ctx.enriched_stage3 = True
        ctx.current_stage = 7
        ctx.stages_completed.append("enrich_stage3")

        return ctx


@step(
    requires={"enriched_stage3", "normalized_data"},
    provides={"transformed", "transformed_data"},
)
class Transform(Step):
    """Stage 8: Transform enriched data."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[8/21] Transforming data...")

        for i, record in enumerate(ctx.normalized_data):
            await asyncio.sleep(random.uniform(0.05, 0.15))

            transformed = {
                "id": record["id"],
                "final_value": record["enriched_3"]["derived_score"],
                "category": record["enriched_1"]["category"],
                "priority": record["enriched_1"]["priority"],
                "tags": record["enriched_2"]["tags"],
                "source": record["source"],
                "processed_at": time.time(),
            }
            ctx.transformed_data.append(transformed)
            ctx.report_progress(i + 1, len(ctx.normalized_data), "Transforming")

        ctx.transformed = True
        ctx.current_stage = 8
        ctx.stages_completed.append("transform")

        return ctx


@step(requires={"transformed_data"}, provides={"analyzed_basic"})
class AnalyzeBasic(Step):
    """Stage 9: Basic analysis."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[9/21] Running basic analysis...")

        await asyncio.sleep(random.uniform(0.5, 1.0))
        ctx.report_progress(1, 3, "Computing stats")

        await asyncio.sleep(random.uniform(0.3, 0.6))
        ctx.report_progress(2, 3, "Aggregating")

        await asyncio.sleep(random.uniform(0.3, 0.6))
        ctx.report_progress(3, 3, "Finalizing")

        ctx.analysis_results["basic"] = {
            "count": len(ctx.transformed_data),
            "avg_value": sum(r["final_value"] for r in ctx.transformed_data)
            / len(ctx.transformed_data)
            if ctx.transformed_data
            else 0,
        }

        ctx.analyzed_basic = True
        ctx.current_stage = 9
        ctx.stages_completed.append("analyze_basic")

        return ctx


@step(requires={"analyzed_basic"}, provides={"analyzed_advanced"})
class AnalyzeAdvanced(Step):
    """Stage 10: Advanced analysis."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[10/21] Running advanced analysis...")

        # Simulate complex analysis
        for i in range(5):
            await asyncio.sleep(random.uniform(0.2, 0.4))
            ctx.report_progress(i + 1, 5, f"Analysis pass {i + 1}")

        values = [r["final_value"] for r in ctx.transformed_data]
        ctx.analysis_results["advanced"] = {
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "variance": sum(
                (v - ctx.analysis_results["basic"]["avg_value"]) ** 2 for v in values
            )
            / len(values)
            if values
            else 0,
        }

        ctx.analyzed_advanced = True
        ctx.current_stage = 10
        ctx.stages_completed.append("analyze_advanced")

        return ctx


@step(requires={"analyzed_advanced"}, provides={"analyzed_deep", "analysis_results"})
class AnalyzeDeep(Step):
    """Stage 11: Deep analysis."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[11/21] Running deep analysis...")

        # Simulate deep learning analysis
        for i in range(8):
            await asyncio.sleep(random.uniform(0.15, 0.3))
            ctx.report_progress(i + 1, 8, f"Deep analysis {i + 1}/8")

        # Category distribution
        categories = {}
        for record in ctx.transformed_data:
            cat = record["category"]
            categories[cat] = categories.get(cat, 0) + 1

        ctx.analysis_results["deep"] = {
            "category_distribution": categories,
            "insights": [
                "Pattern A detected",
                "Anomaly B identified",
                "Trend C observed",
            ],
        }

        ctx.analyzed_deep = True
        ctx.current_stage = 11
        ctx.stages_completed.append("analyze_deep")

        return ctx


@step(requires={"analysis_results"}, provides={"aggregated", "aggregation_results"})
class Aggregate(Step):
    """Stage 12: Aggregate all analysis results."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[12/21] Aggregating results...")

        await asyncio.sleep(random.uniform(0.5, 1.0))
        ctx.report_progress(1, 2, "Merging results")

        await asyncio.sleep(random.uniform(0.3, 0.6))
        ctx.report_progress(2, 2, "Computing summary")

        ctx.aggregation_results = {
            "summary": {
                "total_records": len(ctx.transformed_data),
                "basic_stats": ctx.analysis_results.get("basic", {}),
                "advanced_stats": ctx.analysis_results.get("advanced", {}),
                "deep_insights": ctx.analysis_results.get("deep", {}).get(
                    "insights", []
                ),
            },
            "aggregated_at": time.time(),
        }

        ctx.aggregated = True
        ctx.current_stage = 12
        ctx.stages_completed.append("aggregate")

        return ctx


@step(
    requires={"aggregation_results"},
    provides={"quality_checked", "quality_score", "quality"},
)
class QualityCheck(Step):
    """Stage 13: Check quality of results."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[13/21] Running quality checks...")

        checks = ["completeness", "accuracy", "consistency", "timeliness"]
        scores = []

        for i, check in enumerate(checks):
            await asyncio.sleep(random.uniform(0.2, 0.4))
            score = random.uniform(0.7, 1.0)
            scores.append(score)
            ctx.report_progress(i + 1, len(checks), f"Checking {check}")

        ctx.quality_score = sum(scores) / len(scores)

        # Set routing attribute based on quality score
        if ctx.quality_score >= 0.9:
            ctx.quality = "high"
        elif ctx.quality_score >= 0.8:
            ctx.quality = "medium"
        else:
            ctx.quality = "low"

        ctx.quality_checked = True
        ctx.current_stage = 13
        ctx.stages_completed.append("quality_check")

        print(f"    Quality score: {ctx.quality_score:.2f} -> {ctx.quality}")

        return ctx


@step(requires={"quality_checked"}, provides={"optimized"})
class Optimize(Step):
    """Stage 14: Optimize results."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[14/21] Optimizing...")

        for i in range(4):
            await asyncio.sleep(random.uniform(0.2, 0.4))
            ctx.report_progress(i + 1, 4, f"Optimization pass {i + 1}")

        ctx.optimized = True
        ctx.current_stage = 14
        ctx.stages_completed.append("optimize")

        return ctx


@step(
    requires={"optimized", "aggregation_results"},
    provides={"serialized", "serialized_data"},
)
class Serialize(Step):
    """Stage 15: Serialize results."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[15/21] Serializing results...")

        await asyncio.sleep(random.uniform(0.3, 0.6))
        ctx.report_progress(1, 2, "Converting to JSON")

        ctx.serialized_data = json.dumps(ctx.aggregation_results, indent=2, default=str)

        await asyncio.sleep(random.uniform(0.2, 0.4))
        ctx.report_progress(2, 2, "Serialization complete")

        ctx.serialized = True
        ctx.current_stage = 15
        ctx.stages_completed.append("serialize")

        return ctx


@step(requires={"serialized_data"}, provides={"compressed"})
class Compress(Step):
    """Stage 16: Compress serialized data."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[16/21] Compressing data...")

        await asyncio.sleep(random.uniform(0.4, 0.8))
        ctx.report_progress(1, 1, "Compressing")

        ctx.compressed = True
        ctx.current_stage = 16
        ctx.stages_completed.append("compress")

        return ctx


@step(requires={"compressed"}, provides={"encrypted"})
class Encrypt(Step):
    """Stage 17: Encrypt compressed data."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[17/21] Encrypting data...")

        await asyncio.sleep(random.uniform(0.3, 0.6))
        ctx.report_progress(1, 2, "Generating keys")

        await asyncio.sleep(random.uniform(0.3, 0.6))
        ctx.report_progress(2, 2, "Encrypting")

        ctx.encrypted = True
        ctx.current_stage = 17
        ctx.stages_completed.append("encrypt")

        return ctx


@step(requires={"encrypted"}, provides={"output_generated"})
class GenerateOutput(Step):
    """Stage 18: Generate final output."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[18/21] Generating output...")

        for i in range(3):
            await asyncio.sleep(random.uniform(0.2, 0.4))
            ctx.report_progress(i + 1, 3, f"Generating output {i + 1}/3")

        ctx.output_generated = True
        ctx.current_stage = 18
        ctx.stages_completed.append("generate_output")

        return ctx


@step(requires={"output_generated"}, provides={"notified"})
class Notify(Step):
    """Stage 19: Send notifications."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[19/21] Sending notifications...")

        notifications = ["email", "slack", "webhook"]
        for i, notif in enumerate(notifications):
            await asyncio.sleep(random.uniform(0.2, 0.4))
            ctx.report_progress(i + 1, len(notifications), f"Sending {notif}")

        ctx.notified = True
        ctx.current_stage = 19
        ctx.stages_completed.append("notify")

        return ctx


@step(requires={"notified"}, provides={"cleaned_up"})
class Cleanup(Step):
    """Stage 20: Cleanup temporary resources."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[20/21] Cleaning up...")

        await asyncio.sleep(random.uniform(0.3, 0.6))
        ctx.report_progress(1, 2, "Removing temp files")

        await asyncio.sleep(random.uniform(0.2, 0.4))
        ctx.report_progress(2, 2, "Releasing resources")

        ctx.cleaned_up = True
        ctx.current_stage = 20
        ctx.stages_completed.append("cleanup")

        return ctx


@step(requires={"cleaned_up"}, provides={"completed"})
class Complete(Step):
    """Stage 21: Mark pipeline as complete."""

    async def run(self, ctx: StressTestContext) -> StressTestContext:
        print("[21/21] Completing pipeline...")

        await asyncio.sleep(random.uniform(0.2, 0.4))

        ctx.data["end_time"] = time.time()
        ctx.data["total_duration"] = ctx.data["end_time"] - ctx.data["start_time"]

        ctx.completed = True
        ctx.current_stage = 21
        ctx.stages_completed.append("complete")

        return ctx
