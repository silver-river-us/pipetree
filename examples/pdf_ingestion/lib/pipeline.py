"""Pipeline definition for PDF ingestion."""

from pipetree import B, HTTPProgressNotifier, Pipetree, pipeline, route

from .steps import (
    Categorize,
    ExtractText,
    LoadPdf,
    ProcessElectrical,
    ProcessMechanical,
    ProcessOps,
    SaveText,
)

# Route markers
category = route("category", default="ops")
parts_type = route("parts_type", default="mechanical")

# Branch markers
ops = B("ops")
parts = B("parts")
mechanical = B("mechanical")
electrical = B("electrical")

PIPELINE_NAME = "PDF Processing Pipeline"


def create_pipeline(
    notifier: HTTPProgressNotifier | None = None,
) -> Pipetree:
    """Create the PDF ingestion pipeline with nested branching."""
    return pipeline(
        PIPELINE_NAME,
        [
            LoadPdf,
            ExtractText,
            Categorize,
            category
            >> [
                ops >> ProcessOps,
                parts
                >> parts_type
                >> [
                    mechanical >> ProcessMechanical,
                    electrical >> ProcessElectrical,
                ],
            ],
            SaveText,
        ],
        progress_notifier=notifier,
    )
