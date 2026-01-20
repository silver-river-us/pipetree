"""Categorization step - determines if document is ops or parts manual."""

import re

from pipetree import Step, step
from pipetree.types import Context

# Pre-compile combined regex patterns for efficiency (single scan instead of 25)
_OPS_PATTERN = re.compile(
    r"\b(?:"
    r"procedure|"
    r"step\s+\d+|"
    r"instructions?|"
    r"operat(?:e|ion|ing)|"
    r"perform|"
    r"execut(?:e|ion)|"
    r"maintenance|"
    r"install(?:ation)?|"
    r"remov(?:e|al)|"
    r"check|"
    r"inspect|"
    r"warning|"
    r"caution"
    r")\b"
)

_PARTS_PATTERN = re.compile(
    r"\b(?:"
    r"part\s*(?:number|no|#)|"
    r"p/n|"
    r"quantity|"
    r"qty|"
    r"unit|"
    r"catalog|"
    r"figure\s+\d+|"
    r"item\s+\d+|"
    r"assembly|"
    r"component|"
    r"spec(?:ification)?|"
    r"dimension"
    r")\b"
)

# Pattern for mechanical vs electrical parts detection
_MECHANICAL_KEYWORDS = frozenset(
    [
        "gear",
        "bearing",
        "shaft",
        "housing",
        "bolt",
        "nut",
        "washer",
        "spring",
        "seal",
        "gasket",
        "bushing",
        "coupling",
        "bracket",
    ]
)

_ELECTRICAL_KEYWORDS = frozenset(
    [
        "wire",
        "cable",
        "connector",
        "circuit",
        "relay",
        "fuse",
        "switch",
        "terminal",
        "harness",
        "sensor",
        "motor",
        "solenoid",
    ]
)


@step(requires={"texts"}, provides={"category", "parts_type"})
class Categorize(Step):
    """
    Analyzes extracted text to categorize the document.

    Categories:
    - "ops": Operations/procedures manual (how to do things)
    - "parts": Parts catalog/list (what parts exist)

    For parts documents, also determines parts_type:
    - "mechanical": Mechanical parts (gears, bearings, housings)
    - "electrical": Electrical parts (wiring, connectors, circuits)
    """

    def run(self, ctx: Context) -> Context:
        # Use streaming join to avoid loading all texts into memory at once
        full_text = ctx.texts.join(" ").lower()  # type: ignore

        # Count indicators using pre-compiled patterns (2 scans instead of 25)
        ops_score = len(_OPS_PATTERN.findall(full_text))
        parts_score = len(_PARTS_PATTERN.findall(full_text))

        # Report progress
        ctx.report_progress(1, 2, "Analyzing document content...")

        # Determine category based on scores
        category = "parts" if parts_score > ops_score else "ops"
        ctx.category = category  # type: ignore

        # For parts documents, also determine parts type (mechanical vs electrical)
        mechanical_count = sum(1 for word in _MECHANICAL_KEYWORDS if word in full_text)
        electrical_count = sum(1 for word in _ELECTRICAL_KEYWORDS if word in full_text)
        parts_type = (
            "mechanical" if mechanical_count >= electrical_count else "electrical"
        )
        ctx.parts_type = parts_type  # type: ignore

        ctx.report_progress(2, 2, f"Categorized as: {category}")

        print(f"Document categorized as: {category.upper()}")
        print(f"  Ops indicators: {ops_score}, Parts indicators: {parts_score}")

        return ctx
