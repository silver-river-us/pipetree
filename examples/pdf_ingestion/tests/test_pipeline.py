"""Tests for the PDF ingestion pipeline."""

from pdf_ingestion.main import create_pipeline
from pdf_ingestion.steps import (
    Categorize,
    ExtractText,
    LoadPdf,
    ProcessElectrical,
    ProcessMechanical,
    ProcessOps,
    SaveText,
)


class TestCapabilities:
    """Tests for capability definitions."""

    def test_load_pdf_capability(self) -> None:
        cap = LoadPdf._dsl_capability
        assert cap.name == "load_pdf"
        assert "path" in cap.requires
        assert "pdf" in cap.provides

    def test_text_extraction_capability(self) -> None:
        cap = ExtractText._dsl_capability
        assert cap.name == "extract_text"
        assert "pdf" in cap.requires
        assert "texts" in cap.provides

    def test_categorize_capability(self) -> None:
        cap = Categorize._dsl_capability
        assert cap.name == "categorize"
        assert "texts" in cap.requires
        assert "category" in cap.provides

    def test_process_ops_capability(self) -> None:
        cap = ProcessOps._dsl_capability
        assert cap.name == "process_ops"

    def test_process_mechanical_capability(self) -> None:
        cap = ProcessMechanical._dsl_capability
        assert cap.name == "process_mechanical"

    def test_process_electrical_capability(self) -> None:
        cap = ProcessElectrical._dsl_capability
        assert cap.name == "process_electrical"

    def test_save_text_capability(self) -> None:
        cap = SaveText._dsl_capability
        assert cap.name == "save_text"
        assert "texts" in cap.requires


class TestPipelineCreation:
    """Tests for pipeline creation."""

    def test_create_pipeline_without_notifier(self) -> None:
        pipeline, notifier = create_pipeline(db_path=None)
        assert pipeline is not None
        assert notifier is None
        assert pipeline.name == "PDF Processing Pipeline"
        assert len(pipeline.steps) == 5
