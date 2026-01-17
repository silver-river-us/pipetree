"""Judge functions for evaluating benchmark correctness."""

from collections.abc import Callable

from ingestion.benchmarking.fixture import Fixture
from ingestion.benchmarking.metrics import Metrics
from ingestion.domain.types.context import Ctx

# Judge function type: evaluates correctness and returns metrics
JudgeFn = Callable[[Fixture, Ctx], Metrics]


def accuracy_judge(fixture: Fixture, ctx: Ctx) -> Metrics:
    """Simple accuracy judge for classification tasks."""
    expected = fixture.get("expected", {})
    correct = 0
    total = 0

    for key, expected_value in expected.items():
        if key in ctx:
            total += 1
            if ctx[key] == expected_value:  # type: ignore
                correct += 1

    correctness = correct / total if total > 0 else 0.0
    return {"correctness": correctness, "details": {"correct": correct, "total": total}}
