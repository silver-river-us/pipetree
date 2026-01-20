"""
PDF Ingestion Pipeline Example - DSL Version

This example demonstrates the clean DSL syntax for defining pipelines.
Compare with main.py to see the readability improvement.

The pipeline structure is immediately visible:

    load_pdf
    extract_text
    categorize
    category >> [
        ops >> process_ops,
        parts >> parts_type >> [
            mechanical >> process_mechanical,
            electrical >> process_electrical,
        ],
    ]
    save_text
"""

from pipetree import B, Step, pipeline, route, step

from .context import PdfContext

# =============================================================================
# Route markers - define once, use in pipeline
# =============================================================================

category = route("category")
parts_type = route("parts_type", default="mechanical")

# Branch markers - for explicit branch assignment
ops = B("ops")
parts = B("parts")
mechanical = B("mechanical")
electrical = B("electrical")


# =============================================================================
# Steps - capability defined inline with @step decorator
# =============================================================================


@step(requires={"path", "output_path"}, provides={"pdf", "total_pages"})
class LoadPdf(Step):
    """Load PDF metadata without keeping the document in memory."""

    def run(self, ctx: PdfContext) -> PdfContext:
        import fitz

        print(f"Loading PDF from: {ctx.path}")
        with fitz.open(ctx.path) as doc:
            ctx.total_pages = doc.page_count
        ctx.pdf = True
        print(f"PDF has {ctx.total_pages} pages")
        return ctx


@step(requires={"pdf"}, provides={"texts"})
class ExtractText(Step):
    """Extract text from PDF pages."""

    def run(self, ctx: PdfContext) -> PdfContext:
        from .steps.extract_text import ExtractTextStep

        impl = ExtractTextStep.__new__(ExtractTextStep)
        return impl.run(ctx)


@step(requires={"texts"}, provides={"category"})
class Categorize(Step):
    """Categorize document as ops or parts manual."""

    def run(self, ctx: PdfContext) -> PdfContext:
        from .steps.categorize import CategorizeStep

        impl = CategorizeStep.__new__(CategorizeStep)
        return impl.run(ctx)


@step(requires={"texts", "category"}, provides={"processed_ops"})
class ProcessOps(Step):
    """Process operations/procedures manual."""

    def run(self, ctx: PdfContext) -> PdfContext:
        from .steps.process_ops import ProcessOpsStep

        impl = ProcessOpsStep.__new__(ProcessOpsStep)
        return impl.run(ctx)


@step(requires={"texts", "category"}, provides={"processed_mechanical"})
class ProcessMechanical(Step):
    """Process mechanical parts catalog."""

    def run(self, ctx: PdfContext) -> PdfContext:
        from .steps.process_mechanical import ProcessMechanicalStep

        impl = ProcessMechanicalStep.__new__(ProcessMechanicalStep)
        return impl.run(ctx)


@step(requires={"texts", "category"}, provides={"processed_electrical"})
class ProcessElectrical(Step):
    """Process electrical parts catalog."""

    def run(self, ctx: PdfContext) -> PdfContext:
        from .steps.process_electrical import ProcessElectricalStep

        impl = ProcessElectricalStep.__new__(ProcessElectricalStep)
        return impl.run(ctx)


@step(requires={"texts", "output_path"}, provides={"saved"})
class SaveText(Step):
    """Save extracted text to file."""

    def run(self, ctx: PdfContext) -> PdfContext:
        from .steps.save_text import SaveTextStep

        impl = SaveTextStep.__new__(SaveTextStep)
        return impl.run(ctx)


# =============================================================================
# Pipeline definition - the tree structure is immediately visible!
# =============================================================================

pdf_pipeline = pipeline("PDF Pipeline", [
    LoadPdf,
    ExtractText,
    Categorize,
    category >> [
        ops >> ProcessOps,
        parts >> parts_type >> [
            mechanical >> ProcessMechanical,
            electrical >> ProcessElectrical,
        ],
    ],
    SaveText,
])


# =============================================================================
# Main entry point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    async def main():
        project_root = Path(__file__).parent.parent
        pdf_path = project_root / "assets" / "big.pdf"
        output_path = project_root / "assets" / (pdf_path.stem + ".txt")

        print("PDF Pipeline (DSL Version)")
        print("=" * 40)
        print(f"Input:  {pdf_path}")
        print(f"Output: {output_path}")
        print()

        ctx = PdfContext(
            path=str(pdf_path),
            output_path=str(output_path),
        )

        result = await pdf_pipeline.run(ctx)

        print()
        print("Done!")
        print(f"Category: {result.category}")
        print(f"Pages: {result.total_pages}")

    asyncio.run(main())
