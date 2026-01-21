"""
DSL for defining pipelines with minimal syntax.

Example usage:

    from pipetree.dsl import step, branch, route, pipeline

    @step(requires={"path"}, provides={"pdf"})
    class LoadPdf(Step):
        def run(self, ctx): ...

    @step(requires={"texts", "category"}, provides={"processed_ops"})
    @branch("ops")
    class ProcessOps(Step):
        def run(self, ctx): ...

    # Clean pipeline definition
    pdf_pipeline = pipeline("PDF Pipeline", [
        load_pdf,
        extract_text,
        categorize,
        category >> [
            process_ops,
            parts_type >> [
                process_mechanical,
                process_electrical,
            ],
        ],
        save_text,
    ])
"""

from pipetree.dsl.builder import pipeline
from pipetree.dsl.decorators import branch, step
from pipetree.dsl.markers import B, BranchTarget, RouteMarker, route

__all__ = [
    # Decorators
    "step",
    "branch",
    # Markers
    "route",
    "B",
    "RouteMarker",
    "BranchTarget",
    # Builder
    "pipeline",
]
