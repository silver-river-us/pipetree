"""Mechanical parts processing step."""

import re
import time

from pipetree import Step
from pipetree.types import Context


class ProcessMechanicalStep(Step):
    """
    Processes mechanical parts catalogs.

    Extracts:
    - Torque specifications
    - Dimensions
    - Material types
    """

    def run(self, ctx: Context) -> Context:
        texts: list[str] = ctx.texts  # type: ignore
        full_text = "\n".join(texts)

        print("    Processing MECHANICAL parts...")

        total_tasks = 3
        results = {
            "type": "mechanical_parts",
            "torque_specs": [],
            "dimensions": [],
            "materials": [],
        }

        # Task 1: Extract torque specs
        ctx.report_progress(1, total_tasks, "Extracting torque specifications...")
        time.sleep(0.3)
        torque_specs = re.findall(
            r"(\d+)\s*(?:ft-lb|nm|n·m|lb-ft)",
            full_text,
            re.IGNORECASE,
        )
        results["torque_specs"] = list(set(torque_specs))[:10]

        # Task 2: Extract dimensions
        ctx.report_progress(2, total_tasks, "Extracting dimensions...")
        time.sleep(0.3)
        dimensions = re.findall(
            r"(\d+\.?\d*)\s*(?:mm|cm|in|inch|\")",
            full_text,
            re.IGNORECASE,
        )
        results["dimensions"] = list(set(dimensions))[:15]

        # Task 3: Extract materials
        ctx.report_progress(3, total_tasks, "Identifying materials...")
        time.sleep(0.3)
        materials = re.findall(
            r"(steel|aluminum|brass|bronze|plastic|rubber|nylon|titanium)",
            full_text,
            re.IGNORECASE,
        )
        results["materials"] = list(set(m.lower() for m in materials))

        ctx.processed_mechanical = results  # type: ignore
        ctx.processed_electrical = {}  # Set empty for unselected sibling branch
        ctx.processed_parts = {}  # Mark parent branch as taken

        print(f"      Found {len(results['torque_specs'])} torque specs")
        print(f"      Found {len(results['dimensions'])} dimensions")
        print(f"      Found {len(results['materials'])} materials")

        return ctx
