"""Parts catalog processing step."""

import re

from pipetree import Step
from pipetree.types import Context


class ProcessPartsStep(Step):
    """
    Processes parts catalogs/lists.

    Extracts:
    - Part numbers
    - Quantities
    - Assemblies and components
    """

    def run(self, ctx: Context) -> Context:
        # Use streaming join to avoid loading all texts into memory at once
        full_text = ctx.texts.join("\n")  # type: ignore

        print("Processing as PARTS catalog...")

        # Simulate processing with progress
        total_tasks = 4
        results = {
            "type": "parts_catalog",
            "part_numbers": [],
            "assemblies": [],
            "figures": [],
            "components": [],
        }

        # Task 1: Extract part numbers
        ctx.report_progress(1, total_tasks, "Extracting part numbers...")
        part_numbers = re.findall(
            r"(?:part\s*(?:number|no|#)|p/n)[:\s]*([A-Z0-9][-A-Z0-9]+)",
            full_text,
            re.IGNORECASE,
        )
        results["part_numbers"] = list(set(part_numbers))[:50]

        # Task 2: Extract assemblies
        ctx.report_progress(2, total_tasks, "Identifying assemblies...")
        assemblies = re.findall(
            r"assembly[:\s]+([^\n]+)",
            full_text,
            re.IGNORECASE,
        )
        results["assemblies"] = list(set(assemblies))[:20]

        # Task 3: Extract figures
        ctx.report_progress(3, total_tasks, "Mapping figures...")
        figures = re.findall(
            r"figure\s+(\d+)[:\s]*([^\n]*)",
            full_text,
            re.IGNORECASE,
        )
        results["figures"] = [
            {"number": f[0], "title": f[1].strip()} for f in figures[:30]
        ]

        # Task 4: Extract components
        ctx.report_progress(4, total_tasks, "Cataloging components...")
        components = re.findall(
            r"(?:component|item)\s*\d*[:\s]+([^\n]+)",
            full_text,
            re.IGNORECASE,
        )
        results["components"] = list(set(components))[:30]

        ctx.processed_parts = results  # type: ignore
        ctx.processed_ops = {}  # Set empty for unselected branch

        print(f"  Found {len(results['part_numbers'])} part numbers")
        print(f"  Found {len(results['assemblies'])} assemblies")
        print(f"  Found {len(results['figures'])} figures")

        return ctx
