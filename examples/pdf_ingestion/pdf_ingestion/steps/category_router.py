"""Router that directs to ops or parts processing based on category."""

from typing import ClassVar

from pipetree import Router
from pipetree.types import Context


class CategoryRouter(Router):
    """
    Routes to different processing pipelines based on document category.

    Routes:
    - "ops": Operations manual processing
    - "parts": Parts catalog processing
    """

    # Declare which context attributes each branch provides
    branch_outputs: ClassVar[dict[str, list[str]]] = {
        "ops": ["processed_ops"],
        "parts": ["processed_parts", "processed_mechanical", "processed_electrical"],
    }

    def pick(self, ctx: Context) -> str:
        """Select route based on the category determined by CategorizeStep."""
        category: str | None = getattr(ctx, "category", None)

        if category is None:
            raise ValueError("Category not set in context. Run CategorizeStep first.")

        print(f"Routing to: {category.upper()} processing branch")
        return category
