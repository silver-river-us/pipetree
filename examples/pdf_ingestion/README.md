# PDF Ingestion Example

A multi-branching PDF processing pipeline that extracts text from large PDFs, classifies documents by content, and routes them through specialized analysis steps.

## What it demonstrates

- **Parallel text extraction** using `ProcessPoolExecutor` with chunked page ranges
- **Memory-efficient processing** via file-backed `LazyTextFile` (streams to disk, not RAM)
- **Conditional branching** with nested routers (`ops` vs `parts` -> `mechanical` vs `electrical`)
- **Capability contracts** with `@step(requires=..., provides=...)` decorators
- **A/B benchmarking** comparing pypdf, pdfplumber, and PyMuPDF extraction libraries
- **Progress tracking** with optional cloud reporting via pipetree.io

## Pipeline structure

```
LoadPdf -> ExtractText -> Categorize -> CategoryRouter
                                           |
                                  +--------+--------+
                                  |                 |
                                 ops              parts
                                  |                 |
                            ProcessOps      PartsTypeRouter
                                           +--------+--------+
                                           |                 |
                                       mechanical        electrical
```

## Setup

```bash
bin/setup
```

## Usage

```bash
# Run the pipeline (defaults to assets/big.pdf)
bin/run

# Run with a specific PDF
PDF_PATH=assets/small.pdf bin/run

# Run benchmarks (compares pypdf vs pdfplumber vs pymupdf)
bin/benchmark

# Run checks (lint, types, tests)
bin/check
```

## Sample PDFs

The `assets/` directory contains public domain US government documents for testing:

- `small.pdf` — NIST SP 800-100, Information Security Handbook (178 pages)
- `medium.pdf` — 9/11 Commission Report (585 pages)
- `big.pdf` — Warren Commission Report (920 pages)
