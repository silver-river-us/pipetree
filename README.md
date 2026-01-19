<div align="center">
  <h1>Pipetree</h1>

  **A modular, benchmarkable pipeline framework for large document processing.**

  [![CI](https://github.com/silver-river-us/pipetree/actions/workflows/test.yml/badge.svg)](https://github.com/silver-river-us/pipetree/actions/workflows/test.yml)
  [![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
  [![License: O'Saasy](https://img.shields.io/badge/License-O'Saasy-blue.svg)](LICENSE)
</div>

---

## Features

- **Capability-based contracts** - Explicit pre/postconditions for each step
- **Streaming execution** - Memory-bounded processing for huge documents
- **Async-first** - Supports both sync and async steps transparently
- **Checkpointing** - Resumable processing with cursor-based checkpoints
- **Pluggable implementations** - Registry for swapping step implementations
- **Benchmarking** - A/B testing for steps and pipelines with correctness evaluation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          Pipetree                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │  Step 1  │──▶│  Step 2  │──▶│  Router  │──▶│  Step N  │     │
│  │ (cap: A) │   │ (cap: B) │   │ (cap: C) │   │ (cap: D) │     │
│  └──────────┘   └──────────┘   └────┬─────┘   └──────────┘     │
│                                     │                           │
│                              ┌──────┴──────┐                    │
│                              ▼             ▼                    │
│                         [Route A]     [Route B]                 │
└─────────────────────────────────────────────────────────────────┘
         │                                           │
         ▼                                           ▼
┌─────────────────┐                       ┌─────────────────┐
│ CheckpointStore │                       │    Registry     │
│  (resumability) │                       │ (swappable impl)│
└─────────────────┘                       └─────────────────┘
```

## Core Components

### Capability

Defines a contract for pipeline steps using `requires` (preconditions) and `provides` (postconditions).

```python
Capability(name="chunking", requires={"texts", "kind"}, provides={"chunks"})
```

Steps are interchangeable only if they implement the same capability. The pipeline validates contracts at runtime.

### Step

The base processing unit. Each step declares a capability and implements a `run(ctx)` method that transforms context.

```
┌────────────────────────────┐
│          Step          │
├────────────────────────────┤
│ cap: Capability            │
│ name: str                  │
├────────────────────────────┤
│ run(ctx) → Context             │
└────────────────────────────┘
```

### Router

A specialized step that branches to different implementations based on context signals.

```
         ┌──────────┐
         │  Router  │
         │  pick()  │
         └────┬─────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 [impl_a] [impl_b] [default]
```

### Pipetree

Orchestrates step execution with:
- **Chain validation** - Ensures `provides` from step N satisfies `requires` of step N+1
- **Runtime contract checks** - Validates pre/postconditions during execution
- **Async support** - Handles both sync and async steps transparently

### CheckpointStore

Enables resumable processing via cursor-based checkpoints.

```python
# Cursor tracks progress
Cursor = { page: int, chunk_idx: int, extra: {...} }
```

Implementations: `InMemoryCheckpointStore`, `FileCheckpointStore`

### Registry

Manages multiple implementations per capability for experimentation and A/B testing.

```python
registry.register("chunking", "simple", SimpleChunkerFactory)
registry.register("chunking", "semantic", SemanticChunkerFactory)
step = registry.make("chunking", "semantic")
```

## Data Flow

The `Context` (context) object flows through the pipeline as a streaming data bus:

```
Input: path → pdf → pages → texts → chunks → vec_batches → done
            (iterator)  (iterator)  (iterator)  (async iter)
```

For large documents, values are streams/iterators to maintain bounded memory usage.

### Predefined Capabilities

```
┌────────────────┐     ┌─────────────────┐     ┌──────────┐
│ CLASSIFICATION │────▶│ PAGE_ITERATION  │────▶│TEXT_EXTR │
│ pdf→kind,scan  │     │ pdf→pages       │     │pages→txt │
└────────────────┘     └─────────────────┘     └────┬─────┘
                                                    │
┌────────────────┐     ┌─────────────────┐          ▼
│ INDEX_WRITING  │◀────│    EMBEDDING    │◀────┌──────────┐
│ vecs→done      │     │ chunks→vecs     │     │ CHUNKING │
└────────────────┘     └─────────────────┘     │ txt→chunk│
                                               └──────────┘
```

## Benchmarking

The `BenchRunner` supports A/B testing of implementations:

```python
runner = BenchRunner(registry=registry)
results = await runner.run_step_ab(
    cap_name="chunking",
    impls=["simple", "semantic"],
    fixtures=test_fixtures,
    judge=accuracy_judge,
)
```

Metrics collected: `wall_time_s`, `peak_mem_mb`, `throughput_pages_s`, `correctness`

## Installation

```bash
pipenv install --dev
pipenv run pip install -e .
```

## Running Tests

```bash
# Run all tests
pipenv run pytest

# Run with verbose output
pipenv run pytest -v

# Run a specific test file
pipenv run pytest tests/test_pipeline.py

# Run with coverage (if installed)
pipenv run pytest --cov=pipetree
```

## Linting

```bash
# Check for issues
pipenv run ruff check .

# Auto-fix issues
pipenv run ruff check . --fix

# Format code
pipenv run ruff format .
```

## Run All Checks (CI locally)

```bash
./bin/check
```

This runs lint, type check, and tests - the same checks as CI.

## Running the Pipeline

```python
import asyncio
from pipetree import Pipetree, Capability, Step, Context

# Define a capability
my_cap = Capability(
    name="text_extraction",
    requires={"pages"},
    provides={"texts"},
)

# Implement a step
class MyExtractor(Step):
    def run(self, ctx: Context) -> Context:
        ctx["texts"] = extract_texts(ctx["pages"])
        return ctx

# Build and run pipetree
pipetree = Pipetree(steps=[MyExtractor(my_cap, "extractor")])

async def main():
    result = await pipetree.run({"pages": my_pages})
    print(result)

asyncio.run(main())
```

Or run directly from the shell:

```bash
pipenv run python -c "
import asyncio
from pipetree import Pipetree, Step, Capability, Context

# Define your steps and run
async def main():
    # Your pipeline code here
    pass

asyncio.run(main())
"
```

## Visualizer

Pipetree includes a real-time monitoring dashboard built with FastAPI, HTMX, and Tailwind CSS.

```bash
cd visualizer
pipenv install
pipenv run uvicorn visualizer.app:app --reload
```

Features:
- Real-time pipeline progress via WebSocket
- Multiple database support
- Interactive step visualization (horizontal, vertical, list views)
- CircleCI-inspired UI

## Project Structure

```
pipetree/
├── pipetree/              # Core library
│   ├── pipetree/          # Main package
│   └── tests/             # Unit tests
├── visualizer/            # Monitoring dashboard
│   ├── visualizer/        # FastAPI app
│   └── templates/         # Jinja2 templates
└── examples/
    ├── pdf_ingestion/     # PDF processing example
    └── stress_test/       # Load testing example
```

## License

[O'Saasy License](LICENSE) - Free to use, modify, and self-host. SaaS rights reserved.
