"""Tests for parallel extraction ordering."""

import random
import time
from concurrent.futures import ProcessPoolExecutor


def _simulate_page_extraction(page_num: int) -> tuple[int, str]:
    """Simulate extracting a page with random delay to test ordering."""
    # Random delay to simulate variable processing times
    time.sleep(random.uniform(0.001, 0.01))
    return page_num, f"Page {page_num} content"


class TestParallelOrdering:
    def test_results_ordered_after_parallel_execution(self) -> None:
        """Verify results are correctly ordered after parallel processing."""
        num_pages = 20
        page_nums = list(range(num_pages))

        with ProcessPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(_simulate_page_extraction, page_nums))

        # Sort by page number (same logic as ExtractTextStep)
        results.sort(key=lambda x: x[0])
        texts = [text for _, text in results]

        # Verify order is correct
        for i, text in enumerate(texts):
            assert text == f"Page {i} content", f"Page {i} out of order"

    def test_results_ordered_with_shuffled_input(self) -> None:
        """Verify ordering works even with shuffled input order."""
        num_pages = 20
        page_nums = list(range(num_pages))
        random.shuffle(page_nums)  # Shuffle input order

        with ProcessPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(_simulate_page_extraction, page_nums))

        # Sort by page number
        results.sort(key=lambda x: x[0])
        texts = [text for _, text in results]

        # Verify order is correct (0, 1, 2, ... regardless of input order)
        for i, text in enumerate(texts):
            assert text == f"Page {i} content", f"Page {i} out of order"

    def test_large_parallel_batch_ordering(self) -> None:
        """Verify ordering with larger batch to stress test."""
        num_pages = 100
        page_nums = list(range(num_pages))

        with ProcessPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(_simulate_page_extraction, page_nums))

        results.sort(key=lambda x: x[0])
        texts = [text for _, text in results]

        assert len(texts) == num_pages
        for i, text in enumerate(texts):
            assert text == f"Page {i} content"
