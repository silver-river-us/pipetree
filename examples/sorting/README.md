# Sorting Benchmark Example

A minimal example that uses pipetree's A/B benchmarking framework to compare three sorting algorithm implementations.

## What it demonstrates

- **Registry pattern** for registering pluggable step implementations
- **Capability contracts** defining shared `requires`/`provides` interfaces
- **BenchRunner** for side-by-side comparison with time, memory, and correctness metrics
- **Fixture-based testing** with reproducible random datasets

## Implementations

| Name | Algorithm | Complexity |
|------|-----------|------------|
| `bubble` | Bubble sort | O(n^2) |
| `insertion` | Insertion sort | O(n^2) |
| `builtin` | Python's `sorted()` (Timsort) | O(n log n) |

All three implement the same capability (`requires={"items"}, provides={"sorted"}`), making them interchangeable.

## Setup

```bash
bin/setup
```

## Usage

```bash
# Run benchmarks
bin/benchmark
```

This runs all three implementations against lists of 100, 1,000, and 5,000 items, then prints a results table comparing wall time, peak memory, and correctness.
