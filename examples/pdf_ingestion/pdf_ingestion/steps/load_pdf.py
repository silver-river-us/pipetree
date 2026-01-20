"""Load PDF step - lightweight metadata extraction."""

import fitz  # PyMuPDF - faster and more memory-efficient than pypdf
from pipetree import Step, step

from ..context import PdfContext


@step(requires={"path", "output_path"}, provides={"pdf", "total_pages"})
class LoadPdf(Step):
    """Load PDF metadata without keeping the document in memory."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        print(f"Loading PDF from: {ctx.path}")

        # Use fitz for lightweight page count (doesn't load page content)
        with fitz.open(ctx.path) as doc:
            ctx.total_pages = doc.page_count

        ctx.pdf = True  # type: ignore[assignment]  # Mark as "loaded" for capability check

        print(f"PDF has {ctx.total_pages} pages")
        return ctx
