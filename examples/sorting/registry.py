"""Registry with all sorting implementations."""

from pipetree import Capability, Registry

from steps import BubbleSort, BuiltinSort, InsertionSort

SORTING = Capability(name="sorting", requires={"items"}, provides={"sorted"})

registry = Registry()


@registry.decorator("sorting", "bubble")
def _bubble() -> BubbleSort:
    return BubbleSort(SORTING, "bubble")


@registry.decorator("sorting", "insertion")
def _insertion() -> InsertionSort:
    return InsertionSort(SORTING, "insertion")


@registry.decorator("sorting", "builtin")
def _builtin() -> BuiltinSort:
    return BuiltinSort(SORTING, "builtin")
