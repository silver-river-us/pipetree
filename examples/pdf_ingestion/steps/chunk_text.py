"""Chunk text step."""

from pipetree import BaseStep, Capability

from ..context import PdfContext


class ChunkTextStep(BaseStep):
    """Chunk text into smaller pieces."""

    def __init__(self, cap: Capability, name: str, chunk_size: int = 100):
        super().__init__(cap, name)
        self.chunk_size = chunk_size

    def run(self, ctx: PdfContext) -> PdfContext:  # type: ignore[override]
        chunks = []
        for i, text in enumerate(ctx.texts):
            # Simple chunking - in reality you'd use semantic chunking
            chunks.append(
                {
                    "id": f"chunk_{i}",
                    "text": text,
                    "metadata": {"source_page": i + 1},
                }
            )
        print(f"Created {len(chunks)} chunks")
        ctx.chunks = chunks
        return ctx
