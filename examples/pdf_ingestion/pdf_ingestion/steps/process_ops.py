"""Operations manual processing step."""

import re
import time

from pipetree import Step
from pipetree.types import Context


class ProcessOpsStep(Step):
    """
    Processes operations/procedures manuals.

    Extracts:
    - Procedure steps
    - Warnings and cautions
    - Required tools/materials
    """

    def run(self, ctx: Context) -> Context:
        texts: list[str] = ctx.texts  # type: ignore
        full_text = "\n".join(texts)

        print("Processing as OPERATIONS manual...")

        # Simulate processing with progress
        total_tasks = 4
        results = {
            "type": "operations_manual",
            "procedures": [],
            "warnings": [],
            "cautions": [],
            "tools_mentioned": [],
        }

        # Task 1: Extract procedures
        ctx.report_progress(1, total_tasks, "Extracting procedures...")
        procedures = re.findall(
            r"(?:procedure|step)\s*\d+[:\s]+([^\n]+)",
            full_text,
            re.IGNORECASE,
        )
        results["procedures"] = procedures[:20]  # Limit to 20

        # Task 2: Extract warnings
        ctx.report_progress(2, total_tasks, "Extracting warnings...")
        warnings = re.findall(
            r"warning[:\s]+([^\n]+)",
            full_text,
            re.IGNORECASE,
        )
        results["warnings"] = warnings[:10]

        # Task 3: Extract cautions
        ctx.report_progress(3, total_tasks, "Extracting cautions...")
        cautions = re.findall(
            r"caution[:\s]+([^\n]+)",
            full_text,
            re.IGNORECASE,
        )
        results["cautions"] = cautions[:10]

        # Task 4: Extract tools
        ctx.report_progress(4, total_tasks, "Identifying tools...")
        tools = re.findall(
            r"(?:tool|equipment|material)[:\s]+([^\n]+)",
            full_text,
            re.IGNORECASE,
        )
        results["tools_mentioned"] = list(set(tools))[:15]

        ctx.processed_ops = results  # type: ignore
        ctx.processed_parts = {}  # Set empty for unselected branch
        ctx.processed_mechanical = {}  # Set empty for nested branches
        ctx.processed_electrical = {}  # Set empty for nested branches

        print(f"  Found {len(results['procedures'])} procedures")
        print(f"  Found {len(results['warnings'])} warnings")
        print(f"  Found {len(results['cautions'])} cautions")

        return ctx
