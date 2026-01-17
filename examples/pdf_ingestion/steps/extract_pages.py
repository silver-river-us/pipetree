"""Extract pages step."""

from pipetree import BaseStep

from ..context import PdfContext


class ExtractPagesStep(BaseStep):
    """Extract pages from a PDF."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        # In a real implementation, you'd iterate over PDF pages
        print(f"Extracting pages from PDF: {ctx.pdf['path']}")  # type: ignore
        ctx.pages = [
            {"page_num": 1, "content": "Page 1 content..."},
            {"page_num": 2, "content": "Page 2 content..."},
            {"page_num": 3, "content": "Page 3 content..."},
        ]
        return ctx
