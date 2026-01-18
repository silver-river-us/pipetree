"""Categorization step - determines if document is ops or parts manual."""

import re

from pipetree import Step
from pipetree.types import Context


class CategorizeStep(Step):
    """
    Analyzes extracted text to categorize the document.

    Categories:
    - "ops": Operations/procedures manual (how to do things)
    - "parts": Parts catalog/list (what parts exist)
    """

    def run(self, ctx: Context) -> Context:
        texts: list[str] = ctx.texts  # type: ignore
        full_text = " ".join(texts).lower()

        # Count indicators for each category
        ops_indicators = [
            r"\bprocedure\b",
            r"\bstep\s+\d+\b",
            r"\binstructions?\b",
            r"\boperat(e|ion|ing)\b",
            r"\bperform\b",
            r"\bexecut(e|ion)\b",
            r"\bmaintenance\b",
            r"\binstall(ation)?\b",
            r"\bremov(e|al)\b",
            r"\bcheck\b",
            r"\binspect\b",
            r"\bwarning\b",
            r"\bcaution\b",
        ]

        parts_indicators = [
            r"\bpart\s*(number|no|#)\b",
            r"\bp/n\b",
            r"\bquantity\b",
            r"\bqty\b",
            r"\bunit\b",
            r"\bcatalog\b",
            r"\bfigure\s+\d+\b",
            r"\bitem\s+\d+\b",
            r"\bassembly\b",
            r"\bcomponent\b",
            r"\bspec(ification)?\b",
            r"\bdimension\b",
        ]

        ops_score = sum(len(re.findall(p, full_text)) for p in ops_indicators)
        parts_score = sum(len(re.findall(p, full_text)) for p in parts_indicators)

        # Report progress
        ctx.report_progress(1, 2, "Analyzing document content...")

        # Determine category based on scores
        if parts_score > ops_score:
            category = "parts"
        else:
            category = "ops"

        ctx.category = category  # type: ignore
        ctx.report_progress(2, 2, f"Categorized as: {category}")

        print(f"Document categorized as: {category.upper()}")
        print(f"  Ops indicators: {ops_score}, Parts indicators: {parts_score}")

        return ctx
