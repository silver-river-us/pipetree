"""Tests for the PDF ingestion pipeline."""

from pdf_ingestion.capabilities import (
    CATEGORIZE,
    LOAD_PDF,
    PROCESS_ELECTRICAL,
    PROCESS_MECHANICAL,
    PROCESS_OPS,
    ROUTE_BY_CATEGORY,
    ROUTE_PARTS_TYPE,
    SAVE_TEXT,
    TEXT_EXTRACTION,
)
from pdf_ingestion.main import create_pipeline


class TestCapabilities:
    """Tests for capability definitions."""

    def test_load_pdf_capability(self) -> None:
        assert LOAD_PDF.name == "load_pdf"
        assert "path" in LOAD_PDF.requires
        assert "pdf" in LOAD_PDF.provides

    def test_text_extraction_capability(self) -> None:
        assert TEXT_EXTRACTION.name == "text_extraction"
        assert "pdf" in TEXT_EXTRACTION.requires
        assert "texts" in TEXT_EXTRACTION.provides

    def test_categorize_capability(self) -> None:
        assert CATEGORIZE.name == "categorize"
        assert "texts" in CATEGORIZE.requires
        assert "category" in CATEGORIZE.provides

    def test_router_capabilities(self) -> None:
        assert ROUTE_BY_CATEGORY.name == "process_document"
        assert ROUTE_PARTS_TYPE.name == "route_parts_type"

    def test_process_capabilities(self) -> None:
        assert PROCESS_OPS.name == "process_ops"
        assert PROCESS_MECHANICAL.name == "process_mechanical"
        assert PROCESS_ELECTRICAL.name == "process_electrical"

    def test_save_text_capability(self) -> None:
        assert SAVE_TEXT.name == "save_text"
        assert "texts" in SAVE_TEXT.requires


class TestPipelineCreation:
    """Tests for pipeline creation."""

    def test_create_pipeline_without_notifier(self) -> None:
        pipeline, notifier = create_pipeline(db_path=None)
        assert pipeline is not None
        assert notifier is None
        assert pipeline.name == "PDF Processing Pipeline"
        assert len(pipeline.steps) == 5
