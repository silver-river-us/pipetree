"""Save extracted text to file."""

from pipetree import Step

from ..context import PdfContext


class SaveTextStep(Step):
    """Save extracted text to a .txt file."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        if not ctx.output_path:
            raise ValueError("output_path not set")

        print(f"Saving text to: {ctx.output_path}")

        with open(ctx.output_path, "w", encoding="utf-8") as f:
            for i, text in enumerate(ctx.texts):
                f.write(f"--- Page {i + 1} ---\n")
                f.write(text)
                f.write("\n\n")

        total_chars = sum(len(t) for t in ctx.texts)
        print(f"Saved {len(ctx.texts)} pages ({total_chars:,} characters)")

        ctx.saved = True
        return ctx
