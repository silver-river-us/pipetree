"""Save extracted text to file."""

from pipetree import Step, step

from ..context import PdfContext


@step(requires={"texts", "output_path"}, provides={"saved"})
class SaveText(Step):
    """Save extracted text to a .txt file (streams from disk, memory efficient)."""

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        if not ctx.output_path:
            raise ValueError("output_path not set")

        print(f"Saving text to: {ctx.output_path}")

        total_chars = 0
        page_count = 0

        # Stream texts from file-backed storage to output file
        with open(ctx.output_path, "w", encoding="utf-8") as f:
            for i, text in enumerate(ctx.texts):
                f.write(f"--- Page {i + 1} ---\n")
                f.write(text)
                f.write("\n\n")
                total_chars += len(text)
                page_count += 1

        print(f"Saved {page_count} pages ({total_chars:,} characters)")

        ctx.saved = True
        return ctx
