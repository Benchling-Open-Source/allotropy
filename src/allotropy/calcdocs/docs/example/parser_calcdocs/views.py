from __future__ import annotations

from collections import defaultdict

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class MeanView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="mean", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if mean := element.get_float_or_none("mean"):
                items[str(mean)].append(element)
        return dict(items)


class SumView(View):
    def __init__(self) -> None:
        super().__init__(name="sum")

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if sum_ := element.get_float_or_none("sum"):
                items[str(sum_)].append(element)
        return dict(items)
