"""Sorting step implementations."""

from pipetree import Context, Step, step


@step(requires={"items"}, provides={"sorted"})
class BubbleSort(Step):
    def run(self, ctx: Context) -> Context:
        arr = list(ctx["items"])
        for i in range(len(arr)):
            for j in range(len(arr) - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
        ctx["sorted"] = arr
        return ctx


@step(requires={"items"}, provides={"sorted"})
class InsertionSort(Step):
    def run(self, ctx: Context) -> Context:
        arr = list(ctx["items"])
        for i in range(1, len(arr)):
            key = arr[i]
            j = i - 1
            while j >= 0 and arr[j] > key:
                arr[j + 1] = arr[j]
                j -= 1
            arr[j + 1] = key
        ctx["sorted"] = arr
        return ctx


@step(requires={"items"}, provides={"sorted"})
class BuiltinSort(Step):
    def run(self, ctx: Context) -> Context:
        ctx["sorted"] = sorted(ctx["items"])
        return ctx
