"""Configuration for bounded concurrency."""

from typing import TypedDict


class ConcurrencyConfig(TypedDict, total=False):
    """Configuration for bounded concurrency."""

    max_inflight: int  # e.g. OCR/page workers
    batch_size: int  # e.g. embeddings
    max_batch_inflight: int  # embedding API rate limiting
