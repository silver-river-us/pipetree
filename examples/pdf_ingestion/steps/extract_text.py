"""Extract text step."""

from pipetree import BaseStep

from ..context import PdfContext


class ExtractTextStep(BaseStep):
    """Extract text from pages."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        print(f"Extracting text from {len(ctx.pages)} pages")
        ctx.texts = [page["content"] for page in ctx.pages]
        return ctx
