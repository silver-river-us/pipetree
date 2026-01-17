"""Load PDF step."""

from pipetree import BaseStep

from ..context import PdfContext


class LoadPdfStep(BaseStep):
    """Load a PDF file from disk."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        # In a real implementation, you'd use pymupdf or similar
        print(f"Loading PDF from: {ctx.path}")
        ctx.pdf = {"path": ctx.path, "loaded": True}
        return ctx
