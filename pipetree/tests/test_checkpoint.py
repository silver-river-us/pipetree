"""Tests for checkpoint storage."""

import tempfile
from pathlib import Path

from pipetree.checkpoint import FileCheckpointStore, InMemoryCheckpointStore
from pipetree.types import Cursor


class TestInMemoryCheckpointStore:
    def test_save_and_load(self) -> None:
        store = InMemoryCheckpointStore()
        cursor: Cursor = {"page": 5, "chunk_idx": 10}

        store.save("doc1", cursor)
        loaded = store.load("doc1")

        assert loaded == cursor

    def test_load_missing(self) -> None:
        store = InMemoryCheckpointStore()
        assert store.load("nonexistent") is None

    def test_delete(self) -> None:
        store = InMemoryCheckpointStore()
        cursor: Cursor = {"page": 1}

        store.save("doc1", cursor)
        store.delete("doc1")

        assert store.load("doc1") is None

    def test_delete_nonexistent(self) -> None:
        store = InMemoryCheckpointStore()
        # Should not raise
        store.delete("nonexistent")

    def test_clear(self) -> None:
        store = InMemoryCheckpointStore()
        store.save("doc1", {"page": 1})
        store.save("doc2", {"page": 2})

        store.clear()

        assert store.load("doc1") is None
        assert store.load("doc2") is None

    def test_overwrite(self) -> None:
        store = InMemoryCheckpointStore()
        store.save("doc1", {"page": 1})
        store.save("doc1", {"page": 99})

        loaded = store.load("doc1")
        assert loaded is not None
        assert loaded["page"] == 99


class TestFileCheckpointStore:
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileCheckpointStore(tmpdir)
            cursor: Cursor = {"page": 5, "chunk_idx": 10}

            store.save("doc1", cursor)
            loaded = store.load("doc1")

            assert loaded == cursor

    def test_load_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileCheckpointStore(tmpdir)
            assert store.load("nonexistent") is None

    def test_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileCheckpointStore(tmpdir)
            cursor: Cursor = {"page": 1}

            store.save("doc1", cursor)
            store.delete("doc1")

            assert store.load("doc1") is None

    def test_sanitizes_doc_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileCheckpointStore(tmpdir)
            cursor: Cursor = {"page": 1}

            # Path-like doc_id should be sanitized
            store.save("/path/to/doc.pdf", cursor)
            loaded = store.load("/path/to/doc.pdf")

            assert loaded == cursor

    def test_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "nested" / "dir"
            store = FileCheckpointStore(subdir)

            store.save("doc1", {"page": 1})

            assert subdir.exists()
