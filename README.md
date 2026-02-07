<div align="center">
  <img src="assets/logo.svg" alt="Pipetree Logo" width="120"/>
  <h1>Pipetree</h1>

  **A modular, benchmarkable pipeline framework for large document processing.**

  [![CI](https://github.com/silver-river-us/pipetree/actions/workflows/test.yml/badge.svg)](https://github.com/silver-river-us/pipetree/actions/workflows/test.yml)
  [![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
  [![License: O'Saasy](https://img.shields.io/badge/License-O'Saasy-blue.svg)](LICENSE)
</div>

---

Pipetree gives you capability-based contracts, streaming execution, async support, checkpointing, pluggable implementations via a registry, and built-in A/B benchmarking — all wired together with a clean DSL.

Monitor your pipelines and benchmark results in real-time at [pipetree.io](https://pipetree.io).

## Quick Start

```bash
cd pipetree
pipenv install --dev
pipenv run pip install -e .
```

```python
import asyncio
from pipetree import step, pipeline, Step, Context

@step(requires={"input"}, provides={"words"})
class Split(Step):
    def run(self, ctx: Context) -> Context:
        ctx["words"] = ctx["input"].split()
        return ctx

@step(requires={"words"}, provides={"output"})
class Shout(Step):
    def run(self, ctx: Context) -> Context:
        ctx["output"] = "_".join(w.upper() for w in ctx["words"])
        return ctx

result = asyncio.run(pipeline("demo", [Split, Shout]).run({"input": "hello world"}))
# result["output"] == "HELLO_WORLD"
```

## Benchmarking

Register multiple implementations of the same capability, then A/B test them:

```python
from pipetree import step, Step, Context, Capability, Registry, BenchRunner

@step(requires={"items"}, provides={"sorted"})
class BubbleSort(Step):
    def run(self, ctx: Context) -> Context:
        arr = list(ctx["items"])
        for i in range(len(arr)):
            for j in range(len(arr) - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
        ctx["sorted"] = arr
        return ctx

@step(requires={"items"}, provides={"sorted"})
class BuiltinSort(Step):
    def run(self, ctx: Context) -> Context:
        ctx["sorted"] = sorted(ctx["items"])
        return ctx

# Register both under the same capability
sorting = Capability(name="sorting", requires={"items"}, provides={"sorted"})

registry = Registry()
registry.register("sorting", "bubble", lambda: BubbleSort(sorting, "bubble"))
registry.register("sorting", "builtin", lambda: BuiltinSort(sorting, "builtin"))

# Run the benchmark
runner = BenchRunner(registry=registry)

results = runner.run_step_ab(
    cap_name="sorting",
    impls=["bubble", "builtin"],
    fixtures=[
        {"id": "small", "items": list(range(100, 0, -1))},
        {"id": "large", "items": list(range(10000, 0, -1))},
    ],
    judge=lambda fixture, ctx: {"correctness": float(ctx["sorted"] == sorted(fixture["items"]))},
    setup_ctx=lambda fixture: {"items": fixture["items"]},
)
```

## Cloud

Send pipeline progress and benchmark results to [pipetree.io](https://pipetree.io) by setting two env vars:

```bash
export PIPETREE_HOST=https://pipetree.io
export PIPETREE_API_KEY=your-api-key
```

```python
from pipetree import HTTPProgressNotifier, HTTPBenchmarkStore, BenchRunner, pipeline

# Progress tracking
notifier = HTTPProgressNotifier(base_url=..., api_key=..., pipeline="my-pipeline")
my_pipeline = pipeline("my-pipeline", [Split, Shout], progress_notifier=notifier)

# Remote benchmark results
store = HTTPBenchmarkStore(base_url=..., api_key=...)
runner = BenchRunner(registry=my_registry, store=store)
```

## Development

```bash
cd pipetree
bin/check  # lint, types, tests (100% coverage)
```

## License

[O'Saasy License](LICENSE) - Free to use, modify, and self-host. SaaS rights reserved.
