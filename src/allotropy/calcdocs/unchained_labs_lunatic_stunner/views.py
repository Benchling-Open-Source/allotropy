from __future__ import annotations

from collections import defaultdict

from allotropy.calcdocs.extractor import Element
from allotropy.calcdocs.view import View


class UuidView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="uuid", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if uuid := element.get_str("uuid"):
                items[uuid].append(element)
        return dict(items)


class DetectionTypeView(View):
    def __init__(self, sub_view: View | None = None):
        super().__init__(name="detection_type", sub_view=sub_view)

    def sort_elements(self, elements: list[Element]) -> dict[str, list[Element]]:
        items = defaultdict(list)
        for element in elements:
            if detection_type := element.get_str("detection type"):
                items[detection_type].append(element)
        return dict(items)
