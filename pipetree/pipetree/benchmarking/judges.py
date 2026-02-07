"""Judge functions for evaluating benchmark correctness."""

from collections.abc import Callable

from pipetree.benchmarking.fixture import Fixture
from pipetree.benchmarking.metrics import Metrics
from pipetree.domain.types.context import Context

# Judge function type: evaluates correctness and returns metrics
JudgeFn = Callable[[Fixture, Context], Metrics]


def accuracy_judge(fixture: Fixture, ctx: Context) -> Metrics:
    """Simple accuracy judge for classification tasks."""
    expected = fixture.get("expected", {})
    correct = 0
    total = 0

    for key, expected_value in expected.items():
        if ctx.has(key):
            total += 1
            if ctx.get(key) == expected_value:
                correct += 1

    correctness = correct / total if total > 0 else 0.0
    return {"correctness": correctness, "details": {"correct": correct, "total": total}}
