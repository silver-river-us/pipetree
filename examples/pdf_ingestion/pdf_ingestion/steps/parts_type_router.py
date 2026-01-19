"""Router that further categorizes parts into mechanical vs electrical."""

from pipetree import Router
from pipetree.types import Context


class PartsTypeRouter(Router):
    """
    Routes parts processing based on part type detection.

    Routes:
    - "mechanical": Mechanical parts (gears, bearings, housings)
    - "electrical": Electrical parts (wiring, connectors, circuits)
    """

    # Note: branch_outputs for mechanical/electrical are declared in parent
    # CategoryRouter since it owns processed_mechanical and processed_electrical

    def pick(self, ctx: Context) -> str:
        """Detect part type from text content."""
        texts: list[str] = getattr(ctx, "texts", [])
        full_text = "\n".join(texts).lower()

        # Count indicators
        mechanical_indicators = sum(
            1
            for word in [
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
            if word in full_text
        )

        electrical_indicators = sum(
            1
            for word in [
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
            if word in full_text
        )

        part_type = (
            "mechanical"
            if mechanical_indicators >= electrical_indicators
            else "electrical"
        )
        print(f"  Part type detected: {part_type.upper()}")
        print(
            f"    Mechanical indicators: {mechanical_indicators}, Electrical: {electrical_indicators}"
        )

        return part_type
