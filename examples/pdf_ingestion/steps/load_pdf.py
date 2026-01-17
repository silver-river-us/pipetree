"""Load PDF step."""

from pypdf import PdfReader

from pipetree import Step

from ..context import PdfContext


class LoadPdfStep(Step):
    """Load PDF metadata without keeping it in memory."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        print(f"Loading PDF from: {ctx.path}")

        reader = PdfReader(ctx.path)
        ctx.total_pages = len(reader.pages)
        ctx.pdf = True  # type: ignore[assignment]  # Mark as "loaded" for capability check

        print(f"PDF has {ctx.total_pages} pages")
        return ctx
