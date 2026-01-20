"""Electrical parts processing step."""

import re

from pipetree import Step, step
from pipetree.types import Context


@step(requires={"texts", "category"}, provides={"processed_electrical"})
class ProcessElectrical(Step):
    """
    Processes electrical parts catalogs.

    Extracts:
    - Wire gauges
    - Voltage ratings
    - Connector types
    """

    def run(self, ctx: Context) -> Context:
        # Use streaming join to avoid loading all texts into memory at once
        full_text = ctx.texts.join("\n")  # type: ignore

        print("    Processing ELECTRICAL parts...")

        total_tasks = 3
        results = {
            "type": "electrical_parts",
            "wire_gauges": [],
            "voltages": [],
            "connectors": [],
        }

        # Task 1: Extract wire gauges
        ctx.report_progress(1, total_tasks, "Extracting wire gauges...")
        wire_gauges = re.findall(
            r"(\d+)\s*(?:awg|gauge)",
            full_text,
            re.IGNORECASE,
        )
        results["wire_gauges"] = list(set(wire_gauges))[:10]

        # Task 2: Extract voltages
        ctx.report_progress(2, total_tasks, "Extracting voltage ratings...")
        voltages = re.findall(
            r"(\d+\.?\d*)\s*(?:v|volt|vdc|vac)",
            full_text,
            re.IGNORECASE,
        )
        results["voltages"] = list(set(voltages))[:15]

        # Task 3: Extract connector types
        ctx.report_progress(3, total_tasks, "Identifying connectors...")
        connectors = re.findall(
            r"(deutsch|molex|amp|jst|connector|terminal|plug|socket)",
            full_text,
            re.IGNORECASE,
        )
        results["connectors"] = list(set(c.lower() for c in connectors))

        ctx.processed_electrical = results  # type: ignore
        ctx.processed_mechanical = {}  # Set empty for unselected branch
        ctx.processed_parts = {}  # Parent branch marker

        print(f"      Found {len(results['wire_gauges'])} wire gauges")
        print(f"      Found {len(results['voltages'])} voltages")
        print(f"      Found {len(results['connectors'])} connector types")

        return ctx
